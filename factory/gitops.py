"""Commits series/ and state/ to the private git repo after each stage (PRD section 9)."""

import subprocess
import time

from .config import Config

TRACKED = ("series", "state", "review", "reports")


def _git(cfg: Config, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cfg.paths.root, capture_output=True, text=True)


def is_repo(cfg: Config) -> bool:
    return (cfg.paths.root / ".git").exists()


def commit(cfg: Config, message: str) -> bool:
    if not cfg.get("git.commit_after_stage", True) or not is_repo(cfg):
        return False
    paths = [p for p in TRACKED if (cfg.paths.root / p).exists()]
    if not paths:
        return False
    _git(cfg, "add", "--", *paths)
    if _git(cfg, "diff", "--cached", "--quiet").returncode == 0:
        return False
    ok = _git(cfg, "commit", "-q", "-m", message).returncode == 0
    if ok and cfg.get("git.push_after_commit", False):
        push(cfg)
    return ok


def push(cfg: Config) -> bool:
    """Push so work survives a cloud container being reclaimed. One retry; never fatal."""
    for _ in range(2):
        if all(_git(cfg, "push", "-q", "origin", ref).returncode == 0
               for ref in cfg.get("git.push_refs", ["HEAD"])):
            return True
        time.sleep(5)
    return False
