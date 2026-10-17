"""Commits series/ and state/ to the private git repo after each stage (PRD section 9)."""

import subprocess

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
    return _git(cfg, "commit", "-q", "-m", message).returncode == 0
