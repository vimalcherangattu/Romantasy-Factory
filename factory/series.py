"""Series-level stages: S1 concepts, S2 bible, approval (PRD section 3, "Once per series")."""

import json
import re
from datetime import datetime
from pathlib import Path

from . import agentrun, state, validate
from .config import Config
from .fsutil import atomic_write, read_json, read_text, write_json
from .parse import json_text


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "series"


def new_series(cfg: Config) -> Path:
    """S1: write N concepts to series/_proposals/<batch>/."""
    count = cfg.get("series.proposals", 3)
    existing = [s.get("title", s["series_id"]) for s in state.all_series(cfg)]

    def check(files):
        try:
            data = json_text(files["proposals.json"], "proposals.json")
        except Exception as exc:  # noqa: BLE001 - reported to the agent
            return [str(exc)]
        return validate.proposals(data, count)

    expect = ["proposals.json"] + [f"concept-{i}.md" for i in range(1, count + 1)]
    files = agentrun.run(
        cfg, "concept",
        task=(f"Propose exactly {count} romantasy series concepts for the pen name "
              f"{cfg.get('pen_name')}. Series already in this pen name (don't repeat them): "
              f"{', '.join(existing) or 'none'}."),
        inputs={"taste.md": cfg.paths.taste},
        book_id="series", expect=expect, validator=check,
    )
    batch = datetime.now().strftime("%Y%m%d-%H%M")
    out = cfg.paths.proposals / batch
    for name, body in files.items():
        atomic_write(out / name, body)
    return out


def latest_batch(cfg: Config) -> Path | None:
    batches = sorted(p for p in cfg.paths.proposals.glob("*") if p.is_dir())
    return batches[-1] if batches else None


def pick(cfg: Config, concept: int, batch: str | None = None) -> str:
    """S2: build the bible draft for the chosen concept. Returns the new series id."""
    folder = cfg.paths.proposals / batch if batch else latest_batch(cfg)
    if not folder or not folder.exists():
        raise FileNotFoundError("No proposals found. Run `factory new-series` first.")
    proposals = json.loads(read_text(folder / "proposals.json"))
    meta = proposals["concepts"][concept - 1]
    concept_md = read_text(folder / f"concept-{concept}.md")  # owner may have edited it
    index = len(state.all_series(cfg)) + 1
    series_id = f"s{index:02d}-{_slug(meta.get('slug') or meta['title'])}"

    def check(files):
        try:
            series_json = json_text(files["series.json"], "series.json")
            json_text(files["continuity.json"], "continuity.json")
        except Exception as exc:  # noqa: BLE001
            return [str(exc)]
        return validate.bible(cfg, files["bible.md"], series_json)

    files = agentrun.run(
        cfg, "bible",
        task=f"Write the series bible for this approved concept. Pen name: {cfg.get('pen_name')}.",
        inputs={"concept.md": concept_md, "concept.json": json.dumps(meta, indent=2), "taste.md": cfg.paths.taste},
        book_id=series_id, expect=["bible.md", "continuity.json", "series.json"], validator=check,
    )
    sdir = cfg.paths.series_dir(series_id)
    atomic_write(sdir / "concept.md", concept_md)
    atomic_write(sdir / "bible.md", files["bible.md"])
    write_json(sdir / "continuity.json", json_text(files["continuity.json"]))
    series_json = json_text(files["series.json"])
    write_json(sdir / "series.json", series_json)
    state.save_series(cfg, {
        "series_id": series_id,
        "title": series_json.get("title", meta["title"]),
        "status": "draft",
        "proposal": f"{folder.name}/concept-{concept}",
        "books": [],
        "created_at": state.now(),
    })
    return series_id


def approve(cfg: Config, series_id: str) -> list[str]:
    """Owner approves the (edited) bible; creates a queued book per series.json entry."""
    series = state.load_series(cfg, series_id)
    sdir = cfg.paths.series_dir(series_id)
    series_json = read_json(sdir / "series.json")
    errors = validate.bible(cfg, read_text(sdir / "bible.md"), series_json or {})
    if errors:
        raise ValueError("Bible isn't ready: " + "; ".join(errors))
    book_ids = []
    for entry in sorted(series_json["books"], key=lambda b: b["number"]):
        book_id = f"{series_id}-b{int(entry['number']):02d}"
        book_ids.append(book_id)
        try:
            state.load_book(cfg, book_id)
        except KeyError:
            state.save_book(cfg, state.new_book(series_id, book_id, int(entry["number"]), entry.get("working_title", "")))
    series["status"] = "approved"
    series["books"] = book_ids
    series["approved_at"] = state.now()
    state.save_series(cfg, series)
    return book_ids


def auto_pick(cfg: Config, batch: str | None = None) -> tuple[int, dict]:
    """The selector agent picks a concept from a proposal batch, standing in for the owner."""
    folder = cfg.paths.proposals / batch if batch else latest_batch(cfg)
    if not folder or not folder.exists():
        raise FileNotFoundError("No proposals found. Run `factory new-series` first.")
    proposals = json.loads(read_text(folder / "proposals.json"))
    count = len(proposals["concepts"])
    inputs = {"taste.md": cfg.paths.taste, "proposals.json": folder / "proposals.json"}
    for i in range(1, count + 1):
        inputs[f"concept-{i}.md"] = folder / f"concept-{i}.md"

    def check(files):
        try:
            pick_n = json_text(files["selection.json"], "selection.json").get("pick")
        except Exception as exc:  # noqa: BLE001
            return [str(exc)]
        return [] if isinstance(pick_n, int) and 1 <= pick_n <= count else [f"'pick' must be 1 to {count}"]

    files = agentrun.run(
        cfg, "select",
        task=f"Choose one of these {count} series concepts for the pen name {cfg.get('pen_name')}.",
        inputs=inputs, book_id="series", expect=["selection.json"], validator=check,
    )
    selection = json_text(files["selection.json"])
    write_json(folder / "selection.json", selection)
    return selection["pick"], selection


def autopilot(cfg: Config, *, generate: bool = True, batch: str | None = None) -> dict:
    """S1 (optional) -> selector -> S2 -> approval, per config `auto.*`."""
    folder = new_series(cfg) if generate else (cfg.paths.proposals / batch if batch else latest_batch(cfg))
    n, selection = auto_pick(cfg, folder.name)
    series_id = pick(cfg, n, folder.name)
    result = {"batch": folder.name, "pick": n, "why": selection.get("why", ""), "series_id": series_id, "books": []}
    if cfg.get("auto.approve_series", True):
        result["books"] = approve(cfg, series_id)
    return result
