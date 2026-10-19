import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from typer.testing import CliRunner

from factory import book as bookmod
from factory import orchestrator, series, state
from factory.cli import app

from .conftest import calls


def test_new_series_pick_approve(cfg):
    folder = series.new_series(cfg)
    assert (folder / "proposals.json").exists()
    assert (folder / "concept-3.md").exists()
    sid = series.pick(cfg, 2)
    assert (cfg.paths.series_dir(sid) / "bible.md").exists()
    assert state.load_series(cfg, sid)["status"] == "draft"
    books = series.approve(cfg, sid)
    assert books == [f"{sid}-b01", f"{sid}-b02", f"{sid}-b03"]
    assert state.load_series(cfg, sid)["status"] == "approved"


def test_full_book_reaches_review(cfg, approved_series):
    rep = orchestrator.run(cfg, echo=lambda *_: None)
    b = state.load_book(cfg, f"{approved_series}-b01")
    assert b["status"] == "review", rep.stop_reason
    assert rep.ready == [b["book_id"]]
    bdir = cfg.paths.book_dir(approved_series, b["book_id"])
    for name in ("outline.md", "outline.json", "summary.md", "continuity-report.md", "book-check.json"):
        assert (bdir / name).exists(), name
    pkg = bdir / "package"
    for name in ("book.epub", "book.docx", "metadata.json", "blurb.md", "cover-prompt.md",
                 "ai-disclosure.md", "upload-checklist.md"):
        assert (pkg / name).exists(), name
    assert "AI-generated" in (pkg / "ai-disclosure.md").read_text()
    sheet = (cfg.paths.review / b["book_id"] / "review.md").read_text()
    assert "Chapter 1" in sheet and "weakest" in sheet
    assert all(c["status"] == "edited" for c in b["chapters"].values())
    # book-level check failure is flagged, not blocking
    assert any("real_loss" in f for f in b["flags"])
    # daily quota: book 2 runs but is not staged for review today
    assert rep.stop_reason.startswith("daily quota")
    b2 = state.load_book(cfg, f"{approved_series}-b02")
    assert "S10" in b2["done"] and b2["status"] == "in_progress"
    # usage logged per stage, never with an API key in the child env
    usage = (cfg.paths.state / "usage.csv").read_text()
    assert "S5" not in usage.splitlines()[0] and "critique" in usage
    assert not any(json.loads(line)["api_key_seen"] for line in calls(cfg.paths.root))
    # report written
    assert list(cfg.paths.reports.glob("*.md"))


def test_book_two_gets_book_one_summary(cfg, approved_series):
    orchestrator.run(cfg, echo=lambda *_: None)
    b2 = state.load_book(cfg, f"{approved_series}-b02")
    assert "Open threads" in bookmod.previous_summaries(cfg, b2)


def test_models_per_stage(cfg, approved_series):
    orchestrator.run(cfg, max_steps=3, echo=lambda *_: None)
    lines = [json.loads(line) for line in calls(cfg.paths.root)]
    by_agent = {line["system_head"]: line["model"] for line in lines}
    assert by_agent["# S3 Book outline agent"] == "opus"
    assert by_agent["# S4 Chapter drafting agent"] == "sonnet"
    assert by_agent["# S5 Chapter critic"] == "opus"


def test_resume_after_step_limit(cfg, approved_series):
    rep = orchestrator.run(cfg, max_steps=2, echo=lambda *_: None)
    assert len(rep.steps) == 2
    b = state.load_book(cfg, f"{approved_series}-b01")
    assert b["done"] == ["S3"] and b["chapters"]["01"]["status"] == "drafted"
    rep2 = orchestrator.run(cfg, max_steps=1, echo=lambda *_: None)
    assert rep2.steps == [f"{b['book_id']}: S5 critique ch 1"]


def test_usage_limit_stops_cleanly_and_resumes(cfg, approved_series, monkeypatch):
    orchestrator.run(cfg, max_steps=1, echo=lambda *_: None)
    monkeypatch.setenv("FAKE_CLAUDE_MODE", "limit")
    rep = orchestrator.run(cfg, echo=lambda *_: None)
    assert "usage limit" in rep.stop_reason and rep.steps == []
    b = state.load_book(cfg, f"{approved_series}-b01")
    assert b["chapters"]["01"]["status"] == "pending"
    monkeypatch.delenv("FAKE_CLAUDE_MODE")
    rep = orchestrator.run(cfg, max_steps=1, echo=lambda *_: None)
    assert rep.steps == [f"{b['book_id']}: S4 draft ch 1"]


def test_cli_error_retries_once_then_stops(cfg, approved_series, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_MODE", "error")
    rep = orchestrator.run(cfg, echo=lambda *_: None)
    assert "CLI error" in rep.stop_reason
    assert len([c for c in calls(cfg.paths.root) if "S3" in c]) == 2


def test_critique_fail_then_revise(cfg, approved_series, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_MODE", "critique_fail")
    orchestrator.run(cfg, max_steps=5, echo=lambda *_: None)
    b = state.load_book(cfg, f"{approved_series}-b01")
    ch = b["chapters"]["01"]
    assert ch["revisions"] == 1 and ch["status"] == "passed"
    hist = [h["event"] for h in b["history"]]
    assert "done: S6 revise ch 1" in hist


def test_needs_owner_after_two_revisions(cfg, approved_series, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_MODE", "critique_always_fail")
    orchestrator.run(cfg, max_steps=7, echo=lambda *_: None)
    ch = state.load_book(cfg, f"{approved_series}-b01")["chapters"]["01"]
    assert ch["revisions"] == 2 and "needs-owner" in ch["flags"] and ch["status"] == "passed"


def test_continuity_error_fixed_once(cfg, approved_series, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_MODE", "continuity_error")
    orchestrator.run(cfg, book_id=f"{approved_series}-b01", echo=lambda *_: None)
    b = state.load_book(cfg, f"{approved_series}-b01")
    assert b["status"] == "review"
    assert b["chapters"]["02"]["continuity_fixes"]


def test_unfixable_continuity_blocks_and_moves_on(cfg, approved_series, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_MODE", "continuity_always")
    rep = orchestrator.run(cfg, book_id=f"{approved_series}-b01", echo=lambda *_: None)
    b = state.load_book(cfg, f"{approved_series}-b01")
    assert b["status"] == "blocked" and rep.blocked


def test_bad_outline_blocks_after_retry(cfg, approved_series, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_MODE", "bad_outline")
    rep = orchestrator.run(cfg, echo=lambda *_: None)
    b = state.load_book(cfg, f"{approved_series}-b01")
    assert b["status"] == "blocked" and "outline" in b["errors"][0]
    assert len([c for c in calls(cfg.paths.root) if "S3" in c]) == 2  # one retry with the validation error
    assert rep.blocked


def test_owner_revision_round(cfg, approved_series, tmp_path):
    bid = f"{approved_series}-b01"
    orchestrator.run(cfg, book_id=bid, echo=lambda *_: None)
    notes = tmp_path / "notes.md"
    notes.write_text("Chapter 1: fewer smirks.")
    runner = CliRunner()
    assert runner.invoke(app, ["revise", bid, "--notes", str(notes)]).exit_code == 0
    orchestrator.run(cfg, book_id=bid, echo=lambda *_: None)
    b = state.load_book(cfg, bid)
    assert b["status"] == "review" and b["revision_round"] == 1
    hist = [h["event"] for h in b["history"]]
    assert "done: owner notes plan" in hist and hist.count("done: S6 revise ch 1") >= 1


def test_approve_and_publish_with_daily_cap(cfg, approved_series):
    orchestrator.run(cfg, echo=lambda *_: None)
    runner = CliRunner()
    bid = f"{approved_series}-b01"
    res = runner.invoke(app, ["approve", "book", bid])
    assert res.exit_code == 0, res.output
    # a second approval the same day is refused (1 upload per day)
    b2 = state.load_book(cfg, f"{approved_series}-b02")
    b2["status"] = "review"
    state.save_book(cfg, b2)
    res = runner.invoke(app, ["approve", "book", b2["book_id"]])
    assert res.exit_code == 1 and "limit" in res.output
    res = runner.invoke(app, ["published", bid, "--asin", "B0TEST"])
    assert res.exit_code == 0
    assert state.load_book(cfg, bid)["asin"] == "B0TEST"


def test_lock_prevents_overlap(cfg, approved_series):
    with orchestrator.run_lock(cfg):
        with pytest.raises(orchestrator.LockedError):
            orchestrator.run(cfg, echo=lambda *_: None)


def test_stale_lock_is_cleared(cfg, approved_series):
    (cfg.paths.state / "run.lock").write_text("999999")
    rep = orchestrator.run(cfg, max_steps=1, echo=lambda *_: None)
    assert len(rep.steps) == 1


def test_window(cfg):
    tz = ZoneInfo("Asia/Kolkata")
    assert not orchestrator.outside_window(cfg, datetime(2026, 10, 17, 3, 0, tzinfo=tz))
    assert orchestrator.outside_window(cfg, datetime(2026, 10, 17, 8, 30, tzinfo=tz))
    assert orchestrator.outside_window(cfg, datetime(2026, 10, 17, 0, 30, tzinfo=tz))


def test_atomic_write_leaves_no_temp(cfg, approved_series):
    orchestrator.run(cfg, max_steps=3, echo=lambda *_: None)
    assert not list(cfg.paths.series.rglob("*.tmp"))


def test_autopilot_picks_and_approves(cfg):
    result = series.autopilot(cfg)
    assert result["pick"] == 2
    assert state.load_series(cfg, result["series_id"])["status"] == "approved"
    assert len(result["books"]) == 3
    assert (cfg.paths.proposals / result["batch"] / "selection.json").exists()


def test_autopilot_respects_manual_approval(cfg):
    cfg.data["auto"]["approve_series"] = False
    result = series.autopilot(cfg)
    assert result["books"] == []
    assert state.load_series(cfg, result["series_id"])["status"] == "draft"


def test_cli_pick_auto_from_existing_batch(cfg):
    series.new_series(cfg)
    res = CliRunner().invoke(app, ["pick", "--auto"])
    assert res.exit_code == 0, res.output
    assert "Picked concept 2" in res.output and "Approved" in res.output


def test_beta_reader_triggers_one_revision_round(cfg, approved_series, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_MODE", "beta_always_revise")
    bid = f"{approved_series}-b01"
    orchestrator.run(cfg, book_id=bid, echo=lambda *_: None)
    b = state.load_book(cfg, bid)
    assert b["status"] == "review"
    assert b["beta_rounds"] == 1 and b["revision_round"] == 1
    hist = [h["event"] for h in b["history"]]
    assert hist.count("done: beta read") == 2 and "done: owner notes plan" in hist
    sheet = (cfg.paths.review / bid / "review.md").read_text()
    assert "Beta reader" in sheet and "revise" in sheet


def test_bonus_story_and_back_matter(cfg, approved_series):
    cfg.data["reader"]["signup_url"] = "https://example.com/join"
    bid = f"{approved_series}-b01"
    orchestrator.run(cfg, book_id=bid, echo=lambda *_: None)
    mdir = cfg.paths.series_dir(approved_series) / "magnet"
    assert (mdir / "bonus.md").exists() and (mdir / "bonus.epub").exists()
    md = (cfg.paths.book_dir(approved_series, bid) / "package" / "book.md").read_text()
    assert "Free bonus story" in md and "https://example.com/join" in md and "The Night He Chose" in md


def test_upload_prompt_and_publish_fills_launch_email(cfg, approved_series):
    from PIL import Image

    bid = f"{approved_series}-b01"
    orchestrator.run(cfg, book_id=bid, echo=lambda *_: None)
    runner = CliRunner()
    assert runner.invoke(app, ["approve", "book", bid]).exit_code == 0
    res = runner.invoke(app, ["upload", bid])
    assert res.exit_code == 1 and "cover.jpg" in res.output
    pkg = cfg.paths.book_dir(approved_series, bid) / "package"
    Image.new("RGB", (1600, 2560)).save(pkg / "cover.jpg")
    res = runner.invoke(app, ["upload", bid])
    assert res.exit_code == 0 and "Stop before" in res.output and "Never type passwords" in res.output
    res = runner.invoke(app, ["published", bid, "--asin", "B0TEST"])
    assert res.exit_code == 0
    email = (cfg.paths.review / bid / "launch-email-ready.md").read_text()
    assert "https://www.amazon.com/dp/B0TEST" in email


def test_site_build(cfg, approved_series):
    from factory import site

    cfg.data["reader"]["signup_url"] = "https://example.com/join"
    bid = f"{approved_series}-b01"
    orchestrator.run(cfg, book_id=bid, echo=lambda *_: None)
    b = state.load_book(cfg, bid)
    b.update(status="published", asin="B0TEST")
    state.save_book(cfg, b)
    dist = site.build(cfg)
    index = (dist / "index.html").read_text()
    assert "https://www.amazon.com/dp/B0TEST" in index and "The Ink Oath" in index
    assert (dist / "about.html").exists() and (dist / "bonus.html").exists()


def test_time_budget_stops_cleanly(cfg, approved_series):
    rep = orchestrator.run(cfg, max_minutes=0.0001, echo=lambda *_: None)
    assert "time budget" in rep.stop_reason
