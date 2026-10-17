
# Romantasy Factory PRD

2026-10-17 · @Vimal

## How to use this PRD with Claude Code

This PRD specifies a local pipeline, run by Claude Code on your Max plan, that turns a series concept into upload-ready romantasy books, one book per day, with you approving each book before it goes to KDP.
1. Export this doc as Markdown and save it as `PRD.md` in an empty folder, for example `~/romantasy-factory`.
2. In a terminal, run `env | grep ANTHROPIC_API_KEY`. If anything prints, remove it from your shell profile and open a new terminal. If that variable is set, Claude Code bills the API instead of your Max plan ([support article](https://support.claude.com/en/articles/11145838)).
3. Run `claude login` and sign in with your Max account only.
4. Start `claude` in the folder and paste: *Read PRD.md fully. Build milestone M1 only, then stop and show me the result. Follow every hard constraint in section 2.*
5. Review M1, then ask for each following milestone in turn (section 11). Don't ask it to build everything in one go.

Appendix A holds the full research. The build copies its rules into `canon/` files that every writing agent must load.

## 1. Overview, goals and success metrics

The factory produces complete romantasy series under one pen name. It drafts a full novel per day and stages it for a 45-minute human review and a 15-minute upload.
**Product name:** Romantasy Factory (working name). **Owner and only user:** Vimal (operator, reviewer, publisher). **Platform:** Claude Code CLI on the owner's Mac, authenticated with the Claude Max plan. No API key, no other paid model APIs for text.
**Goals**
- Produce one upload-ready book package per day: manuscript (EPUB + DOCX), cover image, blurb, metadata, AI-disclosure notes.
- Organise output into series of 3 to 6 books with one series bible, so later books keep continuity and drive read-through.
- Apply the research in Appendix A as enforceable rules: every chapter is checked against the scene and chapter checklists before it is accepted.
- Run unattended overnight and resume after usage limits or crashes without losing work.
- Keep the owner's hands-on time to about 1 hour per book.

**Non-goals**
- No unattended uploading to KDP (section 8).
- No KDP account creation, tax forms, passwords or payments handled by Claude.
- No ads, newsletter or social media automation in v1.
- No imitation of named living authors' prose or reproduction of any copyrighted text.

**Success metrics**
| Metric | Target | How measured |
|---|---|---|
| Packages produced | 1 per day when usage allows | `state/` log |
| Review pass rate | 70%+ approved on first review | Review log |
| Critic score | Every chapter at or above threshold (section 6) | Critic reports |
| Continuity errors found by owner | 0 per book after M5 | Review log |
| Average Amazon rating | 4.0+ after 10 ratings | Manual check monthly |
| Read-through, book 1 to 2 | 40%+ | KDP reports, manual |

The last two targets are aspirations to watch, not promises; the research shows no way to guarantee them.

## 2. Hard constraints

These rules override anything else in this PRD. Claude Code must refuse to build anything that breaks them.
**Usage: Max plan only**
- All model calls go through the `claude` CLI (`claude -p` for headless runs), signed in with the Max account. Never use the Anthropic SDK, never read or set `ANTHROPIC_API_KEY`, never call any other paid text-model API.
- The orchestrator checks at startup that `ANTHROPIC_API_KEY` is unset and exits with an error if it is set. With that variable set, Claude Code bills the API instead of the plan ([Anthropic support](https://support.claude.com/en/articles/11145838)).
- Plan usage is shared between the Claude app and Claude Code, with a five-hour session limit and a weekly limit ([same article](https://support.claude.com/en/articles/11145838)). When a limit is hit, the run pauses and resumes later. It never offers to switch to paid credits. Keep "extra usage" switched off in Claude settings.
- Cover images: generated in the owner's Claude chats or another tool the owner already pays for. The pipeline writes the image prompt; it does not call a paid image API by itself (section 7).

**Amazon KDP rules (checked October 2026)**
| Rule | What the build must do | Source |
|---|---|---|
| Max 3 new titles per day per account | Never stage more than 1 book per day for upload; the cap is per account, not per pen name | [Authors Guild](https://authorsguild.org/news/amazon-adds-to-kdp-generative-ai-policy-caps-daily-self-publishing-uploads/), [ALLi](https://selfpublishingadvice.org/self-publishing-news-kdp-ai-new-limits-on-titles/) |
| AI-generated text and images must be disclosed per title | Every package includes `ai-disclosure.md` stating text and cover were AI-generated | [Univers guide](https://univers.studio/blog/kdp-ai-content-policy-2026/) |
| Lightly edited AI output can be flagged as disappointing content | Quality gates in section 6 are mandatory, not optional | [BookWriter guide](https://www.bookwriter.vip/amazon-kdp-ai-publishing-guide-2026) |
| No KDP publishing API exists | Upload is done in a browser with the owner present (section 8) | Owner's account |

**Safety and legal**
- No passwords, 2FA codes, tax or bank details are ever stored in the repo, typed by an agent, or put in prompts.
- No reproduction of lyrics, poems or passages from existing books. No real living authors named as style targets in prompts; use descriptions of qualities instead.
- No content that sexualises minors; all characters in romantic or sexual scenes are explicitly adults. The canon includes this rule and the critic fails any chapter that breaks it.
- Every book carries the pen name's own copyright line; nothing claims to be human-written.


## 3. Daily workflow and human touchpoints

The machine works overnight; the owner spends about an hour each day, split into review and upload.
**Once per series (owner, about 2 hours)**
1. Run `factory new-series`. The concept agent proposes 3 series concepts built from the premises and opportunities in Appendix A.
2. Pick one, edit the series bible draft, approve it with `factory approve series <id>`.
3. Generate the series cover style brief and pick a cover look.

**Every day (machine, overnight, about 01:00 to 07:00 IST)**
1. Scheduler starts `factory run` at 01:00.
2. The orchestrator finds the next unfinished book and continues from its last completed stage.
3. Stages run in order: outline, draft chapters, critique and revise, continuity, line edit, package (section 5).
4. If a usage limit is hit, the run saves state and stops; the next run resumes.
5. At the end, it writes `reports/YYYY-MM-DD.md` and sends a summary to the owner (optional Telegram or email, M7).

**Every day (owner, about 1 hour)**
1. Read the daily report.
2. Review the finished book in `review/<book-id>/` using the review sheet (section 6): chapter 1, the midpoint, the last 3 chapters, the blurb and the cover.
3. Approve with `factory approve book <id>`, or send it back with notes using `factory revise <id> --notes notes.md`.
4. Upload the approved book to KDP (section 8).
5. Mark it live with `factory published <id> --asin <ASIN>`.


## 4. System architecture and repo structure

A small Python orchestrator calls the `claude` CLI once per stage, passing files in and reading files out. All state lives in plain files so any run can resume and the owner can read everything.
**Components**
| Component | Job | Tech |
|---|---|---|
| `factory` CLI | Owner commands: new-series, run, approve, revise, published, status | Python 3.12, Typer |
| Orchestrator | Picks the next stage, calls Claude, validates output, saves state | Python, `subprocess` calling `claude -p` |
| Stage agents | One prompt file per stage in `agents/`, loaded as the system prompt | Markdown + `claude -p --append-system-prompt` |
| Canon | The research rules every agent must follow | Markdown files in `canon/` |
| State store | Book and series progress, stage status, retry counts | `state/*.json` + SQLite index |
| Packager | Builds EPUB and DOCX from chapter Markdown | Pandoc, `epubcheck` |
| Scheduler | Starts the nightly run | macOS `launchd` (fallback: cron) |

**Repo layout**
```markdown
romantasy-factory/
  PRD.md                # this document
  CLAUDE.md             # build rules for Claude Code (from section 2)
  canon/                # rules distilled from Appendix A
    reader-appeal.md
    engagement-techniques.md   # the 26 techniques
    chemistry-worksheet.md
    scene-checklist.md
    chapter-checklist.md
    novel-structure.md
    failure-modes.md
    originality-tests.md
    content-rules.md           # adults only, no copyrighted text, heat level
    style-guide.md             # voice, banned phrases, AI-tell list
  agents/               # one system prompt per stage
  series/<series-id>/
    bible.md            # world rules, cast, arcs, secrets per book
    continuity.json     # facts that must stay true
    books/<book-id>/
      concept.md  outline.md  chapters/ch-01.md ...
      critique/   package/
  state/                # run state, one JSON per book
  review/               # books waiting for the owner
  reports/              # daily run reports
  factory/              # Python source
```
**Why one CLI call per stage:** each call starts with a clean context holding only the files that stage needs. That keeps quality steady across a 30-chapter book and keeps usage predictable.

## 5. Pipeline stages

Each stage reads named files, writes named files, and passes an automatic check before the next stage starts. Default book size: 80,000 to 95,000 words in 30 to 34 chapters of 2,500 to 3,000 words, set in `config.yaml`.
| # | Stage | Reads | Writes | Model | Passes when |
|---|---|---|---|---|---|
| S1 | Series concept | canon/, Appendix A premises, `taste.md` | 3 concepts in `series/_proposals/` | Opus | Each concept passes all 8 originality tests, written as a scored table |
| S2 | Series bible | Approved concept, canon/ | `bible.md`, `continuity.json` | Opus | Bible has world rules with costs, cast with worksheet answers, a per-book arc and a secret map |
| S3 | Book outline | bible, previous books' summaries | `outline.md` with a beat sheet per chapter | Opus | Every chapter lists: POV, goal, value shift, reader question out, technique numbers used |
| S4 | Chapter draft | outline (this and next chapter), bible, continuity, last 2 chapters, style guide | `chapters/ch-NN.md` | Sonnet | Within ±20% of target length; no banned phrases |
| S5 | Chapter critique | chapter, outline beat, checklists | `critique/ch-NN.json` with scores | Opus | Score at or above threshold (section 6), else loop to S6 |
| S6 | Chapter revise | chapter + critique | new `ch-NN.md` | Sonnet | Re-scored; max 2 revision loops, then flag for owner |
| S7 | Whole-book continuity | all chapters, continuity.json | `continuity-report.md`, updated `continuity.json` | Opus | Zero open errors (names, timeline, magic rules, injuries, who knows what) |
| S8 | Line edit | each chapter | edited chapters | Sonnet | Repetition and AI-tell counts under limits in style guide |
| S9 | Book summary | final chapters | `summary.md` (for the next book's context) | Sonnet | Under 1,500 words, covers every open thread |
| S10 | Package | final book | EPUB, DOCX, blurb, metadata, cover prompt, disclosure (section 7) | Sonnet + scripts | `epubcheck` passes; all fields present |

*(Diagram in the original doc: chapter loop draft → critique → revise until pass.)*
Each chapter loops through draft, critique and revise until it passes; only finished books reach you.
**Rules every writing agent follows**
- Load `canon/content-rules.md` and `canon/style-guide.md` on every call.
- Never write past the outline: new plot facts go into `continuity.json` and must be explained in the next critique.
- Each chapter ends on an open question or an interrupted action, but the book's main question resolves by the end of the book (technique 26, Series Hinge).
- Romance changes in every chapter where both leads appear (failure-mode table, Appendix A Part 7).

**Model choice:** Opus for planning and judging, Sonnet for bulk writing, to stretch the Max allowance. Set per stage in `config.yaml` and passed with `claude -p --model`.
**Owner taste file:** `taste.md` holds the owner's choices (heat level, darkness, tropes to use or avoid, comps). S1 to S3 must follow it.

## 6. Quality gates and scoring

A chapter passes only if it scores at least 3.5 average and no single criterion below 3, on a 1 to 5 scale judged by a separate critic call that never sees the drafting prompt.
**Chapter rubric (from Appendix A, Parts 3, 7 and 8)**
| Criterion | Question the critic answers | Source in research |
|---|---|---|
| Reader question | What specific question does the reader carry out of this chapter? | Shaped Gap, Answer-and-Escalate |
| Change | What has changed by the end: power, knowledge or relationship? | Scene checklist |
| Romance movement | Did the relationship change, and is the reason new? | Repetitive-tension failure mode |
| Shown chemistry | Is attraction shown through responsive actions, not narration? | Responsive Care, narrated-only failure |
| Character logic | Would a smart version of this person do this? | Irrational-behaviour failure |
| Stakes and cost | Does the next decision cost something? | Cost Ledger |
| Prose | Repetition, cliché, AI tells, overlong inner monologue | Style guide |
| Continuity | Conflicts with bible or earlier chapters? (0 or 5 only) | Continuity agent |

The critic returns JSON: scores, one-line reasons, and up to 3 concrete fix instructions. The revise agent must address every fix.
**Book-level checks before review**
- The book answers its own central question; only the series hinge stays open.
- Every planted clue in `outline.md` pays off or is logged as a series thread.
- Midpoint reversal exists and changes the romance.
- Heroine changes a belief, shown by a choice she couldn't have made in chapter 1.

**Failure handling**
| Failure | Action |
|---|---|
| Chapter fails after 2 revisions | Mark chapter `needs-owner`, continue the book, flag it in the report |
| Continuity error can't be fixed automatically | Stop the book, report the error, move to the next book |
| CLI error or timeout | Retry once after 5 minutes, then stop and report |
| Usage limit reached | Save state, stop cleanly, resume next run |
| Output file missing or malformed | Retry the stage once with the validation error included |

**Owner review sheet** (`review/<book-id>/review.md`, generated): chapter 1, the midpoint chapter, the last 3 chapters, the blurb, the cover, the list of `needs-owner` items, and the critic's 3 weakest chapters. Approve, or write notes for a revision pass.

## 7. Cover, metadata and packaging

v1 ships Kindle ebooks only; paperback and audio come later. Each package is a folder the owner can upload without editing anything.
**Package contents** (`series/<id>/books/<id>/package/`)
| File | Contents | Check |
|---|---|---|
| `book.epub` | Title page, copyright page, chapters, "Also by" page, next-book teaser | `epubcheck` passes |
| `book.docx` | Same content, fallback upload format | Opens; headings are Heading 1 |
| `cover-prompt.md` | Image prompt in the series cover style, title and pen-name type spec | Matches series brief |
| `cover.jpg` | Added by the owner after generating the art | 2,560 × 1,600 px target, title readable at thumbnail |
| `metadata.json` | Title, subtitle, series name and number, pen name, description, 7 keywords, 3 categories, age and heat notes, price | All fields filled |
| `blurb.md` | Description, HTML-formatted for KDP | Under KDP's length limit |
| `ai-disclosure.md` | What was AI-generated (text, cover art) and which tools | Present |
| `upload-checklist.md` | Every KDP field and its value, in page order | Generated from metadata |

**Cover workflow:** the series bible sets one cover style (palette, motif, type) so all books in a series look like a set. The pipeline writes the prompt; the owner generates the art in a tool they already use, and a script adds title and pen name with a fixed font set.
**Metadata rules**
- Blurb structure: hook line, heroine and her want, the love interest and why he's dangerous to her, the stakes, a closing question. Name the 2 or 3 tropes readers search for.
- Keywords: built from trope + setting + reader phrases (for example *enemies to lovers fae romance*). No author names or trademarked titles.
- Re-check KDP's current limits (description length, keyword boxes, categories, cover size) in M6 against KDP Help; treat the values here as defaults.


## 8. Publishing step: browser-assisted, owner present

Upload is semi-automatic: Claude fills the KDP forms in a browser while the owner is present and signed in, and the owner confirms the final Publish click. It is never part of the unattended nightly run.
**Why not fully automatic**
- KDP has no publishing API, so any automation drives the website. An unattended bot logging in risks the account under Amazon's terms.
- Claude will not type the KDP password or 2FA codes, handle CAPTCHAs, or enter tax or bank details. The owner signs in.
- Claude asks before each submit and before Publish; that confirmation can't be pre-approved for future books.
- The nightly `claude -p` run has no browser; browser control needs the Claude desktop app or Claude in Chrome running with the owner at the computer.

**Flow (experiment in M8)**
1. Owner opens Claude (desktop app or Chrome extension), signs in to KDP in that browser, and says: *Upload book **`<id>`** using its upload-checklist.md.*
2. Claude reads `package/upload-checklist.md` and `metadata.json` from the connected folder.
3. Claude fills Kindle eBook Details: language, title, series, author (pen name), description, keywords, categories.
4. Claude asks before saving each page; owner says yes.
5. On Content: Claude uploads `book.epub` and `cover.jpg`, and fills the AI-content questions from `ai-disclosure.md`. Owner checks the previewer.
6. On Pricing: Claude fills price, territories and KDP Select per `metadata.json`.
7. Claude stops before **Publish** and shows a summary; the owner clicks Publish or tells Claude to.
8. Owner runs `factory published <id> --asin <ASIN>` once KDP shows the ASIN.

**Fallback:** if the browser route fails or KDP changes its pages, the owner uploads by hand from `upload-checklist.md` in about 15 minutes. The pipeline must never depend on the browser step working.

## 9. Scheduling, usage budget and resilience

Whether one full book per day fits inside the Max plan is unknown until measured; M3 measures it on a real book before the schedule is set.
**Usage budget**
- A finished book means roughly 85,000 words written, plus critique and revision passes, so total usage is several times the book's length. Plan usage also covers the owner's daytime Claude chats.
- Every `claude -p` call runs with `--output-format json`; the orchestrator logs the usage fields it returns per stage and per book in `state/usage.csv`.
- After the M3 pilot book, set `books_per_day` in `config.yaml`: 1 if a book fits in one night's run, otherwise 1 book every 2 days. Don't push past the plan by switching to paid credits.
- Levers if usage runs short, in order: Sonnet for critique on chapters that pass first time; fewer revision loops; shorter books (70,000 words); critique every chapter but continuity only per act.

**Scheduling**
- macOS `launchd` job starts `factory run` at 01:00 IST; `pmset` wakes the Mac at 00:55. The Mac must be plugged in.
- One run at a time: a lock file stops overlapping runs.
- The run stops by 08:00 IST so daytime usage stays free for work.

**Resilience**
- Each stage writes to a temp file and renames on success, so a crash never leaves half-written chapters.
- `state/<book-id>.json` records the last completed stage and chapter; `factory run` always resumes from there.
- All of `series/` is committed to a private git repo after each stage, so any output can be rolled back.
- `factory status` shows every book's stage, scores, usage and flags.


## 10. Pen name and series strategy

Web searches on 17 October 2026 found no existing author using any of the six names below, but two sit close to authors already in romance. A final check on Amazon's author search and Goodreads is still needed before choosing.
| Pen name | Exact author match found | Nearby names to note | Verdict |
|---|---|---|---|
| Mara Vellacourt | None | None | Clearest choice |
| Isolde Marrow | None | *Marrow* is a 2025 witch novel by Samantha Browning Shea ([listing](https://www.adlibris.com/nb/bok/marrow-9780593851951)); Isolde is common in Tristan retellings | Good |
| Juno Halloway | None | Juno Dawson writes YA ([profile](https://en.wikipedia.org/wiki/Juno_Dawson)), different genre | Good |
| Wren Ashby | None | Several Ashbys in other genres | Good |
| Avelyn Crane | None | Avelyn Paige writes dark romance ([Goodreads](https://www.goodreads.com/author/show/13914653?tab=author)) | Avoid: same genre, same first name |
| Seraphine Lowe | None | Seraphine Ashe writes erotic short fiction ([profile](https://inboxreads.co/@seraphine_ashe)); a Seraphine Chronicles series exists ([Audible](https://www.audible.fr/author/Sherri-Olson/B0GKCPWX2G)) | Avoid |

A web search can't see every Kindle listing, so "none found" means no visible match, not proof. Search Amazon Kindle Store for the exact name in quotes before committing. A matching domain is optional; it only matters later for a reader newsletter or author site.
**Series strategy**
- Publish series of 3 to 6 books, each book with its own couple or one couple across a trilogy, decided per series in S1.
- Release a series in a short burst (one book every 2 to 7 days), with each book's "Also by" page and next-book teaser in place.
- Keep one pen name per subgenre and heat level so readers get what the name promises.
- The pen name shares the account's 3-titles-per-day cap with any other books you publish.


## 11. Build plan, milestones and acceptance tests

Build in eight milestones and stop after each for the owner to check. M3 is the decision point: one real book, read by the owner, before anything runs on a schedule.
| Milestone | Claude Code builds | Done when |
|---|---|---|
| M1 Foundation | Repo layout, `CLAUDE.md`, `config.yaml`, `factory` CLI skeleton, API-key guard, state files, git setup | `factory status` runs; startup fails if `ANTHROPIC_API_KEY` is set |
| M2 Canon | Split Appendix A into the `canon/` files; write `style-guide.md` with banned phrases and AI tells; write `content-rules.md` | Owner reads canon and approves; every file under 3,000 words |
| M3 Pilot book | Agents S1 to S9 for one book; runs by hand stage by stage | One full book exists; usage logged; owner reads it and writes notes |
| M4 Quality loop | Critic JSON schema, revise loop, book-level checks, review sheet | Pilot rerun scores at threshold; owner rates it better than M3 |
| M5 Series continuity | Series bible, `continuity.json`, book summaries, cross-book context | Book 2 of the pilot series has zero continuity errors in owner review |
| M6 Packaging | Pandoc EPUB/DOCX, `epubcheck`, metadata, blurb, cover prompt and typesetting script, upload checklist | Package validates; Kindle Previewer shows it correctly |
| M7 Scheduling | `launchd` job, wake schedule, lock file, resume logic, daily report, optional Telegram or email summary | 3 nights in a row run unattended and resume correctly after a forced stop |
| M8 Browser upload trial | Upload checklist tuned for the browser flow in section 8 | One book uploaded with Claude filling forms and the owner confirming Publish |

**Rules for Claude Code while building**
- Write tests for the orchestrator (state, resume, validation) with pytest; mock the `claude` CLI in tests so tests use no plan usage.
- Keep every prompt in `agents/` as Markdown, never inside Python strings.
- After each milestone, print what was built, what was tested, and what the owner should check.


## 12. Reader platform: domain and newsletter (M9)

The pen name gets its own website and mailing list so readers of one book can be told about the next, without depending on Amazon. Built after M8, once the first series is live.
| Part | Spec | Done when |
|---|---|---|
| Domain | Pen-name domain, checked for availability at M9; WHOIS privacy on; registered in a way that doesn't show the owner's name | Domain resolves; WHOIS shows privacy service |
| Website | Static site on Vercel: books by series, buy links, sign-up form, about page in the pen name's voice | Lighthouse score 90+; every book page links to Amazon |
| Newsletter | An email service with a free tier, chosen at M9; sender address on the pen-name domain | Test sign-up receives the welcome email |
| Reader magnet | Pipeline writes a free bonus (epilogue or short novella) per series, exported as EPUB | Delivered automatically after sign-up |
| Back matter | Every book's last page links to the sign-up and the bonus | Present in every package |
| Launch emails | Pipeline drafts a launch email per book; owner reviews and sends | Draft lands in `review/` with each book |
| Privacy | Marketing email laws require a physical postal address in each email; use a virtual mailbox or PO box, not a home address | Footer shows the non-home address |

The pipeline drafts emails but never sends them by itself; the owner sends each one.

## Appendix A. The Romantasy Research Bible

Romantasy readers buy a promise: in a dangerous world, one person is seen accurately, chosen deliberately, and made stronger by love. The best-supported tools for delivering it are specific curiosity gaps, suspense about characters readers already like, and intimacy built from disclosure met with understanding. Research current to October 2026.
**Evidence labels used throughout**
- **[EE] Established evidence:** reasonably supported by credible research.
- **[RO] Reader observation:** a pattern in reviews, surveys or discussion; not necessarily representative.
- **[CI] Craft inference:** a reasoned application of research to storytelling.
- **[CH] Creative hypothesis:** an original idea that needs testing.

**Access limits.** Regis, Radway, Comisky and Bryant (1982) and Liebers and Schramm (2017) were read through abstracts and summaries, not full texts. Reddit and BookTok were not mined systematically. Reader observations come from Goodreads threads, one large survey, essays and reviews.

### Ten most consequential findings

1. **The market is large but slowing.** [EE] Circana reported US print romance up 24% year-to-date in mid-2025, with 51 million units in the prior 12 months, more than double four years earlier, and romantasy growing at triple digits. Full-year 2025 then showed romance up only 3.9% (almost 44 million units) and fantasy down 8.7% (24.1 million). The category is moving from land-grab to competition on quality.
2. **One franchise distorts the data.** [EE] *Fourth Wing* and *Iron Flame* sold 2.3 million print copies in 2023; *Onyx Storm* sold 2.7 million in week one, the fastest-selling adult title in BookScan's 20 years.
3. **Appetite is shifting darker and hybrid.** [EE/RO] Circana flagged romance "with a dark twist"; psychological thrillers rose 29%, dark fantasy 23%, horror 13%. The Everand/Fable 2026 State of Reading Report predicts "romantasy fatigue" in a crowded field.
4. **Favourite and disliked tropes.** [RO] A January 2025 ThriftBooks/Talker Research survey of 2,000 US romance readers: forbidden romance 45%, friends-to-lovers 44%, enemies-to-lovers 42%. Most disliked: love triangles 23%, office romance 22%, fake dating 21%.
5. **Curiosity is reward anticipation that boosts memory.** [EE] Kang et al. (2009) and Gruber, Gelman and Ranganath (2014): high curiosity engages reward circuits and improves memory, even for incidental details. Plant clues while the reader is burning with a question.
6. **Suspense needs caring first.** [EE] Zillmann: suspense is fear of bad outcomes for liked characters, peaking at high but not complete certainty. Comisky and Bryant (1982) found suspense rose with liking. A 2025 study (Hirsch, Köppe and Onea, *Journal of Literary Theory*) did not support Zillmann's probability curve and found delay predicted suspense.
7. **The popular Zeigarnik effect failed meta-analysis.** [EE] Ghibellini and Meier (2025) pooled 59 publications: no memory advantage for interrupted tasks (recall ratio 0.99 after the original study), but a reliable urge to resume them (67% resumption vs 50% chance, the Ovsiankina effect). Cliffhangers work through the urge to resume.
8. **Spoiler research is mixed.** [EE] Leavitt and Christenfeld (2011) found spoilers raised enjoyment; Levine et al. (2016) and Johnson and Rosenbaum (2015) found the opposite or nothing. Suspense about how and at what cost can survive knowing what.
9. **Intimacy has a tested mechanism.** [EE] Reis and Shaver's model, supported by Laurenceau et al. (1998): disclosure met with a response that leaves the discloser feeling understood, validated and cared for. That is a precise description of the "being seen" fantasy.
10. **Two pop-science ideas are mostly folklore.** [EE] Dopamine relates to wanting and prediction error, not pleasure (Berridge and Robinson; Schultz). The 1974 "danger makes you fall in love" bridge study has method problems; Foster et al.'s 1998 meta-analysis found a small average effect (d = .27), positive only for already-desirable targets.


### Part 1. Market and readers

**Commercial data**
| Datapoint | Figure | Source | Caveat |
|---|---|---|---|
| US print romance, 12 months to mid-2025 | 51 million units, more than double four years earlier | [Circana, June 2025](https://www.circana.com/post/another-year-of-romance-with-a-dark-twist-circana-bookscan-reports) | Print only; no romantasy category in BookScan |
| Romance growth H1 2025 | +24%; still double-digit excluding Yarros | Circana | Includes *Onyx Storm* spike |
| Romance buyers reading "much more" | 26% | Circana *Future of Books* | Self-report |
| Full-year 2025 romance / fantasy | +3.9% (almost 44m) / −8.7% (24.1m) | [Publishers Weekly](https://www.publishersweekly.com/pw/by-topic/industry-news/financial-reporting/article/99417-print-book-sales-rose-slightly-in-2025.html) | Sharp H2 slowdown |
| *Fourth Wing* + *Iron Flame*, 2023 | 2.3 million print copies | [PW on Entangled](https://www.publishersweekly.com/pw/by-topic/industry-news/publisher-news/article/94874-entangled-publishing-soars-into-the-empyrean.html) | Debut print run 315,000 |
| *Onyx Storm* week one | 2.7 million; fastest adult title in 20 years | Circana | Outlier |

**Self-publishing notes.** [RO/CI] *The Globe and Mail* (August 2026) reports Kindle-chart hits being bought by traditional publishers; Callie Hart's self-published *Quicksilver* is the usual example (details partly from a Wikipedia page flagged as possibly AI-written). PublishDrive claims indie fantasy revenue grew 70% vs 7% for publishers; vendor data, directional only. In Kindle Unlimited, series read-through and release pace matter more than in trade publishing.
**The comp titles succeed for different reasons** [CI]
| Title | Emotional promise | Engine | Lesson |
|---|---|---|---|
| *A Court of Thorns and Roses* | Escape from a gilded cage; love while healing | Retelling, then reinterpreting the first love | A series can reread its own first romance as a warning |
| *Fourth Wing* / *Iron Flame* | Underestimated body, lethal arena, earned power | Survival stakes each chapter, competence, spice | Relentless external threat; readers call it "predictable but super hooked" [RO] |
| *The Cruel Prince* | Power as protection for the powerless | Scheming, betrayal | Romance as a contest of wits |
| *The Serpent and the Wings of Night* | Belonging as prey among predators | Tournament with one survivor | The rules, not attitudes, make them enemies |
| *From Blood and Ash* | Freed from a role; desire as rebellion | Mid-book identity reveal | Momentum can outweigh prose complaints |
| *Throne of Glass* | Becoming legendary | Competition, then epic | Shifting romantic focus mid-series splits readers |
| *The Bridge Kingdom* | Loving the person you were sent to destroy | Dramatic irony | A planted betrayal puts a clock on every tender scene |
| *One Dark Window* | Accepted with the monster inside | Gothic interiority | Intimacy as self, monster and lover |
| *The Invisible Life of Addie LaRue* | Being remembered | One cruel rule | A single costly rule can generate a book |
| *Uprooted* | Wild competence; home | Folklore; magic as temperament | Magic styles as compatibility |
| *The Night Circus* | Wonder; love as collaboration | Atmosphere over plot speed | Polarising pace |
| *The Hunger Games* | Integrity under spectacle | Performed vs real romance | "Is it real?" as uncertainty |

Four engines appear: **arena** (survival pressure), **court** (information and power gaps), **gothic** (threat from within), **rule** (one metaphysical constraint). Readers of one engine don't automatically like another.
**Answers to the market questions**
1. **What readers buy:** being seen and chosen, safety inside danger, empowerment. Radway's 1984 study of 42 readers found escape and vicarious nurturing; romantasy adds the heroine's own power. [RO+EE]
2. **Most memorable parts:** moments, not plots: the first act of protection, the love interest's private vulnerability, a line that reframes everything, the final sacrifice. A Goodreads reader on *Fourth Wing*'s POV switch: it showed how much he loved her and left the question of forgiveness open. [RO]
3. **Enduring vs saturated:** forbidden, friends-to-lovers, enemies-to-lovers, slow burn, forced proximity endure. Fae courts, brooding morally grey males and deadly trials read as interchangeable to critics. [RO]
4. **Best combinations:** one trope supplies proximity, another opposition: enemies + forced proximity; arranged marriage + secret mission; tournament + alliance with expiry; fated bond + resistance to it. [CI]
5. **Beloved vs badly executed:** a reason specific to these characters, a transition readers can track, and a price. Readers audit labels ("not really enemies to lovers"). [CI+RO]
6. **Attachment to characters:** goal clarity, vulnerability, competence and moral choice under pressure (Cohen 2001; Liebers and Schramm 2017). [EE+CI]
7. **On-page chemistry:** responsiveness shown in action, escalating mutual disclosure, banter as proof of understanding, attraction tied to specific observations. [EE+CI]
8. **Memorable leads:** desirable through protective competence, frightening through capacity for harm aimed elsewhere, vulnerable through a private cost, unforgettable through a value they won't trade. [CI]
9. **Why morally grey or forbidden:** being chosen by someone who chooses no one is stronger evidence; it also allows safe simulation of risk. Radway's readers rejected stories where the hero's cruelty went unredeemed: the pleasure is the transformation. [EE+CI]
10. **Complaints:** cheesy dialogue, immature prose, "painful monologues", predictability, stereotyped characters (Goodreads); heroines who don't change, only reveal "inner awesomeness" (*Arc*, 2025); status obsession (Danielle Binks, 2025). [RO]
11. **Gaps:** hypotheses only (below).
12. **Segments:** heat level, darkness, age (YA vs adult), and reader origin. Romance-first readers prioritise the relationship arc and a happy ending; fantasy-first readers audit the worldbuilding. [RO+EE]

**Reader-appeal map**
| Appeal | Need served | Compelling when | Goes wrong when |
|---|---|---|---|
| Being seen accurately | Understood without performing [EE] | Observation is specific and costly | "Not like other girls"; mind-reading |
| Being chosen | Worth, security | Choice has a visible price | Possessiveness disguised as choice |
| Hidden power | Escaping smallness | Power brings obligations and moral risk | No change, only revelation [RO] |
| Safety inside danger | Protection without diminishment | She protects him too | Rescue that strips her agency |
| Desired unchanged | Acceptance | Desire includes her "monstrous" parts | Purely physical |
| Found family | Belonging | Each member has an arc | Interchangeable quippy sidekicks |
| Choosing one's fate | Autonomy | Freedom costs something loved | No consequence |
| Worthy despite the past | Shame relief | The past has real victims; repair needed | Trauma as decoration |
| Love that challenges beliefs | Growth | She changes a belief on the page | Change off-page |
| Competence | Efficacy | Visible skill growth | Unearned power-ups |
| Moral intensity | Meaning | Choices between legitimate values | Strawman villains |
| Sensual fulfilment | Desire without shame | Sex changes the relationship or plot | Interchangeable scenes that stall plot |

**Subgenre map**
| Subgenre | Promise | Heat | Ending |
|---|---|---|---|
| Romantasy (core) | Romance and fantasy equal weight | Varies, often explicit | HEA/HFN per couple; series cliffhangers common |
| Fantasy romance | Romance arc is primary | Varies | HEA required |
| Dark romantasy | Danger, taboo, antihero | High | HEA, often morally compromised |
| Gothic romance | Dread, secrets | Low to moderate | Ambiguous to HEA |
| Paranormal romance | Contemporary + supernatural | Moderate to high | HEA |
| Cozy romantasy | Comfort, low stakes | Low | HEA |
| Literary fantasy with romance | Theme, image, voice | Low | Bittersweet allowed |

**Regis's eight elements** [EE, via summaries]: society defined, meeting, barrier, attraction, declaration, point of ritual death, recognition, betrothal, in any order. The most useful genre contract checklist available.
**Market gaps, all hypotheses**
1. [CH] Heroines who change a belief, not just reveal power (supported by critical comment, not sales).
2. [CH] Non-aristocratic love interests whose power is competence or office.
3. [CH] Older protagonists, neurodivergence (weak survey evidence).
4. [CH] Conflict from value disagreement rather than miscommunication.
5. [CH] Non-European folklore and non-court settings (Norse and pirate variants rising per *Globe and Mail*).
6. Discounted: vendor claims of "97% underserved demand" (proprietary, commercial).


### Part 2. The psychology of obsession

**Evidence status**
| Mechanism | Popular claim | What research supports | Status |
|---|---|---|---|
| Information-gap curiosity | Open loops grip readers | Curiosity comes from awareness of a specific gap (Loewenstein 1994); peaks at intermediate confidence; engages reward and memory (Kang 2009; Gruber 2014) | [EE] |
| Prediction | — | Making a prediction raises curiosity (Brod and Breitwieser 2019) | [EE], lab |
| Suspense | Danger = suspense | Needs a liked character and probable but uncertain harm (Zillmann; Comisky and Bryant 1982) | [EE], curve contested 2025 |
| Anomalous suspense | Rereads can't be suspenseful | Readers feel suspense about known outcomes (Gerrig 1989) | [EE] |
| Narrative order | — | Order of events produces suspense, curiosity or surprise (Brewer and Lichtenstein 1982); surprise improves recall of earlier events (Hoeken and van Vliet 2000) | [EE] |
| Spoilers | Spoilers ruin stories | Mixed results | Contested |
| Zeigarnik | Unfinished = remembered | No recall advantage; resumption urge holds | Popular claim unsupported |
| Transportation | Immersion persuades | Meta-analysis of 132 effect sizes (van Laer et al. 2014) | [EE] |
| Identification | Readers become characters | Defined and measured (Cohen 2001) | [EE] |
| Fiction and empathy | Fiction builds empathy | Small causal effect (Dodell-Feder and Tamir 2018) | [EE], small |
| Intimacy | Shared secrets bond | Disclosure + perceived responsiveness (Reis and Shaver 1988; Laurenceau 1998); escalating disclosure (Aron 1997) | [EE], real relationships |
| Dopamine | "Dopamine hits" | Wanting and prediction error, not pleasure | Popular claim misleading |
| Misattribution of arousal | Danger makes love | Weak, contested (d = .27, desirable targets only) | Weak |
| Parasocial bonds | Readers love characters | Documented for book characters (Liebers and Schramm 2017) | [EE], limited |

**A. Curiosity and information gaps** [CI from EE]
- **Specific beats vague.** "Why does he never remove his left glove?" works; "a dark secret about the kingdom" doesn't. The reader must know roughly what shape the answer has.
- **A little knowledge raises the itch.** Partial answers increase curiosity more than total ignorance.
- **Make readers predict.** Offer two plausible competing explanations.
- **Plant during peaks.** Clues placed mid-question are remembered (Gruber).
- **Answer and escalate.** The glove hides a binding mark; the mark is a marriage bond; he's already married. To whom?
- **Confusion vs intrigue test:** can a reader state the question in one sentence?

**B. Suspense, anticipation, delayed gratification** [CI from EE]
- Earn liking before threatening; establish desire and decency in the first pages.
- An interrupted kiss works only if the kiss would change something: reveal a secret, break a vow, trigger a magic rule.
- Alternate relief and renewed uncertainty: each payoff grants one wish and opens a new risk.
- Productive tension changes state each time; repetitive tension replays the same refusal. Test: is the reason they can't be together new, or stronger?
- Why the journey beats the kiss: Berridge's wanting/liking split is a plausible analogy, not evidence about readers. Huron's *Sweet Anticipation* (2006) treats anticipation as its own feeling (music research).

**C. Attachment and intimacy**
- [EE, relationships] Intimacy: disclosure → response → the discloser feels understood, validated, cared for. Escalating mutual disclosure raised closeness in 45 minutes (Aron 1997). Threat activates attachment needs (Mikulincer and Shaver 2007).
- [EE, readers] Transportation and identification predict involvement; parasocial romances with book characters exist; attachment style relates to engagement with characters (Rain and Mar 2021). Whether readers bond with couples the same way partners do is untested.
- [CI] Witnessing a formidable character's private vulnerability gives readers privileged knowledge: intimacy plus dramatic irony.
- [CI] Small acts of care beat declarations because they prove the giver noticed a specific need.
- [CI] Trust becomes rational when a character could betray and visibly doesn't.
- [CI] Avoid labels: don't write "avoidant hero"; write a man who leaves rooms when gratitude is offered, with a reason from his history.

**D. Reward and uncertainty**
- [EE] Dopamine neurons signal reward prediction error (Schultz, Dayan and Montague 1997); dopamine drives wanting, not liking (Berridge and Robinson); advance information is itself valued (Bromberg-Martin and Hikosaka 2009).
- [CI] Well-set-up reversals feel rewarding because they break an expectation the reader formed. Unpredictable timing of tender moments may sustain wanting.
- **Ethical line:** alternating cruelty and tenderness is the engine of traumatic bonding in abusive relationships. Use unpredictability in plot and revelation, not as the love interest's policy toward the heroine, unless the book treats it as harm.

**E. Identification and wish fulfilment**
| Fantasy | Status |
|---|---|
| Being seen accurately | [EE] for the real need; [CI] for fiction |
| Nurtured by a formidable partner | [EE], Radway, dated sample |
| Chosen above everyone | [RO] |
| Hidden power or identity | [RO] |
| Desired unchanged | [CI], validation research |
| Feared by the world, trusted by one | [RO] |
| Home among outsiders | [CI]+[RO] |
| Choosing one's fate | [CI], autonomy research |
| Love that challenges assumptions | [CI], self-expansion model |
| Worthy despite the past | [RO] |
| Understood in rejected parts | [CI] |

Additional fantasies [CH]: the competent one finally relied upon; being given a choice for the first time; forgiven without being excused; rest, being with someone whose presence lets vigilance stop.
**F. Fear, danger and contrast**
- [EE, contested] Dutton and Aron (1974) has non-random assignment and unmeasured arousal (critiqued in *Polish Psychological Bulletin*, 2012). Foster et al. (1998): small average effect, only for desirable targets.
- [CI] Danger is a revelation engine, not a love potion: under threat, characters choose, and choices reveal values.
- [CI] Tenderness from the formidable means something because it's costly and selective.
- [CI] Rule: the love interest's danger points outward or is disciplined. Pointed at her, the story must treat it as a problem needing repair.

**G. Grief, sacrifice, irreversible choices** [CI]
- Sacrifice makes love credible because it's a costly, hard-to-fake signal.
- Choices between two sacred values grip harder than good vs evil.
- If death or broken vows can be undone, readers discount future stakes.
- A strength becomes a liability: the protector who can't be protected.
- Foreshadow the choice's structure early so the final choice feels inevitable without shock.

**H. Memory and structure**
- [EE] Brewer and Lichtenstein: the same events produce suspense, curiosity or surprise depending on order. Surprise improves recall of earlier events. Suspense in literary text engages social cognition and prediction regions (Lehne et al. 2015).
- [CI] **Fair surprise:** the clue was present, memorable, and ambiguous in meaning. **Cheating:** a POV character knew and hid it, or the clue appeared after the fact.
- [CI] Callbacks gain meaning when the situation around a repeated line has flipped.
- [CI] Surprising yet inevitable endings come from a choice the character's values set up all along.

**I. Other mechanisms**
- **Zeigarnik:** use the Ovsiankina framing: interrupt actions in progress. [EE]
- **Transportation:** helped by identifiable characters, imaginable plot, verisimilitude (van Laer 2014). [EE]
- **Schema violation:** surprise pleases when it still satisfies the underlying promise. [CI]
- **Status:** court intrigue engages status-tracking; readers are noticing status worship. [CI/RO]
- **Mastery:** training arcs work through visible competence growth. [CI]
- **Shame and secrecy:** an identity secret makes disclosure a test of validation. [CI]
- **Parasocial bonds:** documented; research relies on young, mostly female samples (Schramm et al. 2024 review). [EE]
- **Humour and relief:** resets arousal so the next threat lands harder; banter shows mutual understanding. [CI]
- **Perspective:** dual POV creates dramatic irony about feelings. [RO/CI]
- **Curiosity vs concern:** a mystery can run on curiosity; romance needs concern. [EE+CI]


### Part 3. The 26 engagement techniques

The outline agent tags each chapter with the technique numbers it uses; the critic checks they landed.
| # | Technique | Mechanism and evidence | Example | Fails when | Combine with |
|---|---|---|---|---|---|
| 1 | Shaped Gap | Specific information gap [EE] | The prince never eats in front of anyone, yet his plate is always full when cleared | Gap is vague or no character notices it | 11 |
| 2 | Half-Answer | Partial knowledge raises curiosity [EE] | She learns he doesn't eat because something else feeds on him | Halves never complete | 3 |
| 3 | Answer-and-Escalate | Resolution opens a bigger gap [EE+CI] | The thing feeding on him is a bond to a dead queen whose heir is the heroine | Escalation becomes arbitrary | 17 |
| 4 | Prediction Bait | Predicting raises curiosity [EE, lab] | Two characters argue rival explanations for his scars | Truth is an unsignalled third option | 12 |
| 5 | Liked Before Threatened | Disposition-dependent suspense [EE] | Before the dragon trial, she secretly mends another cadet's armour | Threat comes before any reason to care | 6 |
| 6 | Probable-but-Uncertain | Suspense peaks near but below certainty [EE, contested] | Two of thirty fliers survive the storm crossing, and we believe it | Hero always beats stated odds | 19 |
| 7 | Interrupted Action | Urge to resume (Ovsiankina) [EE] | "The person who killed your brother was—" and the bell tolls | Every chapter, or by coincidence | 8 |
| 8 | Meaningful Interruption | Delay that changes state [CI] | The almost-kiss is interrupted by her sister, who now knows | Random knocks at the door | 14 |
| 9 | Responsive Care | Understood, validated, cared for [EE] | She mentioned once that bells hurt; he chooses the one courtyard without a tower | Omniscient or controlling care | 10 |
| 10 | Disclosure Ladder | Gradual mutual self-disclosure [EE] | Prisoners trade "a question for a question", each costing more | One-sided or instant | 13 |
| 11 | Clue at the Peak | Curiosity boosts memory for incidental details [EE] | Mid-duel, she notices the duke's ring on the wrong hand | Clue too hidden to recall | 12 |
| 12 | Fair Twist | Surprise improves recall of what came before [EE] | The threatening letters were him warning her; every letter rereads as protection | POV hid what it knew | 20 |
| 13 | Dramatic-Irony Intimacy | Reader knows more [RO/CI] | Dual POV: we know he must deliver her to the tribunal | Deceived character looks foolish | 6 |
| 14 | Cost Ledger | Every romantic step has a price [CI] | Each night together, his oath-mark spreads | Costs waived at the climax | 22 |
| 15 | Values Collision | Two legitimate values [CI] | She thinks plague-mages must die; he is one, and agrees | One side is a strawman | 24 |
| 16 | Power Seesaw | Status shift within the scene [CI] | She enters as prisoner, leaves knowing his true name | One partner always dominant | 13 |
| 17 | Midpoint Mirror | Reversal that recasts the first half [CI] | The bargain she made in chapter 1 was proposed by him in another face | Reversal unrelated to romance | 3 |
| 18 | Choice Under Pressure | Choices reveal values [CI] | One antidote: him, or the enemy kingdom's hostage child | A third option appears from nowhere | 19 |
| 19 | Real Losses | Irreversibility sets stakes [CI] | A beloved squadmate dies and stays dead | Shock without grief | 23 |
| 20 | Reinterpretation Callback | Repeated detail gains new meaning [EE, partial] | "I'll always find you": threat in ch. 2, devotion in ch. 30 | Signposted callback | 12 |
| 21 | Known Outcome, Unknown Cost | Anomalous suspense [EE] | Prologue: she's crowned and alone. Who did she lose? | Frame removes all uncertainty | 19 |
| 22 | The Rule That Bites Back | Limits make magic meaningful [CI, Sanderson] | Spoken "I love you" is a binding contract | Rule suspended when inconvenient | 14 |
| 23 | Relief Valve | Humour resets arousal [CI] | After a massacre, he teaches her a silly card game; she cheats; he's delighted | Jokes undercut grief | 9 |
| 24 | Mutual Transformation Proof | Change shown by a new choice [CI+RO] | She who never asks for help asks him, in front of her enemies | Change told, not shown | 18 |
| 25 | The Private Face | Unguarded vulnerability [CI] | The feared general practising a lullaby badly, alone | Softness unconnected to plot | 13 |
| 26 | Series Hinge | Resolve the book's question, open a bigger one [EE+RO] | Breaking the curse wakes what the curse held asleep | The book's main question left open | 3 |

**Multi-function scene example** [CH]: he dresses her wound (9); she sees the traitor's brand under his collar (11); she now holds his life (16); she must decide whether to report it, the thing she fears most because her father died for not reporting (18). One scene moves romance, mystery, power and character.

### Part 4. Romantic chemistry

The most combustible combination is high admiration + shared deep values + incompatible immediate goals + a world rule that makes loving costly. The most deadening is attraction + miscommunication + nothing at stake. [CI]
| Component | Creates tension when | Destroys it when |
|---|---|---|
| Attraction | Paired with a reason not to act | It's the only bond |
| Admiration, competence | Each excels where the other is weak | No need for each other |
| Friction | Rooted in values or goals | Rooted in rudeness or misunderstanding |
| Shared values + conflicting goals | They agree on what matters, not how | Goals align too easily |
| Vulnerability | Disclosure is risky and met responsively | Dumped early or one-sided |
| Humour | Shows mutual understanding | Undercuts every serious beat |
| Power | Shifts within scenes and over the arc | Fixed and used to coerce |
| Trust | Earned by declined chances to betray | Assumed or forced |
| Betrayal and repair | Repair needs acknowledgement and changed behaviour | Forgiven instantly or off-page |
| Desire | For this specific person | Generic body description |
| Respect | Survives disagreement | Means agreement |
| Sacrifice | Costly and chosen | Coerced or meaningless |
| Mutual transformation | Both change because of each other | Only one or neither changes |

**Trope engines**
| Model | Deeper engine |
|---|---|
| Enemies to lovers | Being seen by the person with most reason not to; judgement transformed |
| Rivals to lovers | Recognition by an equal; competence as intimacy |
| Forced proximity | The private self exposed; no room to perform |
| Forbidden love | Choosing each other against the world |
| Friends to lovers | Risking a known good for an unknown better |
| Arranged or political marriage | Love as an act of will within constraint |
| Monster romance | Accepting the monstrous in oneself |
| Human and nonhuman | Translating different values or lifespans |
| Second chance | Whether people can change; repair |
| Unequal power | Whether love can discipline power; ethics of rescue |
| Secrets, mistaken beliefs | Whether love survives full knowledge |

**Relationship-design worksheet** (S2 answers it for every couple)
1. What does each consciously want, visible in chapter 1?
2. What do they secretly need?
3. What belief about love or self holds them back, as a sentence they'd say?
4. What do they misunderstand about the other, as a reasonable inference from what they know?
5. What can each offer that nobody else can, tied to plot and world?
6. What makes loving the other morally or practically costly, in world-rule terms?
7. What would make trust rational? List three observable choices.
8. What changes, in them and the world, because they fall in love?
9. Why are these two uniquely suited to challenge each other?
10. What does each refuse to give up, even for the other?
11. What does the reader know before either character does?

**Chemistry without cruelty** [CI/CH]: competence duet (two experts solving what neither can alone); strategic sparring without humiliation; protective reciprocity (each protects in their own domain); translation romance; truthful adversaries who never lie to each other.

### Part 5. Themes and premises

**Sixteen themes** (conflict → fantasy form → conventional treatment → less predictable treatment)
1. **Love vs freedom.** Bond-magic tethers lovers' locations. Usual: break the bond. Fresh: keep it, renegotiate its terms each year.
2. **Memory vs identity.** Memories as currency. Usual: memory restored. Fresh: she falls for him again and he chooses differently this time.
3. **Cost of immortality.** Immortals lose one sense per century. Usual: she becomes immortal. Fresh: he chooses mortality, regrets it, they live with it.
4. **Ethics of power.** Magic drawn from subjects' consent. Usual: the good ruler. Fresh: she abolishes her own power and must be loved ordinary.
5. **Needed vs loved.** Healer loves her patient. Usual: he proves love by not needing her. Fresh: both need each other permanently and accept it.
6. **Becoming who others think you are.** Gods powered by worship. Usual: she reveals her real self. Fresh: the legend was better, and she grows into it.
7. **Loved without being understood.** A truly alien mind. Usual: final understanding. Fresh: permanent partial understanding, accepted.
8. **Duty vs desire.** Physically binding inherited oaths. Usual: oath broken. Fresh: oath fulfilled, and that is the love story.
9. **Grief and reinvention.** Ghosts persist while grieved. Usual: ghost blesses new love. Fresh: the ghost objects, and is right about something.
10. **Love across disagreement about justice.** A judge and a rebel. Usual: one converts. Fresh: they build a third institution.
11. **What we owe past selves.** Vows written young bind magically. Usual: annulled. Fresh: she honours the girl who made it and finds love inside it.
12. **Price of being exceptional.** Power isolates. Usual: found family. Fresh: she gives up exceptionalism to belong.
13. **Safety without freedom.** A warded city; protector as jailer. Usual: escape. Fresh: she redesigns the ward so others can leave.
14. **Ethics of rescue.** Life-debts bind magically. Usual: debt forgiven. Fresh: she rescues him back to equalise, not repay.
15. **Inherited guilt.** Blood curses. Usual: "you're not your father". Fresh: he is partly responsible and must repair.
16. **Right to be forgotten.** Archives that hold souls. Usual: she's saved by being remembered. Fresh: he helps her disappear, losing his own record of her.

**Twenty premises** [CH] (tags: C challenges conventions, U underused emotion, S series engine)
| # | Premise | Hook | Choice and cost | Why it might stand out |
|---|---|---|---|---|
| 1 | The Witness Clause (C) | A truth-scribe whose sworn records become law falls for the border-lord on trial | Record the truth that convicts him, or lie and lose her voice | Power through precision |
| 2 | The Tide-King's Second Wife (S, U) | A diplomat-bride learns the king's first wife was traded to the sea and can be bought back | Free a rival or keep a husband | Second-chance triangle without contrivance |
| 3 | Debt of Warmth (C) | In a frozen city, body heat is currency passed by touch | End the heat-debt system or keep the city alive | Consent and economics as erotic tension |
| 4 | The Understudy (U) | A princess's magical double loves the betrothed who knew all along, and prefers her | Become herself and lose her place, or stay a copy | Being loved as someone else, inverted |
| 5 | The Retired Oracle (C, U) | A 47-year-old seer is summoned by the general her prophecy ruined | Speak and fix his fate again, or let thousands die | Older leads; regret and repair |
| 6 | The Monster's Accountant (C) | An auditor sent to bankrupt a dragon finds the hoard is a pension fund for displaced creatures | Career vs conscience | Comic competence romance in a dark market |
| 7 | A Name Held in Trust (C) | A woman in a political match is given her husband's true name: total command over him | Use it to save her people, or never | Inverts arranged-marriage power |
| 8 | The Last Translator (U) | Two species share no words for feeling; the translator falls for the envoy | Translate honestly and risk war, or shade toward peace | Structural, not contrived, miscommunication |
| 9 | The Exchange Year (S) | This year's royal hostage is warded by the prince she bullied when he was the hostage | Return home or stay | Second chance + enemies; one book per year |
| 10 | Grief-Eater (U) | A man who eats others' grief loves the one widow who won't give hers up | Share her grief to save him, or keep it | Grief romance without a fixer hero |
| 11 | Dreamwarden (S) | Enemy commanders meet nightly in a masked shared dream | Take the city or spare it | Sustained dramatic irony |
| 12 | The Living Reliquary (U) | A devout girl turning into a saint's relic; the heretic treats her as a person | Complete sainthood or flee | Bodily autonomy and faith taken seriously |
| 13 | Borrowed Hours (U) | Her spells drain the life of the person she loves most; her rival starts ageing | Power vs his life | Magic reveals feelings before the characters admit them |
| 14 | The Wound-Taker's Oath (C) | A healer who takes injuries into herself, and a duelist who keeps getting hurt | Refuse to heal him | Refuses the "love cures" fantasy |
| 15 | Heir to the Drowned God (C) | A sacrificed bride finds the sea god is dying and wants an heir | Become a god or stay human | Subverts the monster-bride trope |
| 16 | The Shifting Map (S) | Rival cartographers chart a realm that rearranges when lied to | Map for conquest, or a false map | Rivals to lovers with honesty as stakes |
| 17 | The Defeated Dark Queen (C) | Another story's exiled villain falls for her jailer | Reclaim power to stop the new cruel regime | Accountability without absolution |
| 18 | The Unbonded (C) | In a society of law-enforced fated bonds, she severs hers for a man the magic rejected | Free all bonds or only hers | Questions fated mates |
| 19 | The Poisoned Garden (S) | Her kingdom's green magic poisons the neighbouring land; its envoy is the man she loves | Share scarcity | Ecological stakes |
| 20 | Ghost Wedding (U) | Married to a dead man for his inheritance, she finds his ghost real, furious and fading | Let him go so she can live | Gothic grief romance with a clock |


### Part 6. Worldbuilding that creates emotional stakes

A world rule earns its place when it makes an intimate act (touch, naming, remembering, promising, grieving) politically or bodily costly. Sanderson's laws, as practitioner guidance: magic can solve a problem only as far as readers understand it; limits are more interesting than powers; expand what exists before adding more. [CI]
**Ten questions per magic system:** what people can do; what they can never do; the cost; who benefits; who is excluded; what happens to lovers; which intimate act becomes dangerous; the recurring dilemma; the loophole; what using the loophole costs.
| Concept | Can / never | Lovers' dilemma | Loophole and its cost |
|---|---|---|---|
| Oath-Law | Make words binding / never retract | Every declaration is a contract | Oaths in a dead language; speaker forgets their mother tongue |
| Warmth Economy | Transfer heat / never create it | Touch impoverishes one partner | Mutual-consent contact makes surplus; both must be fully honest during it |
| Name-Ownership | Command by true name / never refuse it | Trust made literal | Split a name between holders; holders fragment |
| Memory Tithe | Pay for magic in memories / never choose which | Every spell risks erasing the beloved | Write memories down; they then feel like someone else's life |
| Shared Dreams | Meet in dreams / never see true faces | Intimacy without identity | Blood shared before sleep reveals faces; nightmares become shared too |
| Wound-Transfer Healing | Move injuries / never erase them | Care is literally self-harm | Spread a wound across many; the community must consent |
| Visible Emotion | Emotions glow on skin / hide only with costly dye | Forbidden love can't be concealed | Wear the partner's emotion; lose your own meanwhile |
| Consent-Gated Magic | Cast on others only with consent | Manipulating consent becomes villainy | Consent given years earlier; the past self binds the present |
| Time Tithe | Draw on others' lifespans / never choose whose | Magic reveals who you love | Redirect love to a community; personal love dims |
| Zero-Sum Ecology | Make land fertile / never without draining elsewhere | Lovers across the drain line | A migrating garden; the court loses its seat |
| Inherited Oaths | Bind descendants / unbind only with the original taker's blood | Sworn by his grandfather to kill her family | Adoption into her family; he loses his lineage |


### Part 7. Failure modes

| Failure | Reader evidence | Craft problem | Repair |
|---|---|---|---|
| Generic protagonist | "Immature and stereotypical" (Goodreads) | No specific want, belief or contradiction | Goal with deadline, false belief, a habit that contradicts self-image |
| Looks instead of personality | Status and beauty critique (Binks) | Desire not tied to traits | Attraction responds to actions she witnesses |
| Narrated-only chemistry | "Cheesy" dialogue | Told, not shown | Techniques 9 and 10 |
| Enemies-to-lovers with no transition | "Not really enemies to lovers" | Enmity unmotivated or dropped | Root enmity in values; map three reversals of judgement |
| Artificial misunderstandings | Widespread complaint | Characters withhold for plot | Make speaking costly (world rule or loyalty) |
| Contrived delays | — | POV knows and withholds | Reveal earlier, escalate the next question |
| Worldbuilding collapse | Fantasy-first readers audit | Rules exist only for set pieces | Write cost and exclusion for each rule |
| Convenient magic | — | Breaks Sanderson's first law | Establish the solving power early, limited |
| Stakes without depth | — | Global stakes, no personal ones | Tie each escalation to a named loved person |
| Trauma as decoration | Critical discourse | Trauma doesn't shape behaviour | Show it shaping choices; partial healing |
| Irrational behaviour to extend plot | "Predictable" | Plot-driven, not character-driven | Would a smart version of this person do it? |
| Twists without setup | — | No retrievable clues | Techniques 11 and 12 |
| Endless monologue | "Painful monologues" | Interiority replaces action | Turn rumination into choices and dialogue |
| Repetitive tension | — | Same obstacle recycled | Each refusal needs a new reason |
| Romance buried by plot | *Iron Flame* read as "more high fantasy" | Relationship stops changing | Every plot event alters the relationship |
| Plot buried by romance | Satire cited by *Arc* | External stakes paused | Use intimate scenes to reveal plot information |
| Over-promising | — | Cover and blurb promise another book | Match comps, heat and darkness to content |
| Static heroine | *Arc* (2025) | Power without change | Technique 24 |

Conventions are not flaws: happy endings, the "point of ritual death", series cliffhangers and spice are genre contracts. Mistakes are in execution, such as a cliffhanger that leaves the book's own question unanswered, or spice that doesn't change the relationship.

### Part 8. Novel design system

**Scene checklist**
- What does each character want in this scene?
- What changes by the end: power, knowledge or relationship?
- What question does the reader carry out?
- What does the reader know that the character doesn't?
- What does this interaction reveal that exposition couldn't?
- What does the next decision cost emotionally?
- Does the relationship change because of this event?
- What detail might gain new meaning later?
- Is suspense from real uncertainty or an artificially withheld answer?
- Does the scene do at least two jobs?

**Chapter checklist**
- Hook on page one: an action or a question.
- At least one partial answer.
- At least one new question bigger than the one answered.
- An emotional turn.
- An ending that interrupts an action or reveals something that makes the next chapter necessary, caused by the story, not coincidence.

**Novel structure** (Regis's elements merged with common romance beats, e.g. Hayes's *Romancing the Beat*) [CI]
| Phase | Romance beats | Fantasy beats | Engagement goal |
|---|---|---|---|
| 0–10% | Society defined; meeting | World rule shown at cost | Liking + shaped gap |
| 10–25% | Attraction; barrier | Inciting threat | Probable-but-uncertain stakes |
| 25–50% | Disclosure ladder; first intimacy | Investigation, training | Half-answers; responsiveness |
| 50% | False declaration or first real choice | Major reversal | Midpoint Mirror |
| 50–75% | Cost ledger rises | Antagonist pressure | Dramatic irony |
| 75–85% | Point of ritual death | All seems lost | Choice Under Pressure |
| 85–95% | Recognition; declaration | Confrontation | Fair twist; transformation proof |
| 95–100% | Betrothal (HEA/HFN) | New balance | Series Hinge |

**Series level:** each book answers its own question and completes one romantic phase; long-term secrets are planted in book 1 and pay off in books 2 and 3; loyalties change on a planned arc; the world expands from the leads' choices.
**Originality tests**
1. Swap the magic system: does the romance change? If not, the world isn't integrated.
2. Can the theme be stated as a question with two legitimate answers?
3. Does the love interest have a goal unrelated to the protagonist?
4. Is the central conflict unsolvable by killing a villain?
5. Does the protagonist change a belief?
6. Is one convention inverted and one fully honoured?
7. Can a reader describe the book without naming a comp title?
8. Does the world make an intimate act politically significant?

**Failure diagnostics:** does chemistry exist without narration saying so? Why these two specifically? Would the misunderstanding survive one honest conversation? Is magic solving a problem it wasn't set up to solve? Does each romantic refusal have a new reason?
**Development prompts**
1. Interview the love interest about the moment he decided to trust her.
2. Three ways the world rule makes the first kiss dangerous.
3. List the clues for the midpoint twist and where each is planted.
4. Write the scene from the antagonist's POV.
5. What would a reader complain about in this outline?
6. Test this chapter against the scene checklist.
7. Five ways to raise the cost of their alliance.
8. The theme's two legitimate answers, assigned to characters.
9. What does the reader know that she doesn't, act by act?
10. Which book-one detail opens book two?


### Reading list

1. Pamela Regis, *A Natural History of the Romance Novel* (2003).
2. Gwen Hayes, *Romancing the Beat* (2016), practitioner guide.
3. Loewenstein, "The psychology of curiosity", *Psychological Bulletin* (1994).
4. Zillmann, "The Psychology of Suspense in Dramatic Exposition" (1996).
5. Reis and Shaver (1988); Laurenceau, Barrett and Pietromonaco, *JPSP* (1998).
6. Ghibellini and Meier, *Humanities and Social Sciences Communications* (2025).
7. Janice Radway, *Reading the Romance* (1984).
8. Brewer and Lichtenstein (1982); Gerrig (1989; *Experiencing Narrative Worlds*, 1993).
9. Gruber, Gelman and Ranganath, *Neuron* (2014); Kang et al., *Psychological Science* (2009).
10. Aron et al., *PSPB* (1997); van Laer et al., *Journal of Consumer Research* (2014); Cohen (2001).
11. Mar and Oatley (2008); Dodell-Feder and Tamir (2018); Berridge and Robinson; Schultz, Dayan and Montague (1997).
12. Huron, *Sweet Anticipation* (2006); Leavitt and Christenfeld (2011); Levine et al. (2016); Liebers and Schramm (2017); Mikulincer and Shaver (2007).
13. Craft, used critically: Sanderson's essays on magic; McKee, *Story*; Cron, *Wired for Story*.


### What we still don't know

1. Whether romantasy is peaking: BookScan has no romantasy category and misses most Kindle Unlimited sales; "fatigue" is a forecast.
2. How well relationship science transfers to readers' bonds with fictional couples.
3. The exact shape of the suspense curve (2025 production studies disagree with Zillmann).
4. Spoiler effects, which likely depend on genre and reader.
5. Reader segments: almost no rigorous studies of romantasy readers specifically.
6. Effects of dark romance on readers: unstudied in the sources reviewed.
7. Which "underserved" niches are real.
8. Whether a values-collision romance can sustain the heat readers expect; whether emotionally complete books still drive read-through; whether readers accept a heroine who changes beliefs at the cost of instant empowerment.


### Most promising creative opportunities

1. **Intimate-act world rules** (Oath-Law, Name-Ownership, Warmth Economy): fuse romance and worldbuilding; most romantasy magic is for combat. Build from a real institution like contract law or debt.
2. **Values-collision couples** (premises 1, 10, 19): replace miscommunication with legitimate disagreement, so the climax tests the relationship.
3. **The changed heroine** (premises 5, 12, 17): transformation, not revelation; name her opening belief and the choice that proves it changed.
4. **Grief and remembrance romance** (premises 2, 10, 20): darkness from loss rather than abuse, in a market moving darker.
5. **Sustained dramatic irony** (premises 4, 9, 11): each lead holds half the secret, so neither is simply fooled.


### Sources

- [Circana BookScan, June 2025](https://www.circana.com/post/another-year-of-romance-with-a-dark-twist-circana-bookscan-reports)
- [Publishers Weekly, 2025 print sales](https://www.publishersweekly.com/pw/by-topic/industry-news/financial-reporting/article/99417-print-book-sales-rose-slightly-in-2025.html)
- [Publishers Weekly, Entangled profile](https://www.publishersweekly.com/pw/by-topic/industry-news/publisher-news/article/94874-entangled-publishing-soars-into-the-empyrean.html)
- [Publishing Perspectives, dark romance](https://publishingperspectives.com/2025/06/circana-cites-dark-romance-in-growing-us-market-sway/)
- [The Globe and Mail, romantasy trends 2026](https://www.theglobeandmail.com/culture/books/article-romantasy-booktok-publishing-trends-2026/)
- [Romance Nerds, trope survey summary](https://www.romancenerds.com/p/romance-tropes-list)
- [Gruber et al. 2014, PubMed](https://pubmed.ncbi.nlm.nih.gov/25284006/)
- [Kang et al. 2009, PDF](https://neuroecon.berkeley.edu/public/papers/Psychol%20Sci%202009%20Kang.pdf)
- [Hirsch, Köppe and Onea 2025, JLT](https://doi.org/10.1515/jlt-2025-2022)
- [Comisky and Bryant 1982](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1468-2958.1982.tb00682.x)
- [Brod and Breitwieser 2019](https://www.nature.com/articles/s41539-019-0056-y)
- [Gerrig 1989](https://www.sciencedirect.com/science/article/pii/0749596X89900016)
- [Laurenceau et al. 1998, PDF](https://www.affective-science.org/pubs/1998/LaurenFBPl1998.pdf)
- [Liebers and Schramm 2017](https://www.researchgate.net/publication/320426014_Friends_in_books_The_influence_of_character_attributes_and_the_reading_experience_on_parasocial_relationships_and_romances)
- [Rain and Mar 2021](https://journals.sagepub.com/doi/abs/10.1177/0265407521996055)
- [Parasocial review 2024](https://www.researchgate.net/publication/379313729_Parasocial_relationships_and_identification_with_fictional_characters_in_adolescents_and_adults_a_systematic_review)
- [Berridge lab, wanting vs liking](https://sites.lsa.umich.edu/berridge-lab/research-overview/neuroscience-of-linking-and-wanting/)
- [Hoeken and van Vliet 2000](https://www.researchgate.net/publication/222121244_Suspense_curiosity_and_surprise_How_discourse_structure_influences_the_affective_and_cognitive_processing_of_a_story)
- [Lehne et al. 2015, PLOS ONE](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0124550)
- [Arc magazine, the problem with romantasy](https://arcmag.org/the-real-problem-with-romantasy/)
- [Danielle Binks, vulgarity of romantasy](https://daniellebinks.substack.com/p/the-vulgarity-of-romantasy)
- [Goodreads, Fourth Wing discussion](https://www.goodreads.com/topic/show/22732056-thoughts-on-fourth-wing?tab=author)
- [Goodreads, overrated thread](https://www.goodreads.com/topic/show/22676414-overrated-or-actually-a-good-read)
- [Everand/Yahoo, romantasy fatigue](https://www.yahoo.com/lifestyle/articles/romantasy-fatigue-even-more-special-195901198.html)
- [PublishDrive romantasy trends](https://publishdrive.com/romantasy-book-trends.html)
- [Quicksilver (Hart novel), Wikipedia](https://en.wikipedia.org/wiki/Quicksilver_(Hart_novel))

