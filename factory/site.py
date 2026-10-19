"""Pen-name website: static pages built from series and book state (PRD section 12, M9).

`factory site` writes site/dist/, which Vercel serves as-is.
"""

import html
import re
import shutil
from pathlib import Path

from . import state
from .config import Config
from .fsutil import atomic_write, read_json, read_text

TEMPLATE = Path(__file__).resolve().parent.parent / "site" / "template.html"


def _md(text: str) -> str:
    """Tiny Markdown: paragraphs, *italic*, **bold**, [links](url). Enough for about.md."""
    out = []
    for para in re.split(r"\n\s*\n", text.strip()):
        if para.startswith("# "):
            continue
        p = html.escape(para.strip())
        p = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", p)
        p = re.sub(r"\*(.+?)\*", r"<i>\1</i>", p)
        p = re.sub(r"\[(.+?)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', p)
        out.append(f"<p>{p}</p>")
    return "\n".join(out)


def _page(cfg: Config, title: str, body: str) -> str:
    template = read_text(TEMPLATE)
    nav_bonus = '<a href="bonus.html">Free story</a>' if cfg.get("reader.signup_url") else ""
    return (template.replace("{{TITLE}}", html.escape(title))
            .replace("{{PEN_NAME}}", html.escape(cfg.get("pen_name", "")))
            .replace("{{NAV_BONUS}}", nav_bonus)
            .replace("{{SITE_URL}}", html.escape(cfg.get("reader.site_url", "")))
            .replace("{{BODY}}", body))


def build(cfg: Config) -> Path:
    dist = cfg.paths.root / "site" / "dist"
    if dist.exists():
        shutil.rmtree(dist)
    (dist / "covers").mkdir(parents=True)
    amazon = cfg.get("reader.amazon_domain", "www.amazon.com")
    sections = []
    for s in state.all_series(cfg):
        if s.get("status") != "approved":
            continue
        cards = []
        for bid in s.get("books", []):
            try:
                b = state.load_book(cfg, bid)
            except KeyError:
                continue
            pkg = cfg.paths.book_dir(s["series_id"], bid) / "package"
            meta = read_json(pkg / "metadata.json", {}) or {}
            title = meta.get("title") or b.get("title") or f"Book {b['number']}"
            cover = ""
            if (pkg / "cover.jpg").exists():
                shutil.copy(pkg / "cover.jpg", dist / "covers" / f"{bid}.jpg")
                cover = f'<img src="covers/{bid}.jpg" alt="Cover of {html.escape(title)}" loading="lazy">'
            if b.get("asin"):
                action = f'<a class="buy" href="https://{amazon}/dp/{b["asin"]}">Read it on Kindle</a>'
                blurb = read_text(pkg / "blurb.md")
            else:
                action = '<span class="soon">Coming soon</span>'
                blurb = ""
            cards.append(f'<article class="book">{cover}<div><h3>Book {b["number"]}: {html.escape(title)}</h3>'
                         f'<div class="blurb">{blurb}</div>{action}</div></article>')
        if any("Read it on Kindle" in c for c in cards):
            sections.append(f'<section><h2>{html.escape(s.get("title", s["series_id"]))}</h2>{"".join(cards)}</section>')
    signup = cfg.get("reader.signup_url", "")
    cta = (f'<p class="cta"><a class="buy" href="bonus.html">Get the free bonus story</a></p>' if signup else "")
    index = "".join(sections) or "<p>The first book is on its way. Join the list to hear the day it's out.</p>"
    atomic_write(dist / "index.html", _page(cfg, cfg.get("pen_name", ""), cta + index))

    about = read_text(cfg.paths.root / "site" / "about.md")
    atomic_write(dist / "about.html", _page(cfg, f"About {cfg.get('pen_name')}", _md(about)))

    if signup:
        bonus = {}
        for s in state.all_series(cfg):
            bonus = read_json(cfg.paths.series_dir(s["series_id"]) / "magnet" / "bonus-meta.json", {}) or bonus
        pitch = html.escape(bonus.get("pitch", "A free bonus story, only for readers on the list."))
        title = html.escape(bonus.get("title", "Your free bonus story"))
        body = (f"<h2>{title}</h2><p>{pitch}</p><p>Join the reader list and it lands in your inbox. "
                f"You'll also hear first when a new book is out. Unsubscribe any time.</p>"
                f'<p class="cta"><a class="buy" href="{html.escape(signup)}">Send me the story</a></p>')
        atomic_write(dist / "bonus.html", _page(cfg, "Free bonus story", body))
    return dist
