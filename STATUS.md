# Status

Last updated: 2026-11-23

## Current state
- Live on KDP (pen name Anya Kalloor, series The Odiyan Contracts):
  - Vow of Teeth, B0HNPFZT9M
  - Oath of Claws, B0HNT2V324
  - Both ebooks; the ledger has no paperback logged.
- In review, waiting on the owner:
  - Crown of Night (s02 b03): since 1 Nov, cover done.
  - Bound till the Thaw (s03 b01, Mira Sangla): since 8 Nov, NO cover.
  - The Winter Oath (s03 b02): since 22 Nov, avg 4.05, no needs-owner chapters, NO cover.
- KDP week of 22 Nov: full (parenting Books 1 and 2, ebook + paperback). Week of 29 Nov: free.
- Ready buffer full (3/3), so new books do not start until one goes live.
- 64 tests pass. Usage to date: about 1576 calls, 14.1M output tokens (`state/usage.csv`).

## In progress
- Nothing drafting. Queued: s03 b03, b04 (start when a ready book goes live). s01 archived.
- Thaw b2 continuity patches by hand: ch 7-8, 24, 28 (16 Nov); ch 28 sheets and crutch (22 Nov).

## Next step
- Owner: approve one book for the Sun 29 Nov 10:00 IST slot (first free factory slot).
- Covers for Thaw b1 and b2: blocked. ElevenLabs `creative_update_node` (aspect/resolution) waits on
  an approval prompt nobody answers in unattended runs, and on 22 Nov the wait restarted the worker.
  Make them in an attended session, or allow that tool.
- Sat night (Sun 29 Nov, 00:52 IST): factory run only if a book went live; otherwise covers only.

## Known issues
- The auto-approve / auto-publish change requested on 21 Oct was refused by the permission
  classifier. Books still stop at review, and the owner approves them.
- The cloud session has no browser, so uploads need the owner's desktop app with Chrome.
- S7 continuity often ends with 1-2 major errors, which are patched by hand before `factory unblock`.
- Published books still carry the critic's needs-owner fixes:
  - Vow of Teeth: ch 4, 7, 15, 23, 26, 27, 28
  - Oath of Claws: ch 6, 9, 12, 23
- The CLI warns that `ANTHROPIC_BASE_URL` is set in this container. Check that it doesn't route
  away from the Max plan.
- `gitops.push` fails quietly when origin/main moves, for example after a publish from another
  session. Merge origin/main and push by hand.
