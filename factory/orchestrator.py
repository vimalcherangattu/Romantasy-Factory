"""The nightly run: pick the next unfinished book, run its next step, save, repeat (PRD sections 3 and 9)."""

import os
from contextlib import contextmanager
from datetime import datetime, time
from zoneinfo import ZoneInfo

from . import book as bookmod
from . import gitops, report, state
from .claude import ClaudeError, UsageLimitError
from .config import Config
from .fsutil import atomic_write

ACTIVE = ("in_progress", "revising")


class LockedError(RuntimeError):
    pass


@contextmanager
def run_lock(cfg: Config):
    """One run at a time. A lock left by a dead process is cleared."""
    path = cfg.paths.state / "run.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            pid = int(path.read_text().strip() or 0)
            os.kill(pid, 0)
            raise LockedError(f"another run is active (pid {pid})")
        except (ValueError, ProcessLookupError, PermissionError):
            path.unlink(missing_ok=True)
    atomic_write(path, str(os.getpid()))
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def _hhmm(text: str) -> time:
    h, m = text.split(":")
    return time(int(h), int(m))


def outside_window(cfg: Config, now: datetime | None = None) -> bool:
    """True between stop_by (08:00) and the next start (01:00), in the configured timezone."""
    tz = ZoneInfo(cfg.get("timezone", "Asia/Kolkata"))
    now = (now or datetime.now(tz)).astimezone(tz).time()
    start, stop = _hhmm(cfg.get("schedule.start", "01:00")), _hhmm(cfg.get("schedule.stop_by", "08:00"))
    return stop <= now < start if stop < start else not (start <= now < stop)


def pick_book(cfg: Config, only: str | None, skip: set[str]) -> dict | None:
    books = state.all_books(cfg)
    if only:
        b = next((b for b in books if b["book_id"] == only), None)
        return b if b and b["book_id"] not in skip and bookmod.next_step(cfg, b) else None
    approved = {s["series_id"] for s in state.all_series(cfg) if s["status"] == "approved"}
    books = [b for b in books if b["series_id"] in approved and b["book_id"] not in skip]
    for b in books:
        if b["status"] in ACTIVE and bookmod.next_step(cfg, b):
            return b
    by_id = {b["book_id"]: b for b in state.all_books(cfg)}
    for b in books:
        if b["status"] != "queued":
            continue
        prev = by_id.get(f"{b['series_id']}-b{b['number'] - 1:02d}")
        if b["number"] == 1 or (prev and prev["status"] in ("review", "approved", "published")):
            return b
    return None


def run(cfg: Config, *, book_id: str | None = None, max_steps: int | None = None,
        scheduled: bool = False, echo=print) -> report.RunReport:
    rep = report.RunReport()
    skip: set[str] = set()
    with run_lock(cfg):
        while True:
            if scheduled and outside_window(cfg):
                rep.stop_reason = f"reached stop time {cfg.get('schedule.stop_by')}"
                break
            b = pick_book(cfg, book_id, skip)
            if not b:
                rep.stop_reason = rep.stop_reason or "no work left"
                break
            name, fn = bookmod.next_step(cfg, b)
            label = f"{b['book_id']}: {name}"
            echo(f"→ {label}")
            try:
                fn(cfg, b)
            except UsageLimitError as exc:
                state.log(b, f"usage limit during {name}")
                state.save_book(cfg, b)
                rep.stop_reason = f"usage limit reached during {label}; resumes next run ({exc})"
                break
            except ClaudeError as exc:
                state.log(b, f"CLI error during {name}: {exc}")
                state.save_book(cfg, b)
                rep.stop_reason = f"claude CLI error during {label} after one retry: {exc}"
                break
            except bookmod.DailyQuotaReached as exc:
                state.save_book(cfg, b)
                rep.stop_reason = f"daily quota: {exc}"
                break
            except bookmod.BookBlocked as exc:
                b["status"] = "blocked"
                b.setdefault("errors", []).append(str(exc))
                state.log(b, f"blocked at {name}: {exc}")
                state.save_book(cfg, b)
                gitops.commit(cfg, f"{b['book_id']}: blocked at {name}")
                rep.blocked.append(f"{b['book_id']} at {name}: {exc}")
                skip.add(b["book_id"])
                continue
            state.log(b, f"done: {name}")
            state.save_book(cfg, b)
            gitops.commit(cfg, label)
            rep.steps.append(label)
            if b["status"] == "review":
                rep.ready.append(b["book_id"])
            if max_steps and len(rep.steps) >= max_steps:
                rep.stop_reason = f"step limit ({max_steps}) reached"
                break
        rep.finished = datetime.now()
        path = report.write(cfg, rep)
        gitops.commit(cfg, f"report {rep.started:%Y-%m-%d %H:%M}")
        echo(f"Report: {path}")
    return rep
