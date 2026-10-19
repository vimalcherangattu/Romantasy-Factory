"""The only way the factory talks to a model: the `claude -p` CLI on the owner's Max plan.

Never import an Anthropic SDK here or anywhere else (PRD section 2).
"""

import csv
import json
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import guard
from .config import Config

LIMIT_PATTERNS = re.compile(
    r"usage limit|limit reached|limit will reset|resets at|rate limit|out of extra usage|"
    r"weekly limit|session limit|5-hour limit|credit balance",
    re.IGNORECASE,
)

USAGE_FIELDS = [
    "timestamp", "book_id", "stage", "model", "input_tokens", "output_tokens",
    "cache_read_input_tokens", "cache_creation_input_tokens", "duration_ms", "num_turns",
    "reported_cost_usd",
]


class ClaudeError(RuntimeError):
    """The CLI failed or timed out."""


class UsageLimitError(RuntimeError):
    """A plan usage limit was hit. The run must save state and stop cleanly."""


@dataclass
class ClaudeResult:
    text: str
    usage: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)


def _log_usage(cfg: Config, book_id: str, stage: str, model: str, raw: dict) -> None:
    path = cfg.paths.state / "usage.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    usage = raw.get("usage") or {}
    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "book_id": book_id,
        "stage": stage,
        "model": model,
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
        "duration_ms": raw.get("duration_ms", 0),
        "num_turns": raw.get("num_turns", 0),
        # Informational only: the CLI reports an API-equivalent figure even on the Max plan.
        "reported_cost_usd": raw.get("total_cost_usd", raw.get("cost_usd", 0)),
    }
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=USAGE_FIELDS)
        if new:
            writer.writeheader()
        writer.writerow(row)


def _extra_args(cfg: Config, tools: list[str] | None) -> list[str]:
    """config extra_args, with the --tools value replaced when an agent declares its own tools."""
    args = [str(a) for a in cfg.get("claude.extra_args", [])]
    if tools is None:
        return args
    if "--tools" in args:
        i = args.index("--tools")
        del args[i : i + 2]
    # Headless runs can't answer permission prompts, so declared tools are also pre-approved.
    return args + ["--tools", ",".join(tools), "--allowedTools", ",".join(tools)]


def _invoke(cfg: Config, system_prompt: str, user_prompt: str, model: str, tools: list[str] | None = None) -> dict:
    # "replace" swaps Claude Code's default coding prompt for the agent prompt: measured at
    # about 1.3k instead of 39k context tokens per call. "append" keeps the default prompt.
    flag = "--append-system-prompt" if cfg.get("claude.system_prompt_mode") == "append" else "--system-prompt"
    args = [
        cfg.claude_binary, "-p",
        "--model", model,
        "--output-format", "json",
        flag, system_prompt,
        *_extra_args(cfg, tools),
    ]
    try:
        proc = subprocess.run(
            args,
            input=user_prompt,
            capture_output=True,
            text=True,
            timeout=cfg.get("claude.timeout_seconds", 1800),
            env=guard.child_env(),
            # Outside the repo, so the CLI doesn't load CLAUDE.md (build rules) into every call.
            cwd=tempfile.gettempdir(),
        )
    except subprocess.TimeoutExpired as exc:
        raise ClaudeError(f"claude timed out after {exc.timeout}s") from exc
    except FileNotFoundError as exc:
        raise ClaudeError(f"claude binary not found: {cfg.claude_binary}") from exc

    combined = f"{proc.stdout}\n{proc.stderr}"
    try:
        raw = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        raw = {}

    text = raw.get("result", "") if isinstance(raw, dict) else ""
    failed = proc.returncode != 0 or (isinstance(raw, dict) and raw.get("is_error"))
    if failed or not raw:
        if LIMIT_PATTERNS.search(combined):
            raise UsageLimitError(_tail(text or combined))
        raise ClaudeError(f"claude exited {proc.returncode}: {_tail(text or combined)}")
    return raw


def _tail(text: str, n: int = 400) -> str:
    text = text.strip()
    return text if len(text) <= n else "…" + text[-n:]


def call(cfg: Config, *, system_prompt: str, user_prompt: str, stage: str, book_id: str,
         model: str | None = None, tools: list[str] | None = None) -> ClaudeResult:
    """Run one stage call. Retries once after `retry_wait_seconds` on CLI error or timeout.

    Raises UsageLimitError immediately (never retried, never switched to paid credits)
    and ClaudeError after the retry fails.
    """
    model = model or cfg.model(stage)
    attempts = 2
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            raw = _invoke(cfg, system_prompt, user_prompt, model, tools)
            _log_usage(cfg, book_id, stage, model, raw)
            return ClaudeResult(text=raw.get("result", ""), usage=raw.get("usage") or {}, raw=raw)
        except UsageLimitError:
            raise
        except ClaudeError as exc:
            last = exc
            if attempt + 1 < attempts:
                time.sleep(cfg.get("claude.retry_wait_seconds", 300))
    raise ClaudeError(str(last))


def usage_rows(cfg: Config) -> list[dict]:
    path: Path = cfg.paths.state / "usage.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))
