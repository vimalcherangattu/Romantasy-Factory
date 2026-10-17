"""Book-level pipeline: S3 to S10 plus book checks and the review sheet (PRD sections 5 and 6).

`next_step` returns the next unit of work for a book, so a run can stop after any step and
resume from state on the next run.
"""

import json
from datetime import date
from pathlib import Path
from typing import Callable

from . import agentrun, package, review, state, validate
from .config import Config
from .fsutil import atomic_write, read_json, read_text, word_count, write_json
from .parse import OutputError, json_text

FINAL_CHAPTER = ("passed", "edited")


class BookBlocked(RuntimeError):
    """The book can't continue without the owner. The run moves to the next book."""


class DailyQuotaReached(RuntimeError):
    """Today's review/upload quota is used; finish this step tomorrow."""


# ---------- paths and context ----------

def bdir(cfg: Config, book: dict) -> Path:
    return cfg.paths.book_dir(book["series_id"], book["book_id"])


def sdir(cfg: Config, book: dict) -> Path:
    return cfg.paths.series_dir(book["series_id"])


def chapter_path(cfg: Config, book: dict, n: int) -> Path:
    return bdir(cfg, book) / "chapters" / f"ch-{n:02d}.md"


def outline(cfg: Config, book: dict) -> dict:
    return read_json(bdir(cfg, book) / "outline.json", {}) or {}


def beat(cfg: Config, book: dict, n: int) -> dict:
    chapters = outline(cfg, book).get("chapters", [])
    return chapters[n - 1] if 0 < n <= len(chapters) else {}


def full_book(cfg: Config, book: dict) -> str:
    return "\n\n".join(read_text(chapter_path(cfg, book, n)) for n in range(1, book["chapter_count"] + 1))


def previous_summaries(cfg: Config, book: dict) -> str:
    parts = []
    for n in range(1, book["number"]):
        prev = cfg.paths.book_dir(book["series_id"], f"{book['series_id']}-b{n:02d}") / "summary.md"
        if prev.exists():
            parts.append(read_text(prev))
    return "\n\n".join(parts) or "(This is book 1. No previous books.)"


def series_entry(cfg: Config, book: dict, number: int | None = None) -> dict:
    series_json = read_json(sdir(cfg, book) / "series.json", {}) or {}
    number = number or book["number"]
    return next((b for b in series_json.get("books", []) if int(b.get("number", 0)) == number), {})


def _save_version(cfg: Config, book: dict, n: int) -> None:
    current = chapter_path(cfg, book, n)
    if current.exists():
        versions = current.parent / "versions"
        k = len(list(versions.glob(f"ch-{n:02d}.v*.md"))) + 1 if versions.exists() else 1
        atomic_write(versions / f"ch-{n:02d}.v{k}.md", read_text(current))


def _add_facts(cfg: Config, book: dict, n: int, facts_json: str) -> list:
    try:
        facts = json_text(facts_json, "new-facts.json").get("facts", [])
    except OutputError:
        facts = []
    atomic_write(bdir(cfg, book) / "chapters" / f"ch-{n:02d}.facts.json", json.dumps({"facts": facts}, indent=2))
    if facts:
        path = sdir(cfg, book) / "continuity.json"
        cont = read_json(path, {"facts": []})
        start = len(cont.setdefault("facts", [])) + 1
        for i, f in enumerate(facts):
            cont["facts"].append({"id": f"F{start + i:03d}", "category": f.get("category", ""), "fact": f.get("fact", ""),
                                  "since": f"{book['book_id']} ch {n}", "provisional": True})
        write_json(path, cont)
    return facts


# ---------- step selection ----------

Step = tuple[str, Callable[[Config, dict], None]]


def next_step(cfg: Config, book: dict) -> Step | None:
    if book["status"] in ("review", "approved", "published", "blocked"):
        return None
    done = set(book["done"])
    if "S3" not in done:
        return ("S3 outline", step_outline)
    if book.get("pending_owner_notes"):
        return ("owner notes plan", step_owner_plan)
    for n in range(1, book["chapter_count"] + 1):
        status = state.chapter(book, n)["status"]
        if status == "pending":
            return (f"S4 draft ch {n}", lambda c, b, n=n: step_draft(c, b, n))
        if status in ("drafted", "revised"):
            return (f"S5 critique ch {n}", lambda c, b, n=n: step_critique(c, b, n))
        if status in ("failed", "owner-revise", "continuity-fix"):
            return (f"S6 revise ch {n}", lambda c, b, n=n: step_revise(c, b, n))
    if "S7" not in done:
        return ("S7 continuity", step_continuity)
    if "book_check" not in done:
        return ("book-level checks", step_book_check)
    for n in range(1, book["chapter_count"] + 1):
        if state.chapter(book, n)["status"] == "passed":
            return (f"S8 line edit ch {n}", lambda c, b, n=n: step_line_edit(c, b, n))
    if "S9" not in done:
        return ("S9 summary", step_summary)
    if "S10" not in done:
        return ("S10 package", step_package)
    if "review" not in done:
        return ("review sheet", step_review)
    return None


def _done(book: dict, key: str) -> None:
    if key not in book["done"]:
        book["done"].append(key)


# ---------- S3 ----------

def step_outline(cfg: Config, book: dict) -> None:
    entry = series_entry(cfg, book)
    lo, hi = cfg.get("book.chapters_min"), cfg.get("book.chapters_max")

    def check(files):
        try:
            return validate.outline(cfg, json_text(files["outline.json"], "outline.json"))
        except OutputError as exc:
            return [str(exc)]

    try:
        files = agentrun.run(
            cfg, "outline",
            task=(f"Outline book {book['number']} of the series in {lo} to {hi} chapters of "
                  f"{cfg.get('book.chapter_words_min')} to {cfg.get('book.chapter_words_max')} words "
                  f"(about {cfg.get('book.target_words')} words in total). This book's entry: "
                  f"{json.dumps(entry)}"),
            inputs={
                "bible.md": sdir(cfg, book) / "bible.md",
                "continuity.json": sdir(cfg, book) / "continuity.json",
                "series.json": sdir(cfg, book) / "series.json",
                "previous-books-summaries.md": previous_summaries(cfg, book),
                "taste.md": cfg.paths.taste,
            },
            book_id=book["book_id"], expect=["outline.md", "outline.json"], validator=check,
        )
    except agentrun.StageFailed as exc:
        raise BookBlocked(f"outline failed validation twice: {exc}") from exc
    data = json_text(files["outline.json"])
    atomic_write(bdir(cfg, book) / "outline.md", files["outline.md"])
    write_json(bdir(cfg, book) / "outline.json", data)
    book["title"] = data.get("title") or book.get("title", "")
    book["chapter_count"] = len(data["chapters"])
    book["midpoint_chapter"] = int(data.get("midpoint_chapter") or book["chapter_count"] // 2)
    book["chapters"] = {}
    for n in range(1, book["chapter_count"] + 1):
        state.chapter(book, n)
    book["status"] = "in_progress"
    _done(book, "S3")


# ---------- S4 ----------

def _chapter_inputs(cfg: Config, book: dict, n: int) -> dict:
    prev = "\n\n".join(read_text(chapter_path(cfg, book, k)) for k in (n - 2, n - 1) if k >= 1) or "(First chapter.)"
    o = outline(cfg, book)
    return {
        "book.json": json.dumps({"title": o.get("title"), "logline": o.get("logline"),
                                 "central_question": o.get("central_question"),
                                 "chapter": n, "of": book["chapter_count"]}, indent=2),
        "this-chapter-beat.json": json.dumps(beat(cfg, book, n), indent=2),
        "next-chapter-beat.json": json.dumps(beat(cfg, book, n + 1) or {"note": "This is the final chapter."}, indent=2),
        "bible.md": sdir(cfg, book) / "bible.md",
        "continuity.json": sdir(cfg, book) / "continuity.json",
        "previous-two-chapters.md": prev,
    }


def _chapter_check(cfg: Config, n: int, target: int):
    def check(files):
        errors = validate.chapter_draft(cfg, files["chapter.md"], n, target)
        try:
            json_text(files["new-facts.json"], "new-facts.json")
        except OutputError as exc:
            errors.append(str(exc))
        return errors
    return check


def _write_chapter(cfg: Config, book: dict, n: int, files: dict) -> None:
    _save_version(cfg, book, n)
    atomic_write(chapter_path(cfg, book, n), files["chapter.md"])
    if "new-facts.json" in files:
        _add_facts(cfg, book, n, files["new-facts.json"])


def step_draft(cfg: Config, book: dict, n: int) -> None:
    ch = state.chapter(book, n)
    target = validate.chapter_target(cfg, beat(cfg, book, n))
    try:
        files = agentrun.run(
            cfg, "draft",
            task=f"Write chapter {n} of {book['chapter_count']}. Target length: {target} words.",
            inputs=_chapter_inputs(cfg, book, n),
            book_id=book["book_id"], expect=["chapter.md", "new-facts.json"],
            validator=_chapter_check(cfg, n, target),
        )
    except agentrun.StageFailed as exc:
        if not exc.files or "chapter.md" not in exc.files:
            raise BookBlocked(f"chapter {n} draft output malformed twice: {exc}") from exc
        files = exc.files
        ch["flags"].append(f"draft check: {exc}")
    _write_chapter(cfg, book, n, files)
    ch["status"] = "drafted"
    ch["words"] = word_count(files["chapter.md"])


# ---------- S5 ----------

def step_critique(cfg: Config, book: dict, n: int) -> None:
    ch = state.chapter(book, n)
    facts = read_text(bdir(cfg, book) / "chapters" / f"ch-{n:02d}.facts.json", '{"facts": []}')
    result: dict = {}

    def check(files):
        nonlocal result
        try:
            result = validate.critique(cfg, json_text(files["critique.json"], "critique.json"))
            return []
        except OutputError as exc:
            return [str(exc)]

    model = cfg.get("levers.recheck_critique_model") or None if ch["revisions"] else None
    prev = read_text(chapter_path(cfg, book, n - 1)) if n > 1 else "(First chapter.)"
    try:
        agentrun.run(
            cfg, "critique",
            task=f"Critique chapter {n} of {book['chapter_count']} against its beat.",
            inputs={
                "chapter.md": chapter_path(cfg, book, n),
                "this-chapter-beat.json": json.dumps(beat(cfg, book, n), indent=2),
                "new-facts-added-by-draft.json": facts,
                "bible.md": sdir(cfg, book) / "bible.md",
                "continuity.json": sdir(cfg, book) / "continuity.json",
                "previous-chapter.md": prev,
            },
            book_id=book["book_id"], expect=["critique.json"], validator=check, model=model,
        )
    except agentrun.StageFailed as exc:
        raise BookBlocked(f"critique for chapter {n} malformed twice: {exc}") from exc
    cdir = bdir(cfg, book) / "critique"
    write_json(cdir / f"ch-{n:02d}.json", result)
    write_json(cdir / f"ch-{n:02d}.r{ch['revisions']}.json", result)
    ch["scores"], ch["average"], ch["minimum"] = result["scores"], result["average"], result["minimum"]
    if result["content_rule_violation"]:
        ch["flags"].append("content-rule violation reported by critic")
    if result["passed"]:
        ch["status"] = "passed"
    elif ch["revisions"] >= cfg.get("quality.max_revisions", 2):
        ch["status"] = "passed"
        if "needs-owner" not in ch["flags"]:
            ch["flags"].append("needs-owner")
    else:
        ch["status"] = "failed"


# ---------- S6 ----------

def step_revise(cfg: Config, book: dict, n: int) -> None:
    ch = state.chapter(book, n)
    status = ch["status"]
    if status == "owner-revise":
        instructions, source = ch.get("owner_instructions", []), "the owner's revision notes"
    elif status == "continuity-fix":
        instructions, source = ch.get("continuity_fixes", []), "the continuity editor"
    else:
        crit = read_json(bdir(cfg, book) / "critique" / f"ch-{n:02d}.json", {})
        instructions, source = crit.get("fixes", []), "the critic"
    target = validate.chapter_target(cfg, beat(cfg, book, n))
    crit_file = bdir(cfg, book) / "critique" / f"ch-{n:02d}.json"
    try:
        files = agentrun.run(
            cfg, "revise",
            task=(f"Revise chapter {n} to address every fix instruction from {source}. "
                  f"Target length: {target} words."),
            inputs={
                "fix-instructions.json": json.dumps(instructions, indent=2),
                "critique.json": crit_file if crit_file.exists() else "(none)",
                "chapter.md": chapter_path(cfg, book, n),
                **{k: v for k, v in _chapter_inputs(cfg, book, n).items() if k != "previous-two-chapters.md"},
                "previous-chapter.md": read_text(chapter_path(cfg, book, n - 1)) if n > 1 else "(First chapter.)",
            },
            book_id=book["book_id"], expect=["chapter.md", "new-facts.json"],
            validator=_chapter_check(cfg, n, target),
        )
    except agentrun.StageFailed as exc:
        if not exc.files or "chapter.md" not in exc.files:
            raise BookBlocked(f"chapter {n} revision output malformed twice: {exc}") from exc
        files = exc.files
        ch["flags"].append(f"revise check: {exc}")
    _write_chapter(cfg, book, n, files)
    if status == "owner-revise":
        ch["revisions"] = 0
        ch["flags"] = [f for f in ch["flags"] if f != "needs-owner"]
    elif status == "failed":
        ch["revisions"] += 1
    ch["status"] = "revised"
    ch["words"] = word_count(files["chapter.md"])


# ---------- S7 ----------

def step_continuity(cfg: Config, book: dict) -> None:
    errors: list = []

    def check(files):
        nonlocal errors
        try:
            errors = json_text(files["errors.json"], "errors.json").get("open_errors", [])
            json_text(files["continuity.json"], "continuity.json")
            return []
        except OutputError as exc:
            return [str(exc)]

    try:
        files = agentrun.run(
            cfg, "continuity",
            task=f"Check this complete book ({book['chapter_count']} chapters) for continuity errors.",
            inputs={
                "bible.md": sdir(cfg, book) / "bible.md",
                "continuity.json": sdir(cfg, book) / "continuity.json",
                "outline.json": bdir(cfg, book) / "outline.json",
                "previous-books-summaries.md": previous_summaries(cfg, book),
                "book.md": full_book(cfg, book),
            },
            book_id=book["book_id"], expect=["errors.json", "continuity-report.md", "continuity.json"],
            validator=check,
        )
    except agentrun.StageFailed as exc:
        raise BookBlocked(f"continuity output malformed twice: {exc}") from exc
    atomic_write(bdir(cfg, book) / "continuity-report.md", files["continuity-report.md"])
    write_json(bdir(cfg, book) / "continuity-errors.json", {"open_errors": errors})
    if not errors:
        write_json(sdir(cfg, book) / "continuity.json", json_text(files["continuity.json"]))
        _done(book, "S7")
        return
    if book.get("continuity_attempts", 0) >= 1:
        raise BookBlocked("continuity errors remain after an automatic fix: "
                          + "; ".join(f"ch {e.get('chapter')}: {e.get('issue')}" for e in errors))
    book["continuity_attempts"] = book.get("continuity_attempts", 0) + 1
    fixable = [e for e in errors if isinstance(e.get("chapter"), int) and 1 <= e["chapter"] <= book["chapter_count"]]
    if not fixable:
        raise BookBlocked("continuity errors without a chapter to fix: " + json.dumps(errors))
    for e in fixable:
        ch = state.chapter(book, e["chapter"])
        ch.setdefault("continuity_fixes", []).append(f"{e.get('issue')} FIX: {e.get('fix')}")
        ch["status"] = "continuity-fix"


# ---------- book checks ----------

def step_book_check(cfg: Config, book: dict) -> None:
    def check(files):
        try:
            data = json_text(files["book-check.json"], "book-check.json")
            return [] if isinstance(data.get("checks"), list) and data["checks"] else ["book-check.json needs a 'checks' list"]
        except OutputError as exc:
            return [str(exc)]

    try:
        files = agentrun.run(
            cfg, "book_check",
            task="Run the book-level checks on this finished book.",
            inputs={"outline.json": bdir(cfg, book) / "outline.json", "book.md": full_book(cfg, book)},
            book_id=book["book_id"], expect=["book-check.json"], validator=check,
        )
    except agentrun.StageFailed as exc:
        raise BookBlocked(f"book-check output malformed twice: {exc}") from exc
    data = json_text(files["book-check.json"])
    write_json(bdir(cfg, book) / "book-check.json", data)
    book["flags"] = [f for f in book["flags"] if not f.startswith("book-check:")]
    for c in data["checks"]:
        if not c.get("pass"):
            book["flags"].append(f"book-check: {c.get('name')} failed ({c.get('evidence', '')})")
    _done(book, "book_check")


# ---------- S8 ----------

def step_line_edit(cfg: Config, book: dict, n: int) -> None:
    ch = state.chapter(book, n)
    original = read_text(chapter_path(cfg, book, n))
    original_words = word_count(original)

    def problems(text: str) -> list[str]:
        errs = validate.style_problems(cfg, validate.style_report(cfg, text))
        if not text.strip().lower().startswith(f"# chapter {n}"):
            errs.append(f"keep the heading '# Chapter {n}: ...'")
        if abs(word_count(text) - original_words) > original_words * 0.10:
            errs.append(f"length changed from {original_words} to {word_count(text)} words; stay within 5%")
        return errs

    try:
        files = agentrun.run(
            cfg, "line_edit",
            task=f"Line-edit chapter {n}. Current style report: "
                 f"{json.dumps(validate.style_report(cfg, original))}",
            inputs={"chapter.md": original},
            book_id=book["book_id"], expect=["chapter.md"],
            validator=lambda f: problems(f["chapter.md"]),
        )
        text = files["chapter.md"]
    except agentrun.StageFailed as exc:
        candidate = (exc.files or {}).get("chapter.md")
        # Keep whichever version has fewer problems, and flag the rest for the owner.
        text = candidate if candidate and len(problems(candidate)) <= len(problems(original)) else original
        ch["flags"].append("style: " + "; ".join(problems(text)))
    _save_version(cfg, book, n)
    atomic_write(chapter_path(cfg, book, n), text)
    ch["style"] = validate.style_report(cfg, text)
    ch["words"] = word_count(text)
    ch["status"] = "edited"


# ---------- S9 ----------

def step_summary(cfg: Config, book: dict) -> None:
    limit = cfg.get("book.summary_max_words", 1500)
    series_clues = [c for c in outline(cfg, book).get("clues", []) if str(c.get("payoff")) == "series"]

    def check(files):
        text = files["summary.md"]
        errs = []
        if word_count(text) > limit:
            errs.append(f"summary has {word_count(text)} words; limit {limit}")
        if "## open threads" not in text.lower():
            errs.append("summary needs a '## Open threads' section")
        return errs

    try:
        files = agentrun.run(
            cfg, "summary",
            task=f"Summarise this finished book for the next book's agents. Series threads to include: "
                 f"{json.dumps(series_clues)}",
            inputs={"outline.json": bdir(cfg, book) / "outline.json",
                    "book-check.json": bdir(cfg, book) / "book-check.json",
                    "book.md": full_book(cfg, book)},
            book_id=book["book_id"], expect=["summary.md"], validator=check,
        )
    except agentrun.StageFailed as exc:
        raise BookBlocked(f"summary failed validation twice: {exc}") from exc
    atomic_write(bdir(cfg, book) / "summary.md", files["summary.md"])
    _done(book, "S9")


# ---------- S10 ----------

def step_package(cfg: Config, book: dict) -> None:
    defaults = {
        "pen_name": cfg.get("pen_name"),
        "series_number": book["number"],
        "price_usd": cfg.get("packaging.default_price_usd"),
        "language": cfg.get("packaging.language"),
        "kdp_select": cfg.get("packaging.kdp_select"),
    }

    def check(files):
        try:
            errs = validate.metadata(cfg, json_text(files["metadata.json"], "metadata.json"))
        except OutputError as exc:
            errs = [str(exc)]
        return errs + validate.blurb(cfg, files["blurb.md"])

    next_entry = series_entry(cfg, book, book["number"] + 1)
    try:
        files = agentrun.run(
            cfg, "package",
            task=f"Write the store material for this book. Fixed values: {json.dumps(defaults)}. "
                 f"Next book in the series: {json.dumps(next_entry) if next_entry else 'none (last book)'}.",
            inputs={
                "series.json": sdir(cfg, book) / "series.json",
                "bible.md": sdir(cfg, book) / "bible.md",
                "outline.json": bdir(cfg, book) / "outline.json",
                "summary.md": bdir(cfg, book) / "summary.md",
                "chapter-01.md": chapter_path(cfg, book, 1),
            },
            book_id=book["book_id"], expect=["metadata.json", "blurb.md", "cover-prompt.md", "teaser.md"],
            validator=check,
        )
    except agentrun.StageFailed as exc:
        raise BookBlocked(f"package material failed validation twice: {exc}") from exc
    meta = json_text(files["metadata.json"])
    meta.update({k: v for k, v in defaults.items() if k in ("pen_name", "series_number")})
    files["metadata.json"] = json.dumps(meta, indent=2, ensure_ascii=False)
    result = package.build(cfg, book, files)
    book["package"] = result
    book["flags"] = [f for f in book["flags"] if not f.startswith("package:")]
    for problem in result.get("problems", []):
        book["flags"].append(f"package: {problem}")
    _done(book, "S10")


# ---------- review ----------

def reviews_today(cfg: Config) -> int:
    today = date.today().isoformat()
    return sum(1 for b in state.all_books(cfg) if (b.get("review_at") or "").startswith(today))


def step_review(cfg: Config, book: dict) -> None:
    if reviews_today(cfg) >= cfg.get("schedule.books_per_day", 1):
        raise DailyQuotaReached(f"{cfg.get('schedule.books_per_day', 1)} book(s) already staged for review today")
    review.build_sheet(cfg, book)
    book["status"] = "review"
    book["review_at"] = state.now()
    _done(book, "review")


# ---------- owner revision ----------

def step_owner_plan(cfg: Config, book: dict) -> None:
    notes_path = Path(book["pending_owner_notes"])

    def check(files):
        try:
            plan = json_text(files["plan.json"], "plan.json")
        except OutputError as exc:
            return [str(exc)]
        bad = [c.get("n") for c in plan.get("chapters", []) if not (isinstance(c.get("n"), int)
                                                                     and 1 <= c["n"] <= book["chapter_count"])]
        return [f"chapter numbers out of range: {bad}"] if bad else []

    titles = [{"n": c.get("n"), "title": c.get("title")} for c in outline(cfg, book).get("chapters", [])]
    try:
        files = agentrun.run(
            cfg, "owner_notes",
            task="Turn the owner's notes into a chapter-by-chapter revision plan.",
            inputs={"owner-notes.md": notes_path, "chapter-titles.json": json.dumps(titles, indent=2),
                    "outline.md": bdir(cfg, book) / "outline.md", "summary.md": bdir(cfg, book) / "summary.md"},
            book_id=book["book_id"], expect=["plan.json"], validator=check,
        )
    except agentrun.StageFailed as exc:
        raise BookBlocked(f"owner notes plan malformed twice: {exc}") from exc
    plan = json_text(files["plan.json"])
    write_json(bdir(cfg, book) / f"owner-plan-{book['revision_round']}.json", plan)
    for item in plan.get("chapters", []):
        ch = state.chapter(book, item["n"])
        ch["owner_instructions"] = item.get("instructions", [])
        ch["status"] = "owner-revise"
    book["done"] = [d for d in book["done"] if d in ("S3",)]
    book["continuity_attempts"] = 0
    book["pending_owner_notes"] = None
