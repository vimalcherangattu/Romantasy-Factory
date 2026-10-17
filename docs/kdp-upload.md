# KDP upload: browser-assisted, owner present (PRD section 8, M8)

Upload is never part of the nightly run. Claude fills the forms while you are signed in and
watching, and you confirm the Publish click.

## Rules

- You sign in to KDP yourself. Claude never types your password or 2FA codes, never handles
  CAPTCHAs, and never enters tax or bank details.
- Claude asks before saving each page and stops before Publish. That confirmation can't be
  pre-approved for future books.
- At most 1 book per day goes up (`factory approve book` enforces this). KDP's cap is 3 new titles
  per day per account, shared across pen names.

## Flow

1. Make sure the book is approved and `package/cover.jpg` exists (`factory cover`).
2. Open Claude (desktop app or Claude in Chrome), sign in to KDP in that browser, and say:
   *Upload book `<id>` using its upload-checklist.md.* Connect the factory folder so Claude can
   read `series/<series>/books/<id>/package/`.
3. Claude reads `upload-checklist.md` and `metadata.json` and fills **Kindle eBook Details**:
   language, title, series, author (pen name), description (from `blurb.md`), keywords,
   categories. It asks before saving.
4. **Content:** Claude uploads `book.epub` and `cover.jpg` and answers the AI-content questions
   from `ai-disclosure.md`. Before upload, fill in the cover tool's name in that file. You check
   the previewer.
5. **Pricing:** Claude fills KDP Select, territories, royalty and price from `metadata.json`.
6. Claude stops before **Publish** and shows a summary. You click Publish or tell Claude to.
7. When KDP shows the ASIN: `factory published <id> --asin <ASIN>`.

## Fallback

If the browser route fails or KDP changes its pages, upload by hand from `upload-checklist.md`
(about 15 minutes). The pipeline never depends on the browser step.
