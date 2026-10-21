# KDP paperback checklist: Oath of Claws

Create it from the Kindle eBook's Bookshelf entry ("+ Create paperback"), so KDP links the two
editions and copies the details. Claude fills this in the browser like the ebook; you say "publish".

| Field | Value |
|---|---|
| Details | Same as the ebook (title, series, pen name, description, keywords, categories) |
| ISBN | Get a free KDP ISBN |
| Print options: ink and paper | Black & white interior with cream paper |
| Trim size | 5.5 x 8.5 in |
| Bleed settings | No bleed |
| Paperback cover finish | Matte |
| Manuscript | `paperback/interior.pdf` (293 pages, gutter 0.5 in) |
| Cover | Upload a cover you already have: `paperback/cover-wrap.pdf` |
| Cover size | ? x ? in, spine None in |
| AI-generated content | Same answers as the ebook (`ai-disclosure.md`) |
| Previewer | Check the spine text sits inside the spine and the barcode area is clear |
| Territories | All |
| Price (USD) | 15.99. KDP shows the printing cost on the Pricing page; keep the royalty above about $3 |
| Expanded distribution | Off at first |

Stop before "Publish Your Paperback Book". Spine and cover sizes follow KDP's formulas; if the
Previewer disagrees, use KDP's cover calculator numbers and run `factory paperback s02-vow-of-teeth-b02`.
