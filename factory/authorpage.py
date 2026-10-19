"""Amazon Author Central kit per pen name: bio, author image (a monogram, never a fake face),
book list with ASINs, and the claim steps the owner's browser session follows."""

import json
import re
from pathlib import Path

from . import agentrun, state
from .config import Config
from .fsutil import atomic_write, read_json, write_json
from .parse import json_text
from .paperback import FONTS


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def folder(cfg: Config, pen_name: str) -> Path:
    return cfg.paths.root / "pen-names" / slug(pen_name)


def books_for(cfg: Config, pen_name: str) -> list[dict]:
    out = []
    for s in state.all_series(cfg):
        if s.get("status") != "approved" or state.pen_name(cfg, s["series_id"]) != pen_name:
            continue
        series_json = read_json(cfg.paths.series_dir(s["series_id"]) / "series.json", {}) or {}
        for bid in s.get("books", []):
            b = state.load_book(cfg, bid)
            out.append({"series": series_json.get("title", s.get("title")), "number": b["number"],
                        "title": b.get("title") or "", "status": b["status"], "asin": b.get("asin")})
    return out


def monogram(pen_name: str, tagline: str, out: Path, palette=((24, 16, 30), (226, 196, 140))) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    size = 1200
    bg, fg = palette
    img = Image.new("RGB", (size, size), bg)
    draw = ImageDraw.Draw(img)
    initials = "".join(w[0] for w in pen_name.split() if w[:1].isalpha())[:3].upper()
    big = ImageFont.truetype(str(FONTS / "Cinzel-Bold.ttf"), 420)
    small = ImageFont.truetype(str(FONTS / "Cinzel-Regular.ttf"), 64)
    tiny = ImageFont.truetype(str(FONTS / "EBGaramond-Italic.ttf"), 46)
    draw.ellipse((90, 90, size - 90, size - 90), outline=fg, width=6)
    w = draw.textlength(initials, font=big)
    draw.text(((size - w) / 2, 300), initials, font=big, fill=fg)
    w = draw.textlength(pen_name.upper(), font=small)
    draw.text(((size - w) / 2, 840), pen_name.upper(), font=small, fill=fg)
    if tagline:
        w = draw.textlength(tagline, font=tiny)
        if w < size - 240:
            draw.text(((size - w) / 2, 930), tagline, font=tiny, fill=fg)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG")
    return out


def build(cfg: Config, pen_name: str, lane: str = "") -> Path:
    books = books_for(cfg, pen_name)
    signup = cfg.get("reader.signup_url", "")

    def check(files):
        try:
            data = json_text(files["author-bio.json"], "author-bio.json")
        except Exception as exc:  # noqa: BLE001
            return [str(exc)]
        errs = [f"author-bio.json is missing '{k}'" for k in ("bio_long", "bio_short", "tagline") if not data.get(k)]
        if len(data.get("bio_short", "").split()) > 55:
            errs.append("bio_short is over 50 words")
        return errs

    files = agentrun.run(
        cfg, "author_bio",
        task=(f"Write the Author Central profile for the pen name \"{pen_name}\". Lane: {lane or 'romantasy'}. "
              f"Sign-up link: {'yes' if signup else 'not yet'}."),
        inputs={"books.json": json.dumps(books, indent=2, ensure_ascii=False), "taste.md": cfg.paths.taste},
        book_id=f"pen:{slug(pen_name)}", expect=["author-bio.json"], validator=check,
    )
    bio = json_text(files["author-bio.json"])
    out = folder(cfg, pen_name)
    write_json(out / "author-bio.json", bio)
    monogram(pen_name, bio.get("tagline", ""), out / "author-image.png")
    book_lines = "\n".join(
        f"| {b['series']} #{b['number']} | {b['title']} | {b['status']} | {b['asin'] or 'not live yet'} |" for b in books)
    atomic_write(out / "author-central.md", f"""# Author Central kit: {pen_name}

Set up at author.amazon.com in the owner's browser (Claude in Chrome or the desktop app). Claude
fills the forms; the owner signs in. One Author Central account can manage several pen names.

## Steps

1. Sign in to author.amazon.com with the KDP account.
2. Claim the first live book: search the title, choose the book, confirm "{pen_name}" as the author.
   The author page appears once Amazon approves the claim (usually a few days).
3. Biography: paste `bio_long` below.
4. Author photo: upload `author-image.png` (a monogram; no invented face).
5. For each new book, claim it under this author so it joins the page.
6. Later: add the website and newsletter link once they're live (docs/reader-platform.md).

## Biography (Author Central)

{bio['bio_long']}

## Short bio (back matter and website)

{bio['bio_short']}

## Tagline

{bio['tagline']}

## Books under this name

| Series | Title | Status | ASIN |
|---|---|---|---|
{book_lines or '| | none yet | | |'}
""")
    return out
