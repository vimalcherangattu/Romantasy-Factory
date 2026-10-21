# KDP upload checklist: Oath of Claws

Book ID `s02-vow-of-teeth-b02`. Fill KDP's pages in this order. Values come from `metadata.json`.
Re-check KDP's current limits in KDP Help before the first upload of a series (PRD section 7).

## 1. Kindle eBook Details

| Field | Value |
|---|---|
| Language | English |
| Book title | Oath of Claws |
| Subtitle | A Dark Romantasy of Shapeshifter Assassins |
| Series | The Odiyan Contracts (add to existing series after book 1) |
| Series number | 2 |
| Edition number | (leave blank) |
| Author (primary) | Anya Kalloor |
| Contributors | (none) |
| Description | paste from `blurb.md` (HTML) |
| Publishing rights | I own the copyright and I hold the necessary publishing rights |
| Primary audience: sexually explicit images or title | No |
| Reading age | (leave blank: adult) |
| Categories | Kindle Store > Kindle eBooks > Romance > Fantasy; Kindle Store > Kindle eBooks > Romance > Paranormal & Urban > Shifters; Kindle Store > Kindle eBooks > Science Fiction & Fantasy > Fantasy > Dark Fantasy |
| Keyword 1 | arranged marriage shapeshifter assassin romance |
| Keyword 2 | dark romantasy heist ledger |
| Keyword 3 | enemies to lovers married fantasy romance |
| Keyword 4 | forced proximity monsoon fantasy romance |
| Keyword 5 | shared wounds bond fantasy romance |
| Keyword 6 | open door romantasy assassin heroine |
| Keyword 7 | protective hero shapeshifter heroine series |
| Release option | I'm ready to release my book now |

Save and continue (Claude asks before saving).

## 2. Kindle eBook Content

| Field | Value |
|---|---|
| Digital rights management | Owner's choice (default: No) |
| Manuscript | `package/book.epub` |
| Cover | `package/cover.jpg` (upload a cover you already have) |
| AI-generated content | Yes. Answer each question from `ai-disclosure.md` |
| Kindle Previewer | Owner checks chapter 1, a scene break, the Also-by page |
| ISBN | (none for ebook) |

Save and continue (Claude asks before saving).

## 3. Kindle eBook Pricing

| Field | Value |
|---|---|
| KDP Select enrollment | Enroll |
| Territories | All territories (worldwide rights) |
| Primary marketplace | Amazon.com |
| Royalty plan | 70% |
| List price (USD) | 4.99 |
| Other marketplaces | Based on USD price |
| Book Lending | Enrolled |

## 4. Stop before Publish

Claude shows a summary and stops. The owner clicks **Publish Your Kindle eBook** or tells Claude to.
Then run: `factory published s02-vow-of-teeth-b02 --asin <ASIN>`
