# Romantasy Factory: rules for Claude Code

Pipeline that drafts romantasy series with the `claude` CLI on the owner's Max plan and packages
them for KDP (spec: `PRD.md`). At session start read this file and `STATUS.md`; update
`STATUS.md` at every wrap-up.

## Stack
- Python 3.12+, Typer CLI `factory` (`factory/cli.py`), PyYAML, Pillow, WeasyPrint (paperback
  PDFs), pandoc (EPUB/DOCX), epubcheck jar in `~/.local/share/epubcheck`.
- Agent prompts: `agents/*.md`. Canon: `canon/*.md`. Settings: `config.yaml`. Taste: `taste.md`.
- State: `state/*.json` (books, series), `state/usage.csv`, `state/kdp-ledger.csv`.
- Output: `series/<id>/books/<book>/` (chapters, `package/`), `review/<book>/`, `reports/`.

## Run, test, deploy
- Setup (cloud): SessionStart hook runs `scripts/cloud-setup.sh` (pip install -e ".[dev]", epubcheck).
- Test: `pytest` (fake `claude` binary in `tests/fake_claude.py`; uses no plan usage). Run before committing.
- Status: `factory status`, `factory kdp --weeks 2`, `factory usage`.
- Night run: `factory run --scheduled --max-minutes 110` (scheduled task `trig_01WvDdhMyA2juEB6nHTViJpt`,
  00:52 IST Sun and Mon). Blocked book: patch chapter, then `factory unblock <id>`.
- Cover: `factory cover <id> --art <png> --tool "ElevenLabs (FLUX 3 Image)"` (builds cover.jpg + paperback wrap).
- After review: `factory approve book <id>`; after KDP: `factory published <id> --asin <ASIN>`.
- Other books on the KDP account: `factory kdp-log "<title>" [--reserve YYYY-MM-DD]`.
- Site: `factory site`, then `vercel deploy site/dist --prod`.
- Every step commits; `git.push_refs` pushes `HEAD` and `HEAD:main`. Work branch: `claude/hopeful-faraday-0dtxcg`.

## Hard constraints (PRD sections 2 and 11)
- Model calls only through `claude -p` on the Max account. Never the Anthropic SDK, never read or
  set `ANTHROPIC_API_KEY`, no other paid text-model API. Do not weaken `factory/guard.py`.
- On a usage limit the run saves state and stops. Never offer or add paid credits.
- The pipeline writes cover prompts only; cover art comes from the session's ElevenLabs connector.
- KDP: 2 new titles per format per week per account (Sunday 00:00 UTC reset), shared with the
  owner's other books (parenting series etc.). Factory share: 1 per format per week. Log every
  title in `state/kdp-ledger.csv`; `factory upload` refuses without a slot.
- Owner run rules (21 Oct 2026): runs Sat and Sun nights only, max 2 passes of 110 min per night;
  at most 1 book reaches review per Mon-Sun week (IST), else covers only; stop as soon as a book
  reaches review; never loop until the usage limit. Uploads only in the owner's Sunday 10:00 IST slot.
- KDP upload is never part of the unattended run and never from the cloud session; the owner
  approves each book and confirms Publish.
- Every package includes `ai-disclosure.md`. Nothing claims to be human-written.
- No passwords, 2FA codes, tax or bank details in the repo, in prompts, or typed by an agent.
  Notification tokens come from environment variables only. Never send emails.
- No lyrics, poems or passages from existing books. No living authors as style targets.
- All characters in romantic or sexual scenes are explicitly adults; the critic fails any chapter
  that breaks `canon/content-rules.md`.

## Conventions
- Prompts live in `agents/*.md`, never inside Python strings. Every agent call loads
  `canon/content-rules.md` and `canon/style-guide.md`.
- Every stage writes to a temp file and renames on success (`factory/fsutil.py`).
- Commit messages: `<book-id>: <step>` for pipeline steps; plain imperative for code changes.
- After each milestone, report what was built, what was tested, and what the owner should check.
- Task Hub (Supabase `mbbucsageoyxhekzbmyq`, project `romantasy-factory`) holds owner tasks and notes.
