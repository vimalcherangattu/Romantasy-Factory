# Romantasy Factory

A local pipeline, run with the `claude` CLI on your Max plan, that turns a series concept into
upload-ready romantasy ebooks: one book per night, reviewed by you before it goes to KDP. The
spec is `PRD.md`; the build rules are in `CLAUDE.md`.

## Setup (once, on your Mac)

```bash
env | grep ANTHROPIC_API_KEY      # must print nothing; remove it from your shell profile if it does
claude login                      # sign in with your Max account only; keep "extra usage" off
brew install pandoc epubcheck     # EPUB/DOCX build and validation
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
factory doctor                    # checks claude, pandoc, epubcheck, git
pytest                            # 40 tests, using a fake claude: no plan usage
```

Edit `config.yaml` (pen name, price, schedule) and `taste.md` (heat, darkness, tropes).

## Once per series (about 2 hours)

```bash
factory new-series                # S1: 3 concepts in series/_proposals/<batch>/
factory pick 2                    # S2: bible draft for concept 2 -> series/<id>/bible.md
# edit bible.md, including its "Cover style" section
factory approve series <id>       # queues the series' books
```

## Every night (machine)

```bash
factory install-schedule          # launchd job at 01:00, prints the pmset wake command
```

`factory run --scheduled` picks the next unfinished book and works through its stages, stopping by
08:00. If it hits a usage limit it saves its place and stops, and the next run carries on. It
writes `reports/YYYY-MM-DD.md` (optionally Telegram/email: set `notify.*` in `config.yaml` and
the `FACTORY_*` environment variables).

## Every day (you, about 1 hour)

```bash
cat reports/$(date +%F).md
open review/<book-id>/review.md   # chapter 1, midpoint, last 3, blurb, cover, needs-owner items
factory approve book <book-id>    # or: factory revise <book-id> --notes notes.md
factory cover <book-id> --art ~/Downloads/art.png   # typesets title + pen name -> package/cover.jpg
# upload with package/upload-checklist.md (docs/kdp-upload.md)
factory published <book-id> --asin B0XXXXXXX
```

Other commands: `factory status`, `factory usage`, `factory unblock <book-id>`,
`factory run --book <id> --steps 1` (hand runs, one stage at a time).

## How it works

| Stage | Agent | Model | Passes when |
|---|---|---|---|
| S1 concept | `agents/concept.md` | Opus | Every concept passes all 8 originality tests |
| S2 bible | `agents/bible.md` | Opus | World rules with costs, cast, worksheet, book arcs, secret map, cover style |
| S3 outline | `agents/outline.md` | Opus | Every chapter has POV, goal, value shift, reader question, techniques |
| S4 draft | `agents/draft.md` | Sonnet | ±20% of target length, no banned phrases |
| S5 critique | `agents/critique.md` | Opus | Average ≥ 3.5, no criterion < 3, continuity 5, no content-rule violation |
| S6 revise | `agents/revise.md` | Sonnet | Re-scored; after 2 revisions the chapter is flagged `needs-owner` |
| S7 continuity | `agents/continuity.md` | Opus | Zero open errors (one automatic fix round, then the book is blocked) |
| Book checks | `agents/book_check.md` | Opus | Failures are flagged on the review sheet |
| S8 line edit | `agents/line_edit.md` | Sonnet | Banned phrases 0, AI tells ≤ 1 per 1,000 words, repetition limits |
| S9 summary | `agents/summary.md` | Sonnet | ≤ 1,500 words with an Open threads section |
| S10 package | `agents/package.md` + `factory/package.py` | Sonnet + scripts | epubcheck passes, metadata complete |

- Each stage is one `claude -p` call with a fresh context. The agent prompt and its canon files
  replace Claude Code's default system prompt (`claude.system_prompt_mode: replace`), and tools are
  turned off. Measured on 17 Oct 2026, that's about 1.3k tokens of overhead per call instead of 39k.
- Every call loads `canon/content-rules.md` and `canon/style-guide.md`.
- Input files go into the prompt; output files come back as `=== FILE: name ===` blocks
  (`agents/_output-format.md`). Malformed output gets one retry, with the validation error included.
- State lives in plain files: `state/<book-id>.json` (plus `state/index.sqlite`). Writes are
  atomic, and `series/` and `state/` are committed to git after every step.
- Usage per call goes to `state/usage.csv`. The cost column is the CLI's API-equivalent figure,
  for information only. On the Max plan nothing is billed per call.

## Layout

```
canon/       rules distilled from PRD Appendix A (all under 3,000 words)
agents/      one prompt per stage
factory/     Python source (orchestrator, stages, validation, packaging, CLI)
templates/   AI-disclosure template
series/      concepts, bibles, books (outline, chapters, critique, package)
state/       run state, usage log
review/      books waiting for you
reports/     daily run reports
docs/        milestones and the KDP upload flow
tests/       pytest suite + fake claude CLI
```
