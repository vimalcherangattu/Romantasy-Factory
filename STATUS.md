# Status

Last updated: 2026-11-01

## Current state
- Live on KDP (pen name Anya Kalloor, series The Odiyan Contracts):
  - Vow of Teeth, B0HNPFZT9M
  - Oath of Claws, B0HNT2V324
  - Both ebooks; the ledger has no paperback logged.
- In review: Crown of Night (s02 b03), 92,405 words. Beta reader says "revise", predicted
  rating 4.2. Cover done. Task Hub todo for the owner, due 1 Nov.
- KDP week of 1 Nov: 1 ebook + 1 paperback reserved for parenting Book 1 (slipped from 25 Oct),
  1 ebook free for Crown of Night. Parenting Book 2 reserved for the week of 22 Nov.
- Week of 26 Oct-1 Nov: review cap used (Crown of Night).
- 64 tests pass. Usage to date: 1093 calls, 10.2M output tokens (`state/usage.csv`).

## In progress
- s03-bound-till-the-thaw-b01 (Mira Sangla): S7 and book check done; line edit at ch 27 of 32.
- Queued: s03 b02-b04; s01 archived.

## Next step
- Sun 1 Nov 10:00 IST upload slot: Crown of Night, if the owner approves it.
- Sun night (Mon 2 Nov, 00:52 IST): new week; factory run, up to 2 passes. Bound till the Thaw
  b1 is closest to review and will need its first cover.

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
- Paperback editions are not confirmed or logged for either live book.
