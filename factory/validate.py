"""Automatic checks each stage must pass (PRD sections 5 and 6)."""

import re
from collections import Counter

from .config import Config
from .fsutil import read_text, word_count
from .parse import OutputError, marker_list

OUTLINE_FIELDS = ("pov", "goal", "value_shift", "reader_question_out", "techniques")


# ---------- style ----------

def style_lists(cfg: Config) -> tuple[list[str], list[str]]:
    guide = read_text(cfg.paths.canon / "style-guide.md")
    return marker_list(guide, "banned"), marker_list(guide, "aitells")


def _count(text_lower: str, phrase: str) -> int:
    return len(re.findall(r"(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", text_lower))


def style_report(cfg: Config, text: str) -> dict:
    banned, tells = style_lists(cfg)
    lower = text.lower().replace("’", "'")
    words = max(word_count(text), 1)
    banned_hits = {p: n for p in banned if (n := _count(lower, p))}
    tell_hits = {p: n for p in tells if (n := _count(lower, p))}
    tokens = re.findall(r"[a-z']+", lower)
    grams = Counter(" ".join(tokens[i : i + 4]) for i in range(len(tokens) - 3))
    top_gram, top_n = grams.most_common(1)[0] if grams else ("", 0)
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip() and not p.lstrip().startswith("#")]
    longest = max((word_count(p) for p in paragraphs), default=0)
    return {
        "words": words,
        "banned_hits": banned_hits,
        "ai_tell_hits": tell_hits,
        "ai_tells_per_1000": round(sum(tell_hits.values()) * 1000 / words, 2),
        "top_4gram": top_gram,
        "top_4gram_count": top_n,
        "longest_paragraph_words": longest,
        "em_dashes_per_1000": round(text.count("—") * 1000 / words, 2),
    }


def style_problems(cfg: Config, report: dict) -> list[str]:
    limits = cfg.get("style_limits", {})
    problems = []
    if sum(report["banned_hits"].values()) > limits.get("banned_phrase_hits", 0):
        problems.append(f"banned phrases present: {report['banned_hits']}")
    if report["ai_tells_per_1000"] > limits.get("ai_tells_per_1000_words", 1.0):
        problems.append(f"AI tells at {report['ai_tells_per_1000']} per 1,000 words: {report['ai_tell_hits']}")
    if report["top_4gram_count"] > limits.get("max_repeated_4gram", 3):
        problems.append(f"phrase repeated {report['top_4gram_count']} times: '{report['top_4gram']}'")
    if report.get("em_dashes_per_1000", 0) > limits.get("em_dashes_per_1000_words", 4):
        problems.append(f"{report['em_dashes_per_1000']} em dashes per 1,000 words (limit 4)")
    if report["longest_paragraph_words"] > limits.get("max_paragraph_words", 220):
        problems.append(f"paragraph of {report['longest_paragraph_words']} words (monologue guard)")
    return problems


# ---------- outline ----------

def outline(cfg: Config, data: dict) -> list[str]:
    errors = []
    chapters = data.get("chapters") or []
    lo, hi = cfg.get("book.chapters_min", 30), cfg.get("book.chapters_max", 34)
    if not lo <= len(chapters) <= hi:
        errors.append(f"outline has {len(chapters)} chapters; need {lo} to {hi}")
    for i, ch in enumerate(chapters, start=1):
        if ch.get("n") != i:
            errors.append(f"chapter {i} has n={ch.get('n')}; number chapters 1..N in order")
        for f in OUTLINE_FIELDS:
            if not ch.get(f):
                errors.append(f"chapter {i} is missing '{f}'")
        if ch.get("techniques") and not all(isinstance(t, int) and 1 <= t <= 26 for t in ch["techniques"]):
            errors.append(f"chapter {i} techniques must be numbers 1 to 26")
    for key in ("title", "central_question", "midpoint_chapter"):
        if not data.get(key):
            errors.append(f"outline.json is missing '{key}'")
    if chapters and 26 not in (chapters[-1].get("techniques") or []):
        errors.append("final chapter must use technique 26 (Series Hinge)")
    return errors


# ---------- chapters ----------

def chapter_target(cfg: Config, beat: dict) -> int:
    lo, hi = cfg.get("book.chapter_words_min", 2500), cfg.get("book.chapter_words_max", 3000)
    return int(beat.get("target_words") or (lo + hi) // 2)


def chapter_draft(cfg: Config, text: str, n: int, target: int) -> list[str]:
    errors = []
    if not re.match(rf"#\s*Chapter\s+{n}\b", text.strip()):
        errors.append(f"chapter must start with '# Chapter {n}: <title>'")
    words = word_count(text)
    tol = cfg.get("book.length_tolerance", 0.2)
    if not target * (1 - tol) <= words <= target * (1 + tol):
        errors.append(f"chapter has {words} words; target {target} ±{int(tol * 100)}%")
    banned, _ = style_lists(cfg)
    lower = text.lower().replace("’", "'")
    hits = [p for p in banned if _count(lower, p)]
    if hits:
        errors.append(f"banned phrases: {', '.join(hits)}")
    return errors


# ---------- critique ----------

def critique(cfg: Config, data: dict) -> dict:
    """Normalise critic JSON and decide pass/fail (PRD section 6)."""
    criteria = cfg.get("quality.criteria", [])
    scores = data.get("scores")
    if not isinstance(scores, dict):
        raise OutputError("critique JSON needs a 'scores' object")
    missing = [c for c in criteria if c not in scores]
    if missing:
        raise OutputError(f"critique is missing scores for: {', '.join(missing)}")
    clean = {}
    for c in criteria:
        try:
            v = float(scores[c])
        except (TypeError, ValueError) as exc:
            raise OutputError(f"score for {c} must be a number 1 to 5") from exc
        if c == "continuity":
            if v not in (0, 5):
                raise OutputError("continuity is scored 0 or 5 only")
        elif not 1 <= v <= 5:
            raise OutputError(f"score for {c} must be 1 to 5")
        clean[c] = v
    fixes = data.get("fixes") or []
    if not isinstance(fixes, list):
        raise OutputError("'fixes' must be a list")
    average = round(sum(clean.values()) / len(clean), 2)
    minimum = min(clean.values())
    violation = bool(data.get("content_rule_violation"))
    passed = (
        average >= cfg.get("quality.pass_average", 3.5)
        and minimum >= cfg.get("quality.pass_minimum", 3)
        and not violation
    )
    return {
        "scores": clean,
        "reasons": data.get("reasons") or {},
        "fixes": fixes[:3],
        "reader_question": data.get("reader_question", ""),
        "techniques_landed": data.get("techniques_landed", []),
        "new_facts_assessment": data.get("new_facts_assessment", ""),
        "content_rule_violation": violation,
        "failure_modes": data.get("failure_modes", []),
        "average": average,
        "minimum": minimum,
        "passed": passed,
    }


# ---------- series / package ----------

def proposals(data: dict, count: int) -> list[str]:
    errors = []
    concepts = data.get("concepts") or []
    if len(concepts) != count:
        errors.append(f"need exactly {count} concepts, got {len(concepts)}")
    for i, c in enumerate(concepts, start=1):
        tests = c.get("originality") or []
        if len(tests) != 8:
            errors.append(f"concept {i} must score all 8 originality tests")
        elif not all(t.get("pass") for t in tests):
            failed = [t.get("test") for t in tests if not t.get("pass")]
            errors.append(f"concept {i} fails originality tests {failed}; replace or rework it")
        for key in ("slug", "title", "premise", "books"):
            if not c.get(key):
                errors.append(f"concept {i} is missing '{key}'")
    return errors


BIBLE_HEADINGS = ("world rules", "cast", "relationship worksheet", "book arcs", "secret map", "cover style")


def bible(cfg: Config, bible_md: str, series: dict) -> list[str]:
    errors = []
    lower = bible_md.lower()
    for h in BIBLE_HEADINGS:
        if not re.search(rf"^#+\s*{h}", lower, re.MULTILINE):
            errors.append(f"bible.md needs a '## {h.title()}' section")
    if "cost" not in lower:
        errors.append("world rules must state their costs")
    books = series.get("books") or []
    lo, hi = cfg.get("series.books_min", 3), cfg.get("series.books_max", 6)
    if not lo <= len(books) <= hi:
        errors.append(f"series.json needs {lo} to {hi} books, got {len(books)}")
    for b in books:
        for key in ("number", "working_title", "central_question"):
            if not b.get(key):
                errors.append(f"series.json book {b.get('number')} is missing '{key}'")
    return errors


METADATA_FIELDS = ("title", "series_name", "series_number", "pen_name", "description", "keywords",
                   "categories", "age_notes", "heat_notes", "price_usd", "language")


def metadata(cfg: Config, data: dict) -> list[str]:
    errors = [f"metadata.json is missing '{k}'" for k in METADATA_FIELDS if data.get(k) in (None, "", [])]
    kw = data.get("keywords") or []
    if len(kw) != cfg.get("packaging.keyword_count", 7):
        errors.append(f"need {cfg.get('packaging.keyword_count', 7)} keywords, got {len(kw)}")
    for k in kw:
        if len(k) > cfg.get("packaging.keyword_max_chars", 50):
            errors.append(f"keyword too long: {k}")
    cats = data.get("categories") or []
    if len(cats) != cfg.get("packaging.category_count", 3):
        errors.append(f"need {cfg.get('packaging.category_count', 3)} categories, got {len(cats)}")
    return errors


def blurb(cfg: Config, html: str) -> list[str]:
    limit = cfg.get("packaging.blurb_max_chars", 4000)
    errors = []
    if len(html) > limit:
        errors.append(f"blurb is {len(html)} characters; KDP limit is {limit}")
    if "<p>" not in html and "<b>" not in html:
        errors.append("blurb must be HTML-formatted for KDP (use <p>, <b>, <i>)")
    return errors
