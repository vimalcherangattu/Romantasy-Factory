"""Startup guard: the factory runs on the Max plan only (PRD section 2)."""

import os
import sys

FORBIDDEN = "ANTHROPIC_API_KEY"
# Other variables that can route Claude Code away from the plan. Warn, don't block.
SUSPICIOUS = ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX")


class ApiKeySetError(RuntimeError):
    pass


def check_environment(env=None) -> list[str]:
    """Raise if ANTHROPIC_API_KEY is set; return warnings for other routing variables."""
    env = os.environ if env is None else env
    if env.get(FORBIDDEN):
        raise ApiKeySetError(
            f"{FORBIDDEN} is set. With it, Claude Code bills the API instead of your Max plan. "
            "Remove it from your shell profile, open a new terminal, and run again. "
            "See https://support.claude.com/en/articles/11145838"
        )
    return [f"{name} is set; check it does not route Claude Code away from your Max plan" for name in SUSPICIOUS if env.get(name)]


def enforce() -> None:
    try:
        warnings = check_environment()
    except ApiKeySetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)


def child_env() -> dict:
    """Environment for `claude -p` subprocesses, with the API key removed as a second line of defence."""
    env = dict(os.environ)
    env.pop(FORBIDDEN, None)
    return env
