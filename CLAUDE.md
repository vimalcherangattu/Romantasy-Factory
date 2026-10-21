# Build rules for Claude Code

This repo is the Romantasy Factory described in `PRD.md`. These rules come from
PRD section 2 and section 11 and override anything else.

## Hard constraints

- All model calls go through the `claude` CLI (`claude -p`), signed in with the
  owner's Max account. Never use the Anthropic SDK, never read or set
  `ANTHROPIC_API_KEY`, never call any other paid text-model API.
- `factory` refuses to start if `ANTHROPIC_API_KEY` is set (`factory/guard.py`).
  Do not weaken or bypass this check.
- When a usage limit is hit the run saves state and stops. Never offer or add a
  switch to paid credits.
- The pipeline writes cover image prompts; it never calls a paid image API.
- KDP allows 2 new titles per format (ebook, paperback, hardcover) per week per
  account, reset Sunday 00:00 UTC, shared across pen names and the owner's other
  books. Every title created is logged in `state/kdp-ledger.csv` (`factory kdp`,
  `factory kdp-log`); `factory upload` refuses when the week has no slot. Never
  stage more than 1 book per day for review.
- Every package includes `ai-disclosure.md`. Nothing claims to be human-written.
- No passwords, 2FA codes, tax or bank details in the repo, in prompts, or typed
  by an agent. Notification tokens come from environment variables only.
- No reproduction of lyrics, poems or passages from existing books. No living
  authors named as style targets in prompts.
- All characters in romantic or sexual scenes are explicitly adults. The critic
  fails any chapter that breaks `canon/content-rules.md`.
- KDP upload is never part of the unattended run (PRD section 8).

## Working rules

- Prompts live in `agents/*.md` as Markdown, never inside Python strings.
- Canon rules live in `canon/*.md`; every agent call loads
  `canon/content-rules.md` and `canon/style-guide.md`.
- Tests use pytest and a fake `claude` binary (`tests/fake_claude.py`), so tests
  use no plan usage. Run `pytest` before committing.
- Every stage writes to a temp file and renames on success (`factory/fsutil.py`).
- After each milestone, report what was built, what was tested, and what the
  owner should check.
