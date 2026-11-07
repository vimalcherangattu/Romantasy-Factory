# Status

Last updated: 2026-11-08

## Current state
- Live on KDP (pen name Anya Kalloor, series The Odiyan Contracts):
  - Vow of Teeth, B0HNPFZT9M
  - Oath of Claws, B0HNT2V324
  - Both ebooks; the ledger has no paperback logged.
- In review, waiting on the owner:
  - Crown of Night (s02 b03): since 1 Nov, cover done.
  - Bound till the Thaw (s03 b01, Mira Sangla): since 8 Nov, 90,981 words, beta 4.2, NO cover yet.
- KDP week of 8 Nov: 1 ebook + 1 paperback reserved for parenting Book 1 (slipped twice),
  1 ebook free for romantasy. Parenting Book 2 reserved for the week of 22 Nov.
- Week of 2-8 Nov: review cap used (Bound till the Thaw).
- 64 tests pass. Usage to date: about 1220 calls, 11.1M output tokens (`state/usage.csv`).

## In progress
- Queued next: s03-bound-till-the-thaw-b02; s01 archived.

## Next step
- Sun night (Mon 9 Nov, 00:52 IST): new week; make the Thaw b1 cover (ElevenLabs connector was not
  connected on 8 Nov), then factory run up to 2 passes (starts s03 b02).
- Sun 8 Nov 10:00 IST upload slot: whichever romantasy book the owner approves (one slot).

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
