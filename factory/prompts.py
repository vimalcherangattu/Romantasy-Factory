"""Builds prompts from agents/*.md and canon/*.md. No prompt text lives in Python (PRD section 11)."""

from pathlib import Path

import yaml

from .config import Config
from .fsutil import read_text

ALWAYS_CANON = ("content-rules", "style-guide")


def _split_frontmatter(text: str) -> tuple[dict, str]:
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            meta = yaml.safe_load(text[4:end]) or {}
            return meta, text[end + 4 :].lstrip("\n")
    return {}, text


def agent(cfg: Config, name: str) -> tuple[dict, str]:
    path = cfg.paths.agents / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Missing agent prompt: {path}")
    return _split_frontmatter(path.read_text(encoding="utf-8"))


def system_prompt(cfg: Config, name: str) -> str:
    """Agent prompt + shared output format + content rules + style guide + the agent's canon files."""
    meta, body = agent(cfg, name)
    parts = [body.strip()]
    fmt = cfg.paths.agents / "_output-format.md"
    if fmt.exists():
        parts.append(fmt.read_text(encoding="utf-8").strip())
    canon = list(ALWAYS_CANON) + [c for c in meta.get("canon", []) if c not in ALWAYS_CANON]
    for item in canon:
        path = cfg.paths.canon / f"{item}.md"
        if not path.exists():
            raise FileNotFoundError(f"Agent {name} needs missing canon file {path}")
        parts.append(f"<canon file=\"canon/{item}.md\">\n{path.read_text(encoding='utf-8').strip()}\n</canon>")
    return "\n\n".join(parts)


def inputs(cfg: Config, task: str, files: dict[str, str | Path], extra: str = "") -> str:
    """User prompt: the task, then each input as a labelled block. Values are text or paths."""
    blocks = [task.strip()]
    for label, value in files.items():
        text = read_text(value) if isinstance(value, Path) else value
        if text is None or not str(text).strip():
            text = "(empty)"
        blocks.append(f"=== INPUT: {label} ===\n{str(text).strip()}\n=== END INPUT ===")
    if extra:
        blocks.append(extra.strip())
    return "\n\n".join(blocks) + "\n"
