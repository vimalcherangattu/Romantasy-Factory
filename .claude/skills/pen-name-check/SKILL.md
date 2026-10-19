---
name: pen-name-check
description: Check whether a pen name is already used by an author on Amazon or Goodreads, in the owner's browser. Use when the owner asks to check, confirm or clear a pen name.
---

# Pen-name check

Use the browser (read the `chrome-browser` or `built-in-browser` skill first). Signing in is not
needed.

1. **Amazon Kindle Store:** search for the exact name in quotes. Check the first two pages of
   results and any author page. Then search the surname alone with "romance".
2. **Amazon author pages:** open `amazon.com/s?k="<name>"&i=digital-text` and look for an author
   entry with that name.
3. **Goodreads:** search the name under Authors (`goodreads.com/search?q=<name>&search_type=authors`)
   and under Books.
4. **Near matches:** note authors who share the first name plus a similar surname in romance or
   fantasy, as in PRD section 10's table.

Report one of three verdicts:
- **Clear:** no exact or near match.
- **Clear with notes:** no exact match; list each near match with its genre.
- **Taken:** there's an exact match.

Then add a note to `config.yaml` beside `pen_name` with the date checked. Domain availability is
a separate check. It doesn't show whether an author is already using the name.
