# Status

Last updated: 2026-10-25

## Current state
- Live on KDP (pen name Anya Kalloor, series The Odiyan Contracts):
  - Vow of Teeth, B0HNPFZT9M
  - Oath of Claws, B0HNT2V324
  - Both ebooks; the ledger has no paperback logged.
- KDP week of 18 Oct: ebook slots 2/2 used. Week of 25 Oct: 1 ebook + 1 paperback reserved for
  Any Fool Can Have a Baby, Book 1 (parenting series).
- Weekly review cap already reached for the week of 19-25 Oct (both Odiyan books reached review).
- 64 tests pass. Usage to date: 827 calls, 7.87M output tokens (`state/usage.csv`).

## In progress
- s03-bound-till-the-thaw-b01 (Mira Sangla, The Winter Passes): 32/32 chapters, in the S7
  continuity check. Hand patches applied to ch 19, 21, 25 and 26, then unblocked.
- s02-vow-of-teeth-b03 (Crown of Night): drafting, around ch 22 of 32. The daytime run was stopped
  on 21 Oct when the weekend-only rule came in. Queued: s03 b02-b04; s01 archived.

## Next step
- Sat night (Sun 25 Oct, 00:52 IST): done. Factory skipped (weekly cap reached); no covers missing.
- Sun night (Mon 26 Oct, 00:52 IST): new week; factory run, up to 2 passes, stops when a book
  reaches review.
- Sun 25 Oct 10:00 IST: the owner's upload slot. Only the parenting Book 1 is planned that week,
  since no factory book is approved yet.

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
