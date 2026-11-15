# Status

Last updated: 2026-11-16

## Current state
- Live on KDP (pen name Anya Kalloor, series The Odiyan Contracts):
  - Vow of Teeth, B0HNPFZT9M
  - Oath of Claws, B0HNT2V324
  - Both ebooks; the ledger has no paperback logged.
- In review, waiting on the owner:
  - Crown of Night (s02 b03): since 1 Nov, cover done.
  - Bound till the Thaw (s03 b01, Mira Sangla): since 8 Nov, 90,981 words, beta 4.2, NO cover yet.
- KDP week of 15 Nov: parenting Book 1 reserved (ebook + paperback); 1 ebook free for romantasy.
  Parenting Book 2 reserved for the week of 22 Nov.
- Week of 9-15 Nov: no book reached review. Week of 16-22 Nov: review cap still free.
- 64 tests pass. Usage to date: about 1461 calls, 13.2M output tokens (`state/usage.csv`).

## In progress
- s03-bound-till-the-thaw-b02: 32/32 drafted; S7 continuity was patched by hand on 16 Nov
  (Glass Lakes named too early in ch 7-8; Mini missing after the ch 24 raid, fixed in ch 24 and 28).
  Now revising (19/32 done; needs-owner ch 21, 32). Queued next: s03 b03, b04. s01 archived.

## Next step
- Sat night (Sun 22 Nov, 00:52 IST): factory run, up to 2 passes; Thaw b2 may reach review.
- Thaw b1 cover: blocked; the ElevenLabs image tools wait on an approval prompt nobody answers in
  unattended runs (flow 2vxqwsQhH2EkmAD6925N, node 7iQ4DLrAjtSEepfrrJcV). Owner task due 22 Nov.
- Sun 10:00 IST upload slot: whichever romantasy book the owner approves (Crown of Night is ready).

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
