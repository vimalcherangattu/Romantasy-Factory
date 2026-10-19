"""Run state: one JSON file per book and per series, plus a SQLite index for `factory status`."""

import sqlite3
from datetime import datetime
from pathlib import Path

from .config import Config
from .fsutil import read_json, write_json

BOOK_STATUSES = ("queued", "in_progress", "blocked", "review", "revising", "approved", "published")


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def book_path(cfg: Config, book_id: str) -> Path:
    return cfg.paths.state / f"{book_id}.json"


def series_path(cfg: Config, series_id: str) -> Path:
    return cfg.paths.state / f"series-{series_id}.json"


def new_book(series_id: str, book_id: str, number: int, title: str = "") -> dict:
    return {
        "book_id": book_id,
        "series_id": series_id,
        "number": number,
        "title": title,
        "status": "queued",
        "stage": "S3",
        "done": [],
        "chapters": {},
        "chapter_count": 0,
        "flags": [],
        "errors": [],
        "revision_round": 0,
        "asin": None,
        "created_at": now(),
        "review_at": None,
        "approved_at": None,
        "published_at": None,
        "history": [],
    }


def load_book(cfg: Config, book_id: str) -> dict:
    data = read_json(book_path(cfg, book_id))
    if data is None:
        raise KeyError(f"No book state for {book_id}")
    return data


def save_book(cfg: Config, book: dict) -> None:
    book["updated_at"] = now()
    write_json(book_path(cfg, book["book_id"]), book)
    _index(cfg, book)


def log(book: dict, event: str) -> None:
    book.setdefault("history", []).append({"at": now(), "event": event})


def chapter(book: dict, n: int) -> dict:
    key = f"{n:02d}"
    return book["chapters"].setdefault(key, {"status": "pending", "revisions": 0, "scores": {}, "average": None, "flags": []})


def pen_name(cfg: Config, series_id: str) -> str:
    """The series' pen name (set at pick time), else the config default."""
    data = read_json(series_path(cfg, series_id)) or {}
    return data.get("pen_name") or cfg.get("pen_name", "")


def load_series(cfg: Config, series_id: str) -> dict:
    data = read_json(series_path(cfg, series_id))
    if data is None:
        raise KeyError(f"No series state for {series_id}")
    return data


def save_series(cfg: Config, series: dict) -> None:
    series["updated_at"] = now()
    write_json(series_path(cfg, series["series_id"]), series)


def all_series(cfg: Config) -> list[dict]:
    return [read_json(p) for p in sorted(cfg.paths.state.glob("series-*.json"))]


def all_books(cfg: Config) -> list[dict]:
    books = [read_json(p) for p in sorted(cfg.paths.state.glob("*.json")) if not p.name.startswith("series-")]
    return sorted((b for b in books if b and "book_id" in b), key=lambda b: (b["series_id"], b["number"]))


def _index(cfg: Config, book: dict) -> None:
    db = cfg.paths.state / "index.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS books (book_id TEXT PRIMARY KEY, series_id TEXT, number INTEGER, "
            "title TEXT, status TEXT, stage TEXT, chapters_passed INTEGER, needs_owner INTEGER, updated_at TEXT)"
        )
        chapters = book.get("chapters", {}).values()
        conn.execute(
            "INSERT OR REPLACE INTO books VALUES (?,?,?,?,?,?,?,?,?)",
            (
                book["book_id"], book["series_id"], book["number"], book.get("title", ""),
                book["status"], book.get("stage", ""),
                sum(1 for c in chapters if c["status"] in ("passed", "edited")),
                sum(1 for c in chapters if "needs-owner" in c.get("flags", [])),
                book.get("updated_at", ""),
            ),
        )
