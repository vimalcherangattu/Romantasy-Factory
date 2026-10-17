"""Daily run reports and optional owner notifications (PRD sections 3 and 9, M7).

Tokens and passwords come from environment variables only, never from the repo.
"""

import json
import os
import smtplib
import ssl
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime
from email.message import EmailMessage

from . import claude, state
from .config import Config
from .fsutil import atomic_write, read_text


@dataclass
class RunReport:
    started: datetime = field(default_factory=datetime.now)
    finished: datetime | None = None
    stop_reason: str = ""
    steps: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)
    ready: list[str] = field(default_factory=list)

    def usage(self, cfg: Config) -> dict:
        start = self.started.isoformat(timespec="seconds")
        rows = [r for r in claude.usage_rows(cfg) if r["timestamp"] >= start]
        total = {"calls": len(rows)}
        for key in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
            total[key] = sum(int(float(r.get(key) or 0)) for r in rows)
        return total


def render(cfg: Config, rep: RunReport) -> str:
    usage = rep.usage(cfg)
    books = state.all_books(cfg)
    lines = [
        f"## Run {rep.started:%H:%M}–{(rep.finished or datetime.now()):%H:%M}",
        "",
        f"**Stopped because:** {rep.stop_reason or 'finished'}",
        "",
        f"**Steps completed ({len(rep.steps)}):**",
        "",
        *([f"- {s}" for s in rep.steps] or ["- none"]),
        "",
        "**Ready for your review:** " + (", ".join(f"`review/{b}/review.md`" for b in rep.ready) or "none"),
        "",
        "**Blocked (need you):**",
        "",
        *([f"- {b}" for b in rep.blocked] or ["- none"]),
        "",
        f"**Usage this run:** {usage['calls']} calls, {usage['input_tokens']:,} input / "
        f"{usage['output_tokens']:,} output tokens (cache read {usage['cache_read_input_tokens']:,}). "
        "Full log: `state/usage.csv`.",
        "",
        "**Books:**",
        "",
        "| Book | Status | Stage | Chapters done | Flags |",
        "|---|---|---|---|---|",
    ]
    for b in books:
        chapters = b.get("chapters", {}).values()
        done = sum(1 for c in chapters if c["status"] in ("passed", "edited"))
        flags = sum(len(c.get("flags", [])) for c in chapters) + len(b.get("flags", []))
        lines.append(f"| {b['book_id']} | {b['status']} | {', '.join(b['done'][-1:]) or '-'} | "
                     f"{done}/{b.get('chapter_count', 0)} | {flags} |")
    return "\n".join(lines) + "\n"


def write(cfg: Config, rep: RunReport) -> str:
    rep.finished = rep.finished or datetime.now()
    path = cfg.paths.reports / f"{date.today().isoformat()}.md"
    existing = read_text(path, f"# Factory report {date.today().isoformat()}\n\n")
    body = render(cfg, rep)
    atomic_write(path, existing.rstrip() + "\n\n" + body)
    notify(cfg, f"Romantasy Factory: {rep.stop_reason or 'finished'}. {len(rep.steps)} steps, "
                f"{len(rep.ready)} ready for review, {len(rep.blocked)} blocked. Report: reports/{path.name}")
    return str(path)


def notify(cfg: Config, message: str) -> list[str]:
    sent = []
    if cfg.get("notify.telegram"):
        token, chat = os.environ.get("FACTORY_TELEGRAM_TOKEN"), os.environ.get("FACTORY_TELEGRAM_CHAT")
        if token and chat:
            try:
                data = urllib.parse.urlencode({"chat_id": chat, "text": message}).encode()
                urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=20)
                sent.append("telegram")
            except OSError:
                pass
    if cfg.get("notify.email"):
        host, to = os.environ.get("FACTORY_SMTP_HOST"), os.environ.get("FACTORY_SMTP_TO")
        user, password = os.environ.get("FACTORY_SMTP_USER"), os.environ.get("FACTORY_SMTP_PASSWORD")
        if host and to and user and password:
            try:
                msg = EmailMessage()
                msg["Subject"], msg["From"], msg["To"] = "Romantasy Factory daily report", user, to
                msg.set_content(message)
                port = int(os.environ.get("FACTORY_SMTP_PORT", "465"))
                with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=30) as s:
                    s.login(user, password)
                    s.send_message(msg)
                sent.append("email")
            except (OSError, smtplib.SMTPException):
                pass
    return sent


def status_table(cfg: Config) -> str:
    rows = []
    for s in state.all_series(cfg):
        rows.append(f"Series {s['series_id']}: {s.get('title', '')} [{s['status']}]")
    for b in state.all_books(cfg):
        chapters = b.get("chapters", {})
        avgs = [c["average"] for c in chapters.values() if c.get("average") is not None]
        needs = [k for k, c in chapters.items() if "needs-owner" in c.get("flags", [])]
        rows.append(
            f"  {b['book_id']:<28} {b['status']:<11} done={','.join(b['done']) or '-':<34} "
            f"chapters={sum(1 for c in chapters.values() if c['status'] in ('passed', 'edited'))}/{b.get('chapter_count', 0)} "
            f"avg={round(sum(avgs) / len(avgs), 2) if avgs else '-'} needs-owner={','.join(needs) or '-'}"
            + (f" asin={b['asin']}" if b.get("asin") else "")
            + (f" ERROR={b['errors'][-1]}" if b["status"] == "blocked" and b.get("errors") else "")
        )
    usage = claude.usage_rows(cfg)
    if usage:
        out_tokens = sum(int(float(r.get("output_tokens") or 0)) for r in usage)
        rows.append(f"Usage logged: {len(usage)} calls, {out_tokens:,} output tokens (state/usage.csv)")
    return "\n".join(rows) or "No series yet. Run `factory new-series`."


def usage_by_book(cfg: Config) -> dict:
    out: dict = {}
    for r in claude.usage_rows(cfg):
        b = out.setdefault(r["book_id"], {"calls": 0, "input_tokens": 0, "output_tokens": 0})
        b["calls"] += 1
        b["input_tokens"] += int(float(r.get("input_tokens") or 0))
        b["output_tokens"] += int(float(r.get("output_tokens") or 0))
    return out


def dumps(obj) -> str:
    return json.dumps(obj, indent=2)
