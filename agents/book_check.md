---
agent: book_check
stage: book_check
canon: [novel-structure, engagement-techniques, failure-modes]
---
# Book-level checks

You verify a finished book meets the structural promises in
canon/novel-structure.md before the owner reviews it. Judge from the chapter
summaries and full chapters given.

## Checks

1. `central_question_resolved`: the book answers its own central question;
   only the series hinge stays open.
2. `clues_paid_off`: every clue in the outline's clue list pays off on the
   page, or is a series thread. List any clue that does neither.
3. `midpoint_reversal`: a midpoint reversal exists and changes the romance.
4. `heroine_belief_change`: the heroine changes a belief, shown by a choice
   she couldn't have made in chapter 1. Quote the choice.
5. `real_loss`: at least one real loss that stays lost.
6. `love_interest_goal`: the love interest has a goal unrelated to the
   heroine.
7. `series_hinge`: the last chapter opens a bigger question for the next book.

## File to return

`book-check.json`:

```
{"checks": [{"name": "central_question_resolved", "pass": true, "evidence": "ch 31: ..."}],
 "series_threads": [{"clue": "C07", "thread": "..."}],
 "summary": "one paragraph"}
```
