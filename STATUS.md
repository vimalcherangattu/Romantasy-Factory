# Status

Last updated: 2026-10-27

## Current state
- Live on KDP (pen name Anya Kalloor, series The Odiyan Contracts):
  - Vow of Teeth, B0HNPFZT9M
  - Oath of Claws, B0HNT2V324
  - Both ebooks; the ledger has no paperback logged.
- KDP week of 25 Oct: 1 ebook + 1 paperback reserved for Any Fool Can Have a Baby Book 1
  (Task Hub still "waiting"); 1 ebook slot free for romantasy. Week of 1 Nov: all free.
- Week of 26 Oct-1 Nov: no book has reached review yet (cap 1).
- 64 tests pass. Usage to date: 984 calls, 9.26M output tokens (`state/usage.csv`).

## In progress
- s02-vow-of-teeth-b03 (Crown of Night): 32/32 chapters, beta-reader revision round (status
  revising), then line edit and package. Cover done 27 Oct. Ch 26 and 31 hand-patched 26 Oct.
- s03-bound-till-the-thaw-b01 (Mira Sangla): 32/32 chapters, S7 continuity check.
- Queued: s03 b02-b04; s01 archived.

## Next step
- Sat night (Sun 1 Nov, 00:52 IST): factory run, up to 2 passes; Crown of Night is closest to
  review. Sun 1 Nov 10:00 IST upload slot: no romantasy book approved yet.

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
