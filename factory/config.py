"""Loads config.yaml and resolves the factory's directories."""

import os
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Paths:
    root: Path

    @property
    def canon(self) -> Path:
        return self.root / "canon"

    @property
    def agents(self) -> Path:
        return self.root / "agents"

    @property
    def series(self) -> Path:
        return self.root / "series"

    @property
    def proposals(self) -> Path:
        return self.series / "_proposals"

    @property
    def state(self) -> Path:
        return self.root / "state"

    @property
    def review(self) -> Path:
        return self.root / "review"

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    @property
    def taste(self) -> Path:
        return self.root / "taste.md"

    def series_dir(self, series_id: str) -> Path:
        return self.series / series_id

    def book_dir(self, series_id: str, book_id: str) -> Path:
        return self.series / series_id / "books" / book_id


@dataclass
class Config:
    data: dict
    paths: Paths

    def get(self, dotted: str, default=None):
        node = self.data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def model(self, stage: str) -> str:
        return self.get(f"models.{stage}", "sonnet")

    @property
    def claude_binary(self) -> str:
        return os.environ.get("FACTORY_CLAUDE_BIN") or self.get("claude.binary", "claude")


def find_root(start: Path | None = None) -> Path:
    env = os.environ.get("FACTORY_ROOT")
    if env:
        return Path(env).resolve()
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "config.yaml").exists() and (candidate / "agents").is_dir():
            return candidate
    return here


def load(root: Path | None = None) -> Config:
    root = Path(root) if root else find_root()
    data = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8")) or {}
    return Config(data=data, paths=Paths(root=root))
