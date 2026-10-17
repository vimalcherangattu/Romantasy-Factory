# Milestone status

Built in one pass on 17 October 2026, at the owner's request, instead of milestone by milestone.
The code for M1, M2 and M4 to M7 is complete and tested with a fake `claude` CLI. M3, M5, M7 and
M8 also have acceptance tests that need real runs, books and nights on your Mac. Those are listed
as **Owner check** below.

| Milestone | Built | Tested here | Owner check |
|---|---|---|---|
| M1 Foundation | Repo layout, `CLAUDE.md`, `config.yaml`, `factory` CLI, API-key guard, state files, git commits | `factory status` runs; every command exits 2 if `ANTHROPIC_API_KEY` is set | Run `factory doctor` on your Mac |
| M2 Canon | 10 `canon/` files from Appendix A, banned-phrase and AI-tell lists, content rules | Every file under 3,000 words; every agent loads content rules and style guide | Read `canon/` and approve, especially `style-guide.md` lists and `content-rules.md` |
| M3 Pilot book | Agents S1 to S9; `factory run --book <id> --steps 1` for hand runs; `factory usage` | Full book runs end to end with the fake CLI; one live critic call verified the output contract | Run one real book stage by stage, read it, write notes; set `schedule.books_per_day` from `factory usage` |
| M4 Quality loop | Critic schema and pass rule, 2-loop revise, `needs-owner`, book-level checks, review sheet | Fail → revise → pass; fail ×3 → `needs-owner`; review sheet contents | Rerun the pilot and judge whether it's better than M3 |
| M5 Series continuity | Bible, `continuity.json` with new facts per chapter, S7 fix round, S9 summaries fed to the next book | Book 2's outline gets book 1's summary; continuity error fixed once, unfixable error blocks | Read book 2 for continuity errors |
| M6 Packaging | Pandoc EPUB/DOCX, epubcheck, metadata/blurb validation, cover prompt, `factory cover` typesetting, upload checklist, AI disclosure | EPUB passes epubcheck 5.3 with 0 warnings; DOCX chapters are Heading 1; cover is 1600×2560 | Open `book.epub` in Kindle Previewer; re-check KDP limits in KDP Help |
| M7 Scheduling | launchd plist, pmset wake command, cron fallback, lock file, stop-by window, resume, daily report, Telegram/email | Lock and stale lock; window times; usage-limit stop and resume; CLI error retry | `factory install-schedule`; 3 unattended nights plus one forced stop |
| M8 Browser upload | `upload-checklist.md` in KDP page order, `docs/kdp-upload.md` | Checklist has every field | One upload with Claude filling forms and you clicking Publish |
| M9 Reader platform | Not built (PRD: after the first series is live) | — | Ask for M9 once a series is live |

## Changes from the PRD

- **System prompt mode.** The PRD says `--append-system-prompt`. The build uses `--system-prompt`
  with tools turned off, because appending kept Claude Code's ~39k-token coding prompt on every
  call. Replacing it measured ~1.3k tokens. To switch back, set `claude.system_prompt_mode: append`.
- **No tool use by agents.** Files go into the prompt and come back as delimited blocks, so the
  orchestrator controls every write, temp file and rename.
- **`factory pick <N>`** was added between `new-series` and `approve series`. It runs S2, so the bible
  draft exists before you approve it (PRD section 3, step 2).
- **`factory unblock <id>`** resumes a blocked book after you've fixed the cause.
- **Premise 12** in the canon says "woman" instead of "girl" to keep the adults-only rule explicit.

## Known limits

- S7, the book checks and S9 each read the whole book (about 120k tokens). If usage is tight, the
  levers are in `config.yaml → levers`.
- epubcheck runs from `brew install epubcheck`, or from a jar in `~/.local/share/epubcheck/`. If it's
  missing, the package is flagged rather than blocked.
- Usage-limit detection matches the CLI's error text. If a future CLI version words it differently,
  the run stops as a CLI error instead. That's still safe, but the report reason will be less exact.
