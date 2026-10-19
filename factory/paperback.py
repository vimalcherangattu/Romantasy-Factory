"""Paperback: print-ready interior PDF and full wraparound cover for KDP Print.

Defaults (config `paperback.*`): 5.5 x 8.5 in trim, cream paper, no interior bleed. KDP's
inside-margin table sets the gutter from the page count, and the spine width follows from the
page count and paper. Checked against KDP Help's published formulas; re-check them in KDP's
cover calculator before the first paperback upload.
"""

import html
import json
import re
import subprocess
from pathlib import Path

from . import state
from .config import Config
from .fsutil import atomic_write, read_json, read_text

FONTS = Path(__file__).resolve().parent.parent / "fonts"
DPI = 300
BLEED = 0.125
# KDP inside (gutter) margin by page count.
GUTTERS = ((150, 0.375), (300, 0.5), (500, 0.625), (700, 0.75), (828, 0.875))
SPINE_PER_PAGE = {"cream": 0.0025, "white": 0.002252}


def gutter_for(pages: int) -> float:
    for limit, inches in GUTTERS:
        if pages <= limit:
            return inches
    raise ValueError(f"{pages} pages is over KDP's paperback limit of 828")


def spine_width(pages: int, paper: str = "cream") -> float:
    return round(pages * SPINE_PER_PAGE[paper], 4)


def _dir(cfg: Config, book: dict) -> Path:
    return cfg.paths.book_dir(book["series_id"], book["book_id"]) / "package" / "paperback"


def _body_html(markdown: str) -> str:
    proc = subprocess.run(["pandoc", "-f", "markdown", "-t", "html5"], input=markdown,
                          capture_output=True, text=True, check=True)
    return proc.stdout


def interior_html(cfg: Config, book: dict, meta: dict, gutter: float) -> str:
    bdir = cfg.paths.book_dir(book["series_id"], book["book_id"])
    trim_w, trim_h = cfg.get("paperback.trim", [5.5, 8.5])
    pen = meta.get("pen_name") or state.pen_name(cfg, book["series_id"])
    title = meta.get("title") or book.get("title", "")
    year = cfg.get("copyright_year")
    chapters = []
    for n in range(1, book["chapter_count"] + 1):
        text = read_text(bdir / "chapters" / f"ch-{n:02d}.md").strip()
        first, _, rest = text.partition("\n")
        heading = re.sub(r"^#\s*", "", first).strip()
        number, _, name = heading.partition(":")
        body = _body_html(rest.replace("\n* * *\n", "\n\n<p class=\"scene\">*</p>\n\n"))
        chapters.append(f'<section class="chapter"><h1><span class="num">{html.escape(number.strip())}</span>'
                        f'<span class="name">{html.escape(name.strip())}</span></h1>{body}</section>')
    teaser = read_text(bdir / "package" / "teaser.md")
    also = read_text(bdir / "package" / "book.md")
    also_block = re.search(r"## Also by.*?(?=\n## |\Z)", also, re.DOTALL)
    back = ""
    if also_block:
        back += f'<section class="back">{_body_html(also_block.group(0).replace("{.unnumbered}", ""))}</section>'
    if teaser.strip():
        back += f'<section class="back"><h2>Coming next</h2>{_body_html(re.sub(r"^#.*\n", "", teaser.strip()))}</section>'
    font = lambda name: (FONTS / name).as_uri()  # noqa: E731
    css = f"""
@font-face {{ font-family: "Book"; src: url({font("EBGaramond-Regular.ttf")}); }}
@font-face {{ font-family: "Book"; font-style: italic; src: url({font("EBGaramond-Italic.ttf")}); }}
@font-face {{ font-family: "Book"; font-weight: bold; src: url({font("EBGaramond-Bold.ttf")}); }}
@font-face {{ font-family: "Book"; font-weight: bold; font-style: italic; src: url({font("EBGaramond-BoldItalic.ttf")}); }}
@font-face {{ font-family: "Display"; src: url({font("Cinzel-Regular.ttf")}); }}
@page {{ size: {trim_w}in {trim_h}in; margin: 0.7in 0.5in 0.7in {gutter}in;
  @bottom-center {{ content: counter(page); font: 9pt "Book"; }} }}
@page :left {{ margin-left: 0.5in; margin-right: {gutter}in;
  @top-center {{ content: "{html.escape(pen.upper())}"; font: 8pt "Display"; letter-spacing: 0.15em; }} }}
@page :right {{ margin-left: {gutter}in; margin-right: 0.5in;
  @top-center {{ content: "{html.escape(title.upper())}"; font: 8pt "Display"; letter-spacing: 0.15em; }} }}
@page front {{ @top-center {{ content: none; }} @bottom-center {{ content: none; }} }}
@page chapter:first {{ @top-center {{ content: none; }} }}
@page :blank {{ @top-center {{ content: none; }} @bottom-center {{ content: none; }} }}
html {{ font-family: "Book"; font-size: 11pt; line-height: 1.38; hyphens: auto; }}
.front {{ page: front; break-after: page; text-align: center; }}
.title-page h1 {{ font: 24pt "Display"; margin-top: 2in; }}
.title-page .series {{ font-style: italic; margin-top: 0.3in; }}
.title-page .pen {{ font: 13pt "Display"; margin-top: 1.2in; letter-spacing: 0.1em; }}
.copyright {{ font-size: 8.5pt; text-align: left; padding-top: 4in; }}
.copyright p {{ text-indent: 0; margin: 0 0 0.6em; }}
.chapter {{ page: chapter; break-before: right; }}
.chapter h1 {{ text-align: center; margin: 1.3in 0 0.45in; font-weight: normal; }}
.chapter h1 .num {{ display: block; font: 10pt "Display"; letter-spacing: 0.2em; }}
.chapter h1 .name {{ display: block; font: 17pt "Display"; margin-top: 0.15in; }}
p {{ margin: 0; text-indent: 1.2em; text-align: justify; orphans: 2; widows: 2; }}
h1 + p, .scene + p {{ text-indent: 0; }}
h1 + p::first-line {{ font-variant: small-caps; letter-spacing: 0.04em; }}
p.scene {{ text-align: center; text-indent: 0; margin: 0.6em 0; }}
.back {{ break-before: right; }}
.back h2 {{ font: 14pt "Display"; text-align: center; margin: 1in 0 0.4in; }}
.back ol {{ padding-left: 1.2em; }}
"""
    front = (f'<section class="front title-page"><h1>{html.escape(title)}</h1>'
             f'<p class="series">{html.escape(meta.get("series_name", ""))}, Book {meta.get("series_number", book["number"])}</p>'
             f'<p class="pen">{html.escape(pen)}</p></section>'
             f'<section class="front copyright"><p>Copyright © {year} {html.escape(pen)}. All rights reserved.</p>'
             '<p>This is a work of fiction. Names, characters, places and events are products of the '
             "author's imagination. Any resemblance to actual persons, living or dead, is coincidental.</p>"
             '<p>No part of this book may be reproduced without written permission, except for brief '
             'quotations in reviews.</p>'
             f'<p>{html.escape(meta.get("age_notes", "For adult readers. All characters are adults."))}</p></section>')
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><style>{css}</style></head>'
            f'<body>{front}{"".join(chapters)}{back}</body></html>')


def build_interior(cfg: Config, book: dict, meta: dict) -> dict:
    """Two passes: lay out with a provisional gutter, then with KDP's gutter for the real page count."""
    from weasyprint import HTML

    out_dir = _dir(cfg, book)
    out_dir.mkdir(parents=True, exist_ok=True)
    gutter = 0.625
    for _ in range(3):
        doc = HTML(string=interior_html(cfg, book, meta, gutter)).render()
        pages = len(doc.pages)
        needed = gutter_for(pages)
        if needed == gutter:
            break
        gutter = needed
    pdf = out_dir / "interior.pdf"
    doc.write_pdf(pdf)
    return {"pages": pages, "gutter_in": gutter, "interior": str(pdf.name)}


# ---------- cover wrap ----------

def _font(name: str, size: int):
    from PIL import ImageFont

    return ImageFont.truetype(str(FONTS / name), size)


def _wrap_text(draw, text: str, font, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def compose_front(art, width: int, height: int, title: str, pen: str):
    """The ebook-cover look at any size: art cropped to fill, shaded top and bottom, title and pen name."""
    from PIL import Image, ImageDraw

    img = art.convert("RGB")
    scale = max(width / img.width, height / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left, top = (img.width - width) // 2, (img.height - height) // 2
    img = img.crop((left, top, left + width, top + height))
    shade = Image.new("L", (1, height))
    for y in range(height):
        edge = min(y / (height * 0.3), (height - y) / (height * 0.18), 1.0)
        shade.putpixel((0, y), int(170 * (1 - edge)))
    img = Image.composite(Image.new("RGB", (width, height)), img, shade.resize((width, height)))
    draw = ImageDraw.Draw(img)
    title_font = _font("Cinzel-Bold.ttf", int(height * 0.075))
    author_font = _font("Cinzel-Regular.ttf", int(height * 0.042))
    y = int(height * 0.06)
    for line in _wrap_text(draw, title.upper(), title_font, int(width * 0.86)):
        w = draw.textlength(line, font=title_font)
        draw.text(((width - w) / 2, y), line, font=title_font, fill=(245, 236, 220),
                  stroke_width=max(2, height // 900), stroke_fill=(20, 12, 10))
        y += int(height * 0.085)
    w = draw.textlength(pen.upper(), font=author_font)
    draw.text(((width - w) / 2, height - int(height * 0.09)), pen.upper(), font=author_font,
              fill=(245, 236, 220), stroke_width=max(2, height // 1200), stroke_fill=(20, 12, 10))
    return img


def build_wrap(cfg: Config, book: dict, meta: dict, art_path: Path, pages: int) -> dict:
    from PIL import Image, ImageDraw

    trim_w, trim_h = cfg.get("paperback.trim", [5.5, 8.5])
    paper = cfg.get("paperback.paper", "cream")
    spine = spine_width(pages, paper)
    px = lambda inches: round(inches * DPI)  # noqa: E731
    W, H = px(BLEED * 2 + trim_w * 2 + spine), px(trim_h + BLEED * 2)
    back_w, spine_w = px(BLEED + trim_w), px(spine)
    front_x = back_w + spine_w
    title = meta.get("title") or book.get("title", "")
    pen = meta.get("pen_name") or state.pen_name(cfg, book["series_id"])
    art = Image.open(art_path)

    wrap = Image.new("RGB", (W, H))
    wrap.paste(compose_front(art, W - front_x, H, title, pen), (front_x, 0))

    # Back: the art mirrored, blurred and darkened, so the wrap reads as one image.
    back = compose_back_art(art, back_w + spine_w, H)
    wrap.paste(back, (0, 0))

    draw = ImageDraw.Draw(wrap)
    # Spine: darkened band, title and pen name running top to bottom (KDP allows text over 79 pages).
    spine_color = tuple(int(c * 0.35) for c in art.convert("RGB").resize((1, 1)).getpixel((0, 0)))
    draw.rectangle((back_w, 0, front_x, H), fill=spine_color)
    spine_text = None
    if pages > 79:
        size = max(10, min(int(spine_w * 0.5), px(0.22)))
        f = _font("Cinzel-Bold.ttf", size)
        label = f"{title.upper()}     {pen.upper()}"
        tw = int(draw.textlength(label, font=f))
        strip = Image.new("RGBA", (tw + 20, size + 20), (0, 0, 0, 0))
        ImageDraw.Draw(strip).text((10, 5), label, font=f, fill=(245, 236, 220))
        strip = strip.rotate(-90, expand=True)
        wrap.paste(strip, (back_w + (spine_w - strip.width) // 2, (H - strip.height) // 2), strip)
        spine_text = label

    # Back text: hook line, blurb, series line. Kept clear of KDP's barcode area (2 x 1.2 in, bottom right).
    margin = px(BLEED + 0.5)
    text_w = back_w - margin - px(0.5)
    y = px(BLEED + 0.7)
    hook_font = _font("Cinzel-Bold.ttf", px(0.17))
    body_font = _font("EBGaramond-Regular.ttf", px(0.135))
    hook = meta.get("subtitle") or ""
    blurb = read_text(cfg.paths.book_dir(book["series_id"], book["book_id"]) / "package" / "blurb.md")
    blurb = re.sub(r"(?i)</p>|<br\s*/?>", "\n", blurb)
    blurb = re.sub(r"<[^>]+>", "", blurb)
    paragraphs = [html.unescape(" ".join(p.split())) for p in blurb.split("\n") if p.strip()]
    barcode_top = H - px(BLEED + 0.25 + 1.2 + 0.2)
    if hook:
        for line in _wrap_text(draw, hook.upper(), hook_font, text_w):
            draw.text((margin, y), line, font=hook_font, fill=(245, 236, 220))
            y += int(px(0.17) * 1.35)
        y += px(0.15)
    for para in paragraphs:
        for line in _wrap_text(draw, para, body_font, text_w):
            if y > barcode_top - px(0.4):
                break
            draw.text((margin, y), line, font=body_font, fill=(240, 232, 220))
            y += int(px(0.135) * 1.45)
        y += px(0.08)
    series_line = f"{meta.get('series_name', '')} · Book {meta.get('series_number', book['number'])}".upper()
    draw.text((margin, H - px(BLEED + 0.6)), series_line, font=_font("Cinzel-Regular.ttf", px(0.11)),
              fill=(220, 210, 195))

    out_dir = _dir(cfg, book)
    out_dir.mkdir(parents=True, exist_ok=True)
    wrap.save(out_dir / "cover-wrap.pdf", "PDF", resolution=DPI)
    preview = wrap.copy()
    preview.thumbnail((2000, 2000))
    preview.save(out_dir / "cover-wrap-preview.jpg", "JPEG", quality=88)
    return {"spine_in": spine, "wrap_in": [round(W / DPI, 4), round(H / DPI, 4)], "wrap_px": [W, H],
            "spine_text": spine_text, "paper": paper}


def compose_back_art(art, width: int, height: int):
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps

    img = ImageOps.mirror(art.convert("RGB"))
    scale = max(width / img.width, height / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left, top = (img.width - width) // 2, (img.height - height) // 2
    img = img.crop((left, top, left + width, top + height)).filter(ImageFilter.GaussianBlur(radius=width // 60))
    return ImageEnhance.Brightness(img).enhance(0.35)


def checklist(cfg: Config, book: dict, meta: dict, info: dict) -> str:
    trim_w, trim_h = cfg.get("paperback.trim", [5.5, 8.5])
    return f"""# KDP paperback checklist: {meta.get('title')}

Create it from the Kindle eBook's Bookshelf entry ("+ Create paperback"), so KDP links the two
editions and copies the details. Claude fills this in the browser like the ebook; you say "publish".

| Field | Value |
|---|---|
| Details | Same as the ebook (title, series, pen name, description, keywords, categories) |
| ISBN | Get a free KDP ISBN |
| Print options: ink and paper | Black & white interior with {info.get('paper', 'cream')} paper |
| Trim size | {trim_w} x {trim_h} in |
| Bleed settings | No bleed |
| Paperback cover finish | Matte |
| Manuscript | `paperback/interior.pdf` ({info.get('pages')} pages, gutter {info.get('gutter_in')} in) |
| Cover | Upload a cover you already have: `paperback/cover-wrap.pdf` |
| Cover size | {info.get('wrap_in', ['?', '?'])[0]} x {info.get('wrap_in', ['?', '?'])[1]} in, spine {info.get('spine_in')} in |
| AI-generated content | Same answers as the ebook (`ai-disclosure.md`) |
| Previewer | Check the spine text sits inside the spine and the barcode area is clear |
| Territories | All |
| Price (USD) | {cfg.get('paperback.price_usd', 15.99)}. KDP shows the printing cost on the Pricing page; keep the royalty above about $3 |
| Expanded distribution | Off at first |

Stop before "Publish Your Paperback Book". Spine and cover sizes follow KDP's formulas; if the
Previewer disagrees, use KDP's cover calculator numbers and run `factory paperback {book['book_id']}`.
"""


def build(cfg: Config, book: dict, art_path: Path | None = None) -> dict:
    """Interior, then the wrap if cover art exists. Records results in paperback/paperback.json."""
    pkg = cfg.paths.book_dir(book["series_id"], book["book_id"]) / "package"
    meta = read_json(pkg / "metadata.json", {}) or {}
    info = build_interior(cfg, book, meta)
    art_path = art_path or next(iter(sorted(pkg.glob("cover-art.*"))), None)
    if art_path:
        info.update(build_wrap(cfg, book, meta, Path(art_path), info["pages"]))
    out_dir = _dir(cfg, book)
    atomic_write(out_dir / "paperback.json", json.dumps(info, indent=2) + "\n")
    atomic_write(out_dir / "paperback-checklist.md", checklist(cfg, book, meta, info))
    return info
