"""KDP weekly title limit (in force from 21 Sep 2026).

KDP lets one account create at most 2 new titles per format (ebook, paperback, hardcover)
per week; the week resets Sunday 00:00 UTC. The limit is per account, shared by every pen
name and by the owner's other books, so all of them are logged in state/kdp-ledger.csv.

Rows are "used" (a title was created on KDP) or "reserved" (a slot held for a planned book
in that week). Both count against the week.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone

from .config import Config
from . import fsutil, state

FORMATS = ("ebook", "paperback", "hardcover")
FIELDS = ("week_start", "date", "kind", "format", "book", "note")


def week_start(when: datetime | None = None) -> datetime:
    """Sunday 00:00 UTC of the KDP week containing `when`."""
    when = (when or datetime.now(timezone.utc)).astimezone(timezone.utc)
    sunday = when - timedelta(days=(when.weekday() + 1) % 7)
    return sunday.replace(hour=0, minute=0, second=0, microsecond=0)


def _path(cfg: Config):
    return cfg.paths.state / "kdp-ledger.csv"


def rows(cfg: Config) -> list[dict]:
    p = _path(cfg)
    if not p.exists():
        return []
    with p.open(newline="") as f:
        return list(csv.DictReader(f))


def _write(cfg: Config, data: list[dict]) -> None:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    for r in sorted(data, key=lambda r: (r["week_start"], r["date"])):
        w.writerow({k: r.get(k, "") for k in FIELDS})
    fsutil.atomic_write(_path(cfg), buf.getvalue())


def limit(cfg: Config) -> int:
    return int(cfg.get("kdp.titles_per_format_per_week", 2))


def used(cfg: Config, fmt: str, week: datetime | None = None) -> list[dict]:
    ws = week_start(week).date().isoformat()
    return [r for r in rows(cfg) if r["week_start"] == ws and r["format"] == fmt]


def slots_left(cfg: Config, fmt: str, week: datetime | None = None, book: str | None = None) -> int:
    """Free slots this week. A reservation for `book` itself is counted as free for it."""
    taken = [r for r in used(cfg, fmt, week) if not (book and r["kind"] == "reserved" and r["book"] == book)]
    return limit(cfg) - len(taken)


def factory_slots_left(cfg: Config, fmt: str, week: datetime | None = None) -> int:
    """Slots the factory may still use this week: its own share, and never more than are free.

    The rest of the weekly limit is kept for the owner's other books (parenting series and so on)."""
    ids = {b["book_id"] for b in state.all_books(cfg)}
    mine = [r for r in used(cfg, fmt, week) if r["book"] in ids and r["kind"] == "used"]
    share = int(cfg.get("kdp.factory_slots_per_week", 1)) - len(mine)
    return min(share, slots_left(cfg, fmt, week))


def record(cfg: Config, book: str, formats: list[str], kind: str = "used",
           when: datetime | None = None, note: str = "") -> None:
    """Log a title creation (or a reservation) for each format. A use replaces that book's reservation."""
    when = (when or datetime.now(timezone.utc)).astimezone(timezone.utc)
    ws = week_start(when).date().isoformat()
    data = rows(cfg)
    for fmt in formats:
        if fmt not in FORMATS:
            raise ValueError(f"format must be one of {FORMATS}")
        data = [r for r in data if not (r["book"] == book and r["format"] == fmt and r["kind"] == "reserved")]
        data.append({"week_start": ws, "date": when.date().isoformat(), "kind": kind,
                     "format": fmt, "book": book, "note": note})
    _write(cfg, data)


def ready_buffer(cfg: Config) -> list[str]:
    """Factory books finished but not yet live (review or approved)."""
    return [b["book_id"] for b in state.all_books(cfg) if b["status"] in ("review", "revising", "approved")]


def buffer_full(cfg: Config) -> bool:
    return len(ready_buffer(cfg)) >= int(cfg.get("kdp.max_ready_buffer", 3))


def plan(cfg: Config, weeks: int = 6) -> str:
    """Text table of ebook/paperback slots for this and the coming weeks."""
    out = [f"KDP weekly limit: {limit(cfg)} new titles per format, week resets Sunday 00:00 UTC "
           f"(05:30 IST).", ""]
    start = week_start()
    for i in range(weeks):
        wk = start + timedelta(weeks=i)
        out.append(f"Week of {wk.date().isoformat()}:")
        for fmt in ("ebook", "paperback"):
            us = used(cfg, fmt, wk)
            names = ", ".join(f"{r['book']}{' (reserved)' if r['kind'] == 'reserved' else ''}" for r in us) or "-"
            out.append(f"  {fmt:<9} {len(us)}/{limit(cfg)}  {names}")
    buf = ready_buffer(cfg)
    out += ["", f"Factory books ready or in review: {len(buf)} (cap {cfg.get('kdp.max_ready_buffer', 3)})"
            + (f": {', '.join(buf)}" if buf else "")]
    return "\n".join(out)
