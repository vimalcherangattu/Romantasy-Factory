"""Owner review sheet: review/<book-id>/review.md (PRD section 6)."""

import shutil

from .config import Config
from .fsutil import atomic_write, read_json, read_text


def build_sheet(cfg: Config, book: dict) -> str:
    bdir = cfg.paths.book_dir(book["series_id"], book["book_id"])
    rdir = cfg.paths.review / book["book_id"]
    rdir.mkdir(parents=True, exist_ok=True)
    count = book["chapter_count"]
    mid = book.get("midpoint_chapter") or count // 2
    picks = sorted({1, mid, *range(max(1, count - 2), count + 1)})
    for n in picks:
        src = bdir / "chapters" / f"ch-{n:02d}.md"
        if src.exists():
            shutil.copy(src, rdir / src.name)
    pkg = bdir / "package"
    for name in ("blurb.md", "cover-prompt.md", "cover.jpg", "metadata.json", "teaser.md"):
        if (pkg / name).exists():
            shutil.copy(pkg / name, rdir / name)

    chapters = {int(k): v for k, v in book["chapters"].items()}
    scored = [(v.get("average") or 0, n) for n, v in chapters.items() if v.get("average") is not None]
    weakest = sorted(scored)[:3]
    needs_owner = [(n, v) for n, v in sorted(chapters.items()) if "needs-owner" in v.get("flags", [])]
    other_flags = [(n, f) for n, v in sorted(chapters.items()) for f in v.get("flags", []) if f != "needs-owner"]
    meta = read_json(pkg / "metadata.json", {}) or {}

    lines = [
        f"# Review: {book.get('title') or book['book_id']}",
        "",
        f"Book `{book['book_id']}` · series `{book['series_id']}` · book {book['number']} · "
        f"{sum(v.get('words', 0) for v in chapters.values()):,} words in {count} chapters",
        "",
        "About 45 minutes. Read in this order, then approve or send back with notes:",
        "",
        f"- `factory approve book {book['book_id']}`",
        f"- `factory revise {book['book_id']} --notes notes.md`",
        "",
        "## 1. Read",
        "",
    ]
    for n in picks:
        label = "opening" if n == 1 else "midpoint" if n == mid else "ending"
        avg = chapters.get(n, {}).get("average")
        lines.append(f"- [ ] Chapter {n} ({label}, critic {avg}): `ch-{n:02d}.md`")
    lines += [
        "- [ ] Blurb: `blurb.md`",
        "- [ ] Cover: `cover-prompt.md` (and `cover.jpg` once typeset)",
        "",
        "## 2. Items needing you",
        "",
    ]
    if needs_owner:
        for n, v in needs_owner:
            crit = read_json(bdir / "critique" / f"ch-{n:02d}.json", {}) or {}
            lines.append(f"- **Chapter {n}** failed critique after {v['revisions']} revisions "
                         f"(avg {v.get('average')}, min {v.get('minimum')}). Fixes left: "
                         + " | ".join(crit.get("fixes", [])))
    else:
        lines.append("- None: every chapter passed the critic.")
    for n, f in other_flags:
        lines.append(f"- Chapter {n}: {f}")
    for f in book.get("flags", []):
        lines.append(f"- Book: {f}")
    lines += ["", "## 3. Critic's three weakest chapters", ""]
    for avg, n in weakest:
        crit = read_json(bdir / "critique" / f"ch-{n:02d}.json", {}) or {}
        low = sorted(crit.get("scores", {}).items(), key=lambda kv: kv[1])[:2]
        lines.append(f"- Chapter {n}: average {avg}; lowest {', '.join(f'{k} {v}' for k, v in low)}")
    lines += ["", "## 4. Book-level checks", ""]
    for c in (read_json(bdir / "book-check.json", {}) or {}).get("checks", []):
        mark = "pass" if c.get("pass") else "**FAIL**"
        lines.append(f"- {c.get('name')}: {mark}. {c.get('evidence', '')}")
    lines += [
        "",
        "## 5. Continuity",
        "",
        read_text(bdir / "continuity-report.md", "(no report)").strip(),
        "",
        "## 6. Package",
        "",
        f"- Title: {meta.get('title', '?')}",
        f"- Keywords: {', '.join(meta.get('keywords', []))}",
        f"- Categories: {'; '.join(meta.get('categories', []))}",
        f"- Package status: {book.get('package', {})}",
        f"- Package folder: `{pkg.relative_to(cfg.paths.root)}`",
        "",
        "## 7. Your notes",
        "",
        "Write revision notes in a separate file and pass it to `factory revise`.",
    ]
    text = "\n".join(lines) + "\n"
    atomic_write(rdir / "review.md", text)
    return text
