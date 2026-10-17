"""Runs one agent call with validation and the one-retry rule for malformed output (PRD section 6)."""

from typing import Callable

from . import claude, parse, prompts
from .config import Config

# Agent name -> config.yaml models key
MODEL_KEYS = {
    "concept": "S1_concept",
    "bible": "S2_bible",
    "outline": "S3_outline",
    "draft": "S4_draft",
    "critique": "S5_critique",
    "revise": "S6_revise",
    "continuity": "S7_continuity",
    "book_check": "book_check",
    "line_edit": "S8_line_edit",
    "summary": "S9_summary",
    "package": "S10_package",
    "owner_notes": "owner_notes",
}


class StageFailed(RuntimeError):
    """Output still failed validation after the retry. `files` holds the last parsed output, if any."""

    def __init__(self, agent: str, message: str, files: dict | None = None):
        super().__init__(f"{agent}: {message}")
        self.agent = agent
        self.files = files


Validator = Callable[[dict[str, str]], list[str]]


def run(cfg: Config, agent: str, *, task: str, inputs: dict, book_id: str, expect: list[str],
        validator: Validator | None = None, model: str | None = None) -> dict[str, str]:
    system = prompts.system_prompt(cfg, agent)
    user = prompts.inputs(cfg, task, inputs)
    model = model or cfg.get(f"models.{MODEL_KEYS[agent]}", "sonnet")
    extra = ""
    last_error = ""
    last_files: dict | None = None
    for attempt in (1, 2):
        result = claude.call(cfg, system_prompt=system, user_prompt=user + extra, stage=agent,
                             book_id=book_id, model=model)
        try:
            files = parse.require_files(result.text, expect)
            last_files = files
            errors = validator(files) if validator else []
            if errors:
                raise parse.OutputError("; ".join(errors))
            return files
        except parse.OutputError as exc:
            last_error = str(exc)
            extra = f"\n\nVALIDATION ERROR (attempt {attempt}). Fix all of these and return every file again:\n- " + \
                last_error.replace("; ", "\n- ") + "\n"
    raise StageFailed(agent, last_error, last_files)
