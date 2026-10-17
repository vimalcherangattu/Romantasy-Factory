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
    lines = [f"## Also by {cfg.get('pen_name')} {{.unnumbered}}", "", f"**{series_title}**", ""]
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
        parts.append(text.replace("\n* * *\n", "\n\n<center>\\* \\* \\*</center>\n\n"))
    parts.append(also_by(cfg, book, meta.get("series_name", "")))
    if teaser.strip():
        parts.append("## Coming next {.unnumbered}\n\n" + re.sub(r"^#.*\n", "", teaser.strip()))
    return "\n\n".join(p for p in parts if p is not None) + "\n"


def _pandoc(src: Path, out: Path, meta_file: Path) -> str | None:
    if not shutil.which("pandoc"):
        return "pandoc not installed"
    args = ["pandoc", str(src), "-o", str(out), "--metadata-file", str(meta_file), "--toc", "--toc-depth=1"]
    if out.suffix == ".epub":
        args += ["--split-level=1", "--epub-title-page=false"]
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
    for name in ("metadata.json", "blurb.md", "cover-prompt.md", "teaser.md"):
        atomic_write(pkg / name, files[name])

    template = read_text(TEMPLATES / "ai-disclosure.md")
    atomic_write(pkg / "ai-disclosure.md", template.format(
        title=meta["title"], book_id=book["book_id"], pen_name=meta["pen_name"],
        date=date.today().isoformat(), cover_tool="the owner's image tool (fill in before upload)"))
    atomic_write(pkg / "upload-checklist.md", upload_checklist(cfg, book, meta))

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
    if not (pkg / "cover.jpg").exists():
        result["cover"] = "missing: generate art from cover-prompt.md, then run `factory cover`"
    return result


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
    """Crop the art to KDP portrait size and add title and pen name with a fixed font set."""
    from PIL import Image, ImageDraw

    W, H = cfg.get("packaging.cover_width", 1600), cfg.get("packaging.cover_height", 2560)
    img = Image.open(art).convert("RGB")
    scale = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left, top = (img.width - W) // 2, (img.height - H) // 2
    img = img.crop((left, top, left + W, top + H))

    shade = Image.new("L", (1, H))
    for y in range(H):
        edge = min(y / (H * 0.3), (H - y) / (H * 0.18), 1.0)
        shade.putpixel((0, y), int(170 * (1 - edge)))
    overlay = Image.new("RGB", (W, H), (0, 0, 0))
    img = Image.composite(overlay, img, shade.resize((W, H)))

    draw = ImageDraw.Draw(img)
    title_font = _font(cfg.get("packaging.title_font", ""), int(H * 0.085))
    author_font = _font(cfg.get("packaging.author_font", ""), int(H * 0.045))
    y = int(H * 0.06)
    for line in _wrap(draw, title.upper(), title_font, int(W * 0.88)):
        w = draw.textlength(line, font=title_font)
        draw.text(((W - w) / 2, y), line, font=title_font, fill=(245, 236, 220), stroke_width=3, stroke_fill=(20, 12, 10))
        y += int(H * 0.095)
    author = pen_name.upper()
    w = draw.textlength(author, font=author_font)
    draw.text(((W - w) / 2, H - int(H * 0.09)), author, font=author_font, fill=(245, 236, 220),
              stroke_width=2, stroke_fill=(20, 12, 10))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=92)
    return out
