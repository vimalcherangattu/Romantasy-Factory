"""S10 packaging: EPUB, DOCX, metadata, blurb, disclosure, upload checklist (PRD section 7)."""

import json
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

from . import state
from .config import Config
from .fsutil import atomic_write, read_json, read_text

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"


def _pkg(cfg: Config, book: dict) -> Path:
    return cfg.paths.book_dir(book["series_id"], book["book_id"]) / "package"


def also_by(cfg: Config, book: dict, series_title: str) -> str:
    entries = (read_json(cfg.paths.series_dir(book["series_id"]) / "series.json", {}) or {}).get("books", [])
    lines = [f"## Also by {state.pen_name(cfg, book['series_id'])} {{.unnumbered}}", "", f"**{series_title}**", ""]
    for e in sorted(entries, key=lambda e: int(e["number"])):
        bid = f"{book['series_id']}-b{int(e['number']):02d}"
        try:
            title = state.load_book(cfg, bid).get("title") or e.get("working_title")
        except KeyError:
            title = e.get("working_title")
        marker = " (this book)" if bid == book["book_id"] else ""
        lines.append(f"{e['number']}. *{title}*{marker}")
    return "\n".join(lines)


def manuscript(cfg: Config, book: dict, meta: dict, teaser: str) -> str:
    bdir = cfg.paths.book_dir(book["series_id"], book["book_id"])
    year = cfg.get("copyright_year", date.today().year)
    series_line = f"{meta.get('series_name')}, Book {meta.get('series_number')}"
    parts = [
        f"# {meta['title']} {{.unnumbered .unlisted}}",
        f"*{meta['subtitle']}*" if meta.get("subtitle") else "",
        series_line,
        f"**{meta['pen_name']}**",
        "",
        "## Copyright {.unnumbered .unlisted}",
        f"Copyright © {year} {meta['pen_name']}. All rights reserved.",
        "This is a work of fiction. Names, characters, places and events are products of the "
        "author's imagination. Any resemblance to actual persons, living or dead, is coincidental.",
        "No part of this book may be reproduced without written permission, except for brief "
        "quotations in reviews.",
        f"{meta.get('age_notes', 'For adult readers. All characters are adults.')}",
    ]
    for n in range(1, book["chapter_count"] + 1):
        text = read_text(bdir / "chapters" / f"ch-{n:02d}.md").strip()
        text = re.sub(r"^\s*#\s*Chapter", "# Chapter", text, count=1)
        parts.append(text.replace("\n* * *\n", "\n\n::: {.scene-break}\n\\* \\* \\*\n:::\n\n"))
    parts.append(also_by(cfg, book, meta.get("series_name", "")))
    signup = cfg.get("reader.signup_url", "")
    if signup:
        bonus = read_json(cfg.paths.series_dir(book["series_id"]) / "magnet" / "bonus-meta.json", {}) or {}
        pitch = bonus.get("pitch") or "a free bonus story from this series"
        title = f"*{bonus['title']}*: " if bonus.get("title") else ""
        parts.append(f"## Free bonus story {{.unnumbered}}\n\nWant more? Get {title}{pitch}, free when you join "
                     f"{meta['pen_name']}'s reader list. You'll also hear first when the next book is out.\n\n"
                     f"[Get the bonus story]({signup})")
    if teaser.strip():
        parts.append("## Coming next {.unnumbered}\n\n" + re.sub(r"^#.*\n", "", teaser.strip()))
    return "\n\n".join(p for p in parts if p is not None) + "\n"


def _pandoc(src: Path, out: Path, meta_file: Path) -> str | None:
    if not shutil.which("pandoc"):
        return "pandoc not installed"
    args = ["pandoc", str(src), "-o", str(out), "--metadata-file", str(meta_file), "--toc", "--toc-depth=1"]
    if out.suffix == ".epub":
        args += ["--split-level=1", "--epub-title-page=false", "--css", str(TEMPLATES / "epub.css")]
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        return f"pandoc failed for {out.name}: {proc.stderr.strip()[:300]}"
    return None


def epubcheck_command(path: Path) -> list[str] | None:
    if shutil.which("epubcheck"):
        return ["epubcheck", str(path)]
    jar = next((p for p in (Path.home() / ".local/share/epubcheck").glob("**/epubcheck.jar")), None)
    if jar and shutil.which("java"):
        return ["java", "-jar", str(jar), str(path)]
    return None


def epubcheck(path: Path) -> tuple[bool | None, str]:
    """True/False when epubcheck ran; None when it isn't installed."""
    cmd = epubcheck_command(path)
    if not cmd:
        return None, "epubcheck not installed (brew install epubcheck)"
    proc = subprocess.run(cmd, capture_output=True, text=True)
    out = (proc.stdout + proc.stderr).strip()
    return proc.returncode == 0, out[-800:]


def docx_headings_ok(path: Path) -> bool | None:
    try:
        import docx  # python-docx, optional
    except ImportError:
        return None
    doc = docx.Document(str(path))
    return any(p.style.name == "Heading 1" and p.text.startswith("Chapter") for p in doc.paragraphs)


def upload_checklist(cfg: Config, book: dict, meta: dict) -> str:
    kw = meta.get("keywords", [])
    cats = meta.get("categories", [])
    rows = [
        f"# KDP upload checklist: {meta['title']}",
        "",
        f"Book ID `{book['book_id']}`. Fill KDP's pages in this order. Values come from `metadata.json`.",
        "Re-check KDP's current limits in KDP Help before the first upload of a series (PRD section 7).",
        "",
        "## 1. Kindle eBook Details",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Language | {meta.get('language')} |",
        f"| Book title | {meta['title']} |",
        f"| Subtitle | {meta.get('subtitle', '')} |",
        f"| Series | {meta.get('series_name')} (add to existing series after book 1) |",
        f"| Series number | {meta.get('series_number')} |",
        "| Edition number | (leave blank) |",
        f"| Author (primary) | {meta['pen_name']} |",
        "| Contributors | (none) |",
        "| Description | paste from `blurb.md` (HTML) |",
        "| Publishing rights | I own the copyright and I hold the necessary publishing rights |",
        "| Primary audience: sexually explicit images or title | No |",
        "| Reading age | (leave blank: adult) |",
        f"| Categories | {'; '.join(cats)} |",
    ]
    rows += [f"| Keyword {i} | {k} |" for i, k in enumerate(kw, start=1)]
    rows += [
        "| Release option | I'm ready to release my book now |",
        "",
        "Save and continue (Claude asks before saving).",
        "",
        "## 2. Kindle eBook Content",
        "",
        "| Field | Value |",
        "|---|---|",
        "| Digital rights management | Owner's choice (default: No) |",
        "| Manuscript | `package/book.epub` |",
        "| Cover | `package/cover.jpg` (upload a cover you already have) |",
        "| AI-generated content | Yes. Answer each question from `ai-disclosure.md` |",
        "| Kindle Previewer | Owner checks chapter 1, a scene break, the Also-by page |",
        "| ISBN | (none for ebook) |",
        "",
        "Save and continue (Claude asks before saving).",
        "",
        "## 3. Kindle eBook Pricing",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| KDP Select enrollment | {'Enroll' if meta.get('kdp_select') else 'Do not enroll'} |",
        "| Territories | All territories (worldwide rights) |",
        "| Primary marketplace | Amazon.com |",
        "| Royalty plan | 70% |",
        f"| List price (USD) | {meta.get('price_usd')} |",
        "| Other marketplaces | Based on USD price |",
        "| Book Lending | Enrolled |",
        "",
        "## 4. Stop before Publish",
        "",
        "Claude shows a summary and stops. The owner clicks **Publish Your Kindle eBook** or tells Claude to.",
        f"Then run: `factory published {book['book_id']} --asin <ASIN>`",
    ]
    return "\n".join(rows) + "\n"


def build(cfg: Config, book: dict, files: dict[str, str]) -> dict:
    pkg = _pkg(cfg, book)
    pkg.mkdir(parents=True, exist_ok=True)
    meta = json.loads(files["metadata.json"])
    for name in ("metadata.json", "blurb.md", "cover-prompt.md", "teaser.md", "launch-email.md"):
        if name in files:
            atomic_write(pkg / name, files[name])

    template = read_text(TEMPLATES / "ai-disclosure.md")
    atomic_write(pkg / "ai-disclosure.md", template.format(
        title=meta["title"], book_id=book["book_id"], pen_name=meta["pen_name"],
        date=date.today().isoformat(), cover_tool="the owner's image tool (fill in before upload)"))
    atomic_write(pkg / "upload-checklist.md", upload_checklist(cfg, book, meta))
    atomic_write(pkg / "browser-upload-prompt.md", browser_prompt(cfg, book, meta))

    src = pkg / "book.md"
    atomic_write(src, manuscript(cfg, book, meta, files.get("teaser.md", "")))
    meta_file = pkg / "pandoc-meta.yaml"
    atomic_write(meta_file, "\n".join([
        f"title: {json.dumps(meta['title'])}",
        f"author: {json.dumps(meta['pen_name'])}",
        f"lang: en",
        f"rights: {json.dumps('Copyright © ' + str(cfg.get('copyright_year')) + ' ' + meta['pen_name'])}",
        f"belongs-to-collection: {json.dumps(meta.get('series_name', ''))}",
        f"group-position: {meta.get('series_number', 1)}",
        f"description: {json.dumps(meta.get('description', ''))}",
    ]) + "\n")

    problems = []
    for out in (pkg / "book.epub", pkg / "book.docx"):
        err = _pandoc(src, out, meta_file)
        if err:
            problems.append(err)
    result = {"problems": problems, "epubcheck": None, "docx_headings": None}
    if (pkg / "book.epub").exists():
        ok, log = epubcheck(pkg / "book.epub")
        result["epubcheck"] = ok
        atomic_write(pkg / "epubcheck.log", log + "\n")
        if ok is False:
            problems.append("epubcheck failed (see package/epubcheck.log)")
        elif ok is None:
            problems.append(log)
    if (pkg / "book.docx").exists():
        result["docx_headings"] = docx_headings_ok(pkg / "book.docx")
        if result["docx_headings"] is False:
            problems.append("book.docx chapters are not Heading 1")
    if cfg.get("paperback.enabled", True):
        try:
            from . import paperback
            result["paperback"] = paperback.build(cfg, book)
        except Exception as exc:  # noqa: BLE001 - the ebook must not fail because of print
            problems.append(f"paperback build failed: {exc}")
    if not (pkg / "cover.jpg").exists():
        result["cover"] = "missing: generate art from cover-prompt.md, then run `factory cover`"
    return result


def browser_prompt(cfg: Config, book: dict, meta: dict) -> str:
    """The message the owner pastes into Claude in Chrome (or the desktop app) to run the upload."""
    pkg = cfg.paths.book_dir(book["series_id"], book["book_id"]) / "package"
    return f"""Upload the Kindle ebook "{meta['title']}" ({book['book_id']}) to KDP.

Files are in: {pkg}
Follow {pkg}/upload-checklist.md page by page, using metadata.json, blurb.md and ai-disclosure.md.

Rules:
- I am signed in to kdp.amazon.com in this browser. Never type passwords, 2FA codes, tax or bank details.
  If KDP asks for any of them, or shows a CAPTCHA, stop and hand over to me.
- Create a new Kindle eBook (Bookshelf > + Create > Kindle eBook). This is book {book['number']} of
  "{meta.get('series_name')}": {'create the series' if book['number'] == 1 else 'add it to the existing series'}.
- Fill Details, then Content (upload book.epub and cover.jpg; answer the AI-content questions from
  ai-disclosure.md exactly), then Pricing.
- Save as draft at the end of each page without asking. Show me what you filled in on each page as you go.
- Stop before "Publish Your Kindle eBook". Show me a summary of every field and wait for me to say "publish".
- When it is published and KDP shows the ASIN, tell me the ASIN so I can run:
  factory published {book['book_id']} --asin <ASIN>
"""


def bonus_epub(cfg: Config, series_id: str, meta: dict) -> str | None:
    """Builds magnet/bonus.epub for the newsletter sign-up. Returns a problem, or None."""
    mdir = cfg.paths.series_dir(series_id) / "magnet"
    series_json = read_json(cfg.paths.series_dir(series_id) / "series.json", {}) or {}
    author = state.pen_name(cfg, series_id)
    meta_file = mdir / "pandoc-meta.yaml"
    atomic_write(meta_file, "\n".join([
        f"title: {json.dumps(meta.get('title') or series_json.get('title', 'Bonus story'))}",
        f"author: {json.dumps(author)}",
        "lang: en",
        f"rights: {json.dumps('Copyright © ' + str(cfg.get('copyright_year')) + ' ' + author)}",
    ]) + "\n")
    err = _pandoc(mdir / "bonus.md", mdir / "bonus.epub", meta_file)
    if err:
        return err
    ok, log = epubcheck(mdir / "bonus.epub")
    return None if ok is not False else f"bonus.epub failed epubcheck: {log[-200:]}"


# ---------- cover typesetting ----------

def _font(path: str, size: int):
    from PIL import ImageFont

    candidates = [path] if path else []
    candidates += [
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/Library/Fonts/Georgia Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default(size=size)


def _wrap(draw, text: str, font, width: int) -> list[str]:
    words, lines, line = text.split(), [], ""
    for w in words:
        trial = f"{line} {w}".strip()
        if draw.textlength(trial, font=font) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def typeset_cover(cfg: Config, art: Path, out: Path, title: str, pen_name: str) -> Path:
    """Crop the art to KDP's ebook size and add title and pen name in the series display face."""
    from PIL import Image

    from .paperback import compose_front

    W, H = cfg.get("packaging.cover_width", 1600), cfg.get("packaging.cover_height", 2560)
    img = compose_front(Image.open(art), W, H, title, pen_name)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=92)
    return out
