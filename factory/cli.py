"""`factory` command line: the owner's interface (PRD sections 3 and 4)."""

import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

import typer

from . import config as configmod
from . import gitops, guard, orchestrator, package, report, schedule, series, state
from .fsutil import read_json

app = typer.Typer(add_completion=False, no_args_is_help=True, help="Romantasy Factory")
approve_app = typer.Typer(help="Approve a series bible or a reviewed book.")
app.add_typer(approve_app, name="approve")


@app.callback()
def _startup() -> None:
    """Every command refuses to start if ANTHROPIC_API_KEY is set (PRD section 2)."""
    guard.enforce()


def _cfg() -> configmod.Config:
    return configmod.load()


def _die(message: str) -> None:
    typer.secho(f"error: {message}", fg=typer.colors.RED, err=True)
    raise typer.Exit(1)


@app.command()
def status() -> None:
    """Every series and book: stage, scores, usage and flags."""
    typer.echo(report.status_table(_cfg()))


@app.command()
def doctor() -> None:
    """Check the tools the pipeline needs."""
    cfg = _cfg()
    checks = {
        "claude CLI": shutil.which(cfg.claude_binary) is not None,
        "pandoc": shutil.which("pandoc") is not None,
        "epubcheck": package.epubcheck_command(Path("book.epub")) is not None,
        "git repo": gitops.is_repo(cfg),
        "ANTHROPIC_API_KEY unset": True,  # the callback already exited if it was set
    }
    for name, ok in checks.items():
        typer.echo(f"{'ok ' if ok else 'MISSING'}  {name}")
    if shutil.which(cfg.claude_binary):
        out = subprocess.run([cfg.claude_binary, "--version"], capture_output=True, text=True, env=guard.child_env())
        typer.echo(f"     claude {out.stdout.strip()}")
    typer.echo("Sign in with your Max account only: `claude login`. Keep extra usage off in Claude settings.")


def _report_autopilot(cfg, result: dict) -> None:
    gitops.commit(cfg, f"{result['series_id']}: autopilot pick {result['pick']}")
    typer.echo(f"Picked concept {result['pick']} from {result['batch']}: {result['why']}")
    typer.echo(f"Bible: series/{result['series_id']}/bible.md")
    if result["books"]:
        typer.echo(f"Approved. Queued {len(result['books'])} books: {', '.join(result['books'])}")
    else:
        typer.echo(f"Review the bible, then: factory approve series {result['series_id']}")


@app.command("new-series")
def new_series(auto: bool = typer.Option(None, "--auto/--manual",
                                         help="Let agents pick the concept and approve the bible (default: config auto.pick_concept)")) -> None:
    """S1: propose series concepts from the canon and taste.md (and, with --auto, pick and approve one)."""
    cfg = _cfg()
    auto = cfg.get("auto.pick_concept", False) if auto is None else auto
    if auto:
        _report_autopilot(cfg, series.autopilot(cfg, generate=True))
        return
    folder = series.new_series(cfg)
    gitops.commit(cfg, f"proposals {folder.name}")
    typer.echo(f"Concepts written to {folder.relative_to(cfg.paths.root)}/")
    typer.echo("Read them, edit any concept-N.md you like, then: factory pick <N> (or factory pick --auto)")


@app.command()
def pick(concept: int = typer.Argument(None, help="Concept number from the latest proposals"),
         batch: str = typer.Option(None, help="Proposal batch folder (default: latest)"),
         auto: bool = typer.Option(False, "--auto", help="Let the selector agent pick, then approve per config"),
         pen_name: str = typer.Option(None, help="Pen name for this series (default: config pen_name)"),
         title: str = typer.Option(None, help="Book 1 title, e.g. a cleared replacement from the market check")) -> None:
    """S2: draft the series bible for the chosen concept."""
    cfg = _cfg()
    if auto or concept is None:
        _report_autopilot(cfg, series.autopilot(cfg, generate=False, batch=batch))
        return
    series_id = series.pick(cfg, concept, batch, title=title, pen_name=pen_name)
    gitops.commit(cfg, f"{series_id}: bible draft")
    typer.echo(f"Bible draft: series/{series_id}/bible.md")
    typer.echo(f"Edit it (including its Cover style section), then: factory approve series {series_id}")


@approve_app.command("series")
def approve_series(series_id: str) -> None:
    """Approve the edited bible and queue the series' books."""
    cfg = _cfg()
    try:
        books = series.approve(cfg, series_id)
    except (ValueError, KeyError) as exc:
        _die(str(exc))
    gitops.commit(cfg, f"{series_id}: approved")
    typer.echo(f"Approved. Queued {len(books)} books: {', '.join(books)}")


@approve_app.command("book")
def approve_book(book_id: str) -> None:
    """Approve a reviewed book for upload (max one per day)."""
    cfg = _cfg()
    try:
        b = state.load_book(cfg, book_id)
    except KeyError as exc:
        _die(str(exc))
    if b["status"] != "review":
        _die(f"{book_id} is '{b['status']}', not waiting for review")
    today = date.today().isoformat()
    approved_today = sum(1 for x in state.all_books(cfg) if (x.get("approved_at") or "").startswith(today))
    limit = cfg.get("schedule.max_uploads_per_day", 1)
    if approved_today >= limit:
        _die(f"{approved_today} book(s) already approved for upload today; the limit is {limit}. Approve tomorrow.")
    pkg = cfg.paths.book_dir(b["series_id"], book_id) / "package"
    if not (pkg / "cover.jpg").exists():
        typer.secho("warning: package/cover.jpg is missing; run `factory cover` before uploading", fg=typer.colors.YELLOW)
    b["status"] = "approved"
    b["approved_at"] = state.now()
    state.log(b, "approved by owner")
    state.save_book(cfg, b)
    gitops.commit(cfg, f"{book_id}: approved")
    typer.echo(f"Approved. Upload from {pkg.relative_to(cfg.paths.root)}/upload-checklist.md (PRD section 8).")


@app.command()
def revise(book_id: str, notes: Path = typer.Option(..., exists=True, readable=True, help="Your revision notes")) -> None:
    """Send a reviewed book back with notes for a revision pass."""
    cfg = _cfg()
    b = state.load_book(cfg, book_id)
    if b["status"] not in ("review", "approved", "blocked"):
        _die(f"{book_id} is '{b['status']}'; revise books that are in review, approved or blocked")
    b["revision_round"] = b.get("revision_round", 0) + 1
    dest = cfg.paths.book_dir(b["series_id"], book_id) / f"owner-notes-{b['revision_round']}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(notes, dest)
    b["pending_owner_notes"] = str(dest)
    b["status"] = "revising"
    b["review_at"] = None
    b["approved_at"] = None
    state.log(b, f"owner revision round {b['revision_round']}")
    state.save_book(cfg, b)
    gitops.commit(cfg, f"{book_id}: owner notes round {b['revision_round']}")
    typer.echo(f"Queued revision round {b['revision_round']}. The next run plans and applies it.")


@app.command()
def unblock(book_id: str) -> None:
    """Resume a blocked book from where it stopped, after you've fixed the cause."""
    cfg = _cfg()
    b = state.load_book(cfg, book_id)
    if b["status"] != "blocked":
        _die(f"{book_id} is not blocked")
    b["status"] = "in_progress" if "S3" in b["done"] else "queued"
    b["continuity_attempts"] = 0
    state.log(b, "unblocked by owner")
    state.save_book(cfg, b)
    typer.echo(f"{book_id} will resume on the next run.")


@app.command()
def published(book_id: str, asin: str = typer.Option(..., help="ASIN shown by KDP")) -> None:
    """Mark an uploaded book as live."""
    cfg = _cfg()
    b = state.load_book(cfg, book_id)
    if b["status"] != "approved":
        _die(f"{book_id} is '{b['status']}'; approve it before marking it published")
    b.update(status="published", asin=asin, published_at=state.now())
    state.log(b, f"published as {asin}")
    state.save_book(cfg, b)
    pkg = cfg.paths.book_dir(b["series_id"], book_id) / "package"
    email = pkg / "launch-email.md"
    if email.exists():
        link = f"https://{cfg.get('reader.amazon_domain', 'www.amazon.com')}/dp/{asin}"
        ready = cfg.paths.review / book_id / "launch-email-ready.md"
        ready.parent.mkdir(parents=True, exist_ok=True)
        ready.write_text(email.read_text().replace("{{AMAZON_LINK}}", link))
        typer.echo(f"Launch email ready to send: {ready.relative_to(cfg.paths.root)}")
    gitops.commit(cfg, f"{book_id}: published {asin}")
    typer.echo(f"{book_id} is live as {asin}. Rebuild the website with: factory site")


@app.command()
def upload(book_id: str) -> None:
    """Print the message that has Claude in Chrome upload an approved book to KDP (you confirm Publish)."""
    cfg = _cfg()
    b = state.load_book(cfg, book_id)
    if b["status"] != "approved":
        _die(f"{book_id} is '{b['status']}'; approve it first with: factory approve book {book_id}")
    pkg = cfg.paths.book_dir(b["series_id"], book_id) / "package"
    if not (pkg / "cover.jpg").exists():
        _die(f"{pkg.relative_to(cfg.paths.root)}/cover.jpg is missing; run: factory cover {book_id} --art <image>")
    typer.echo("Sign in to kdp.amazon.com in Chrome, open Claude in Chrome, and paste:\n")
    typer.echo((pkg / "browser-upload-prompt.md").read_text())


@app.command("site")
def site_cmd() -> None:
    """Build the pen-name website into site/dist (deploy with: vercel deploy site/dist --prod)."""
    from . import site

    cfg = _cfg()
    dist = site.build(cfg)
    typer.echo(f"Built {dist.relative_to(cfg.paths.root)}/. Deploy: vercel deploy site/dist --prod")


@app.command()
def run(book: str = typer.Option(None, help="Only work on this book"),
        steps: int = typer.Option(None, help="Stop after this many steps (hand runs, M3)"),
        scheduled: bool = typer.Option(False, help="Nightly mode: stop at schedule.stop_by"),
        max_minutes: float = typer.Option(None, help="Stop starting new steps after this many minutes")) -> None:
    """Continue the next unfinished book from its last completed stage."""
    cfg = _cfg()
    try:
        rep = orchestrator.run(cfg, book_id=book, max_steps=steps, scheduled=scheduled,
                               max_minutes=max_minutes, echo=typer.echo)
    except orchestrator.LockedError as exc:
        _die(str(exc))
    typer.echo(f"Stopped: {rep.stop_reason}. {len(rep.steps)} step(s) done.")


@app.command()
def cover(book_id: str, art: Path = typer.Option(..., exists=True, help="Cover art you generated"),
          tool: str = typer.Option("ElevenLabs image generation", help="Image tool that made the art (for the AI disclosure)")) -> None:
    """Typeset title and pen name onto the cover art -> package/cover.jpg, and record the tool in ai-disclosure.md."""
    cfg = _cfg()
    b = state.load_book(cfg, book_id)
    pkg = cfg.paths.book_dir(b["series_id"], book_id) / "package"
    meta = read_json(pkg / "metadata.json", {}) or {}
    out = package.typeset_cover(cfg, art, pkg / "cover.jpg", meta.get("title") or b.get("title", ""),
                                meta.get("pen_name") or state.pen_name(cfg, b["series_id"]))
    art_copy = pkg / f"cover-art{art.suffix.lower() or '.png'}"
    if art.resolve() != art_copy.resolve():
        shutil.copy(art, art_copy)  # full-resolution original, reused for the paperback wrap
    if cfg.get("paperback.enabled", True) and (pkg / "metadata.json").exists():
        from . import paperback
        try:
            info = paperback.build(cfg, b, art_copy)
            typer.echo(f"Paperback: {info['pages']} pages, spine {info.get('spine_in')} in, wrap {info.get('wrap_in')} in")
        except Exception as exc:  # noqa: BLE001
            typer.secho(f"warning: paperback build failed: {exc}", fg=typer.colors.YELLOW)
    disclosure = pkg / "ai-disclosure.md"
    if disclosure.exists():
        disclosure.write_text(disclosure.read_text().replace("the owner's image tool (fill in before upload)", tool))
    review_copy = cfg.paths.review / book_id
    if review_copy.exists():
        shutil.copy(out, review_copy / "cover.jpg")
    gitops.commit(cfg, f"{book_id}: cover")
    typer.echo(f"Cover: {out.relative_to(cfg.paths.root)} (check the title is readable at thumbnail size)")


@app.command("paperback")
def paperback_cmd(book_id: str) -> None:
    """Rebuild the paperback interior PDF and wraparound cover for a book."""
    from . import paperback

    cfg = _cfg()
    b = state.load_book(cfg, book_id)
    info = paperback.build(cfg, b)
    gitops.commit(cfg, f"{book_id}: paperback")
    typer.echo(json.dumps(info, indent=2))


@app.command("author-page")
def author_page(pen_name: str = typer.Argument(..., help="Pen name, e.g. \"Anya Kalloor\""),
                lane: str = typer.Option("", help="What this name writes, e.g. 'Kerala gothic romantasy'")) -> None:
    """Build the Amazon Author Central kit for a pen name: bio, monogram image, books and claim steps."""
    from . import authorpage

    cfg = _cfg()
    if not lane:
        lanes = {v: k for k, v in (cfg.get("pen_names") or {}).items()}
        lane = lanes.get(pen_name, "").replace("_", " ")
    out = authorpage.build(cfg, pen_name, lane)
    gitops.commit(cfg, f"author page: {pen_name}")
    typer.echo(f"Author Central kit: {out.relative_to(cfg.paths.root)}/author-central.md")


@app.command("install-schedule")
def install_schedule(dry_run: bool = typer.Option(False, help="Print the plist without installing")) -> None:
    """Install the 01:00 launchd job (macOS)."""
    cfg = _cfg()
    target, text = schedule.install(cfg, dry_run=dry_run)
    if dry_run:
        typer.echo(text)
    else:
        typer.echo(f"Wrote {target}. Load it with:\n  launchctl load -w {target}")
    typer.echo(f"Wake the Mac before each run (keep it plugged in):\n  {schedule.wake_command(cfg)}")
    typer.echo(f"Cron fallback line:\n  {schedule.cron_line(cfg)}")


@app.command("usage")
def usage() -> None:
    """Usage per book from state/usage.csv (M3 measurement)."""
    typer.echo(report.dumps(report.usage_by_book(_cfg())))


if __name__ == "__main__":
    app()
