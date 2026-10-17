"""`factory` command line: the owner's interface (PRD sections 3 and 4)."""

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


@app.command("new-series")
def new_series() -> None:
    """S1: propose series concepts from the canon and taste.md."""
    cfg = _cfg()
    folder = series.new_series(cfg)
    gitops.commit(cfg, f"proposals {folder.name}")
    typer.echo(f"Concepts written to {folder.relative_to(cfg.paths.root)}/")
    typer.echo("Read them, edit any concept-N.md you like, then: factory pick <N>")


@app.command()
def pick(concept: int = typer.Argument(..., help="Concept number from the latest proposals"),
         batch: str = typer.Option(None, help="Proposal batch folder (default: latest)")) -> None:
    """S2: draft the series bible for the chosen concept."""
    cfg = _cfg()
    series_id = series.pick(cfg, concept, batch)
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
    gitops.commit(cfg, f"{book_id}: published {asin}")
    typer.echo(f"{book_id} is live as {asin}.")


@app.command()
def run(book: str = typer.Option(None, help="Only work on this book"),
        steps: int = typer.Option(None, help="Stop after this many steps (hand runs, M3)"),
        scheduled: bool = typer.Option(False, help="Nightly mode: stop at schedule.stop_by")) -> None:
    """Continue the next unfinished book from its last completed stage."""
    cfg = _cfg()
    try:
        rep = orchestrator.run(cfg, book_id=book, max_steps=steps, scheduled=scheduled, echo=typer.echo)
    except orchestrator.LockedError as exc:
        _die(str(exc))
    typer.echo(f"Stopped: {rep.stop_reason}. {len(rep.steps)} step(s) done.")


@app.command()
def cover(book_id: str, art: Path = typer.Option(..., exists=True, help="Cover art you generated")) -> None:
    """Typeset title and pen name onto your cover art -> package/cover.jpg."""
    cfg = _cfg()
    b = state.load_book(cfg, book_id)
    pkg = cfg.paths.book_dir(b["series_id"], book_id) / "package"
    meta = read_json(pkg / "metadata.json", {}) or {}
    out = package.typeset_cover(cfg, art, pkg / "cover.jpg", meta.get("title") or b.get("title", ""),
                                meta.get("pen_name") or cfg.get("pen_name"))
    review_copy = cfg.paths.review / book_id
    if review_copy.exists():
        shutil.copy(out, review_copy / "cover.jpg")
    gitops.commit(cfg, f"{book_id}: cover")
    typer.echo(f"Cover: {out.relative_to(cfg.paths.root)} (check the title is readable at thumbnail size)")


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
