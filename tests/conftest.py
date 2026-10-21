import os
import shutil
import stat
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from factory import config as configmod  # noqa: E402


@pytest.fixture
def factory_root(tmp_path, monkeypatch):
    """A throwaway factory folder wired to the fake claude CLI, with tiny books."""
    root = tmp_path / "factory"
    root.mkdir()
    for name in ("agents", "canon", "templates", "site"):
        shutil.copytree(REPO / name, root / name)
    shutil.copy(REPO / "taste.md", root / "taste.md")
    cfg = yaml.safe_load((REPO / "config.yaml").read_text())
    cfg["pen_name"] = "Test Pen"
    cfg["book"].update(chapters_min=3, chapters_max=4, chapter_words_min=300, chapter_words_max=340)
    cfg["claude"].update(retry_wait_seconds=0, timeout_seconds=60)
    cfg["git"]["commit_after_stage"] = False
    cfg["reader"].update(magnet_min_words=100, magnet_max_words=400)
    (root / "config.yaml").write_text(yaml.safe_dump(cfg))

    fake = tmp_path / "bin" / "claude"
    fake.parent.mkdir()
    fake.write_text(f"#!/bin/sh\nexec {sys.executable} {REPO / 'tests' / 'fake_claude.py'} \"$@\"\n")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)

    monkeypatch.setenv("FACTORY_ROOT", str(root))
    monkeypatch.setenv("FACTORY_CLAUDE_BIN", str(fake))
    monkeypatch.setenv("FAKE_CLAUDE_STATE", str(tmp_path / "fake-state"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("FAKE_CLAUDE_MODE", raising=False)
    return root


@pytest.fixture
def cfg(factory_root):
    c = configmod.load(factory_root)
    # the weekly review cap and stop-after-review are tested on their own
    c.data["schedule"]["reviews_per_week"] = None
    c.data["schedule"]["stop_after_review"] = False
    return c


@pytest.fixture
def approved_series(cfg):
    from factory import series

    series.new_series(cfg)
    sid = series.pick(cfg, 1)
    series.approve(cfg, sid)
    return sid


def calls(tmp_root: Path) -> list[str]:
    log = Path(os.environ["FAKE_CLAUDE_STATE"]) / "calls.log"
    return log.read_text().splitlines() if log.exists() else []
