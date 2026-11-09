# 15: A double click on Mark reviewed sends one request and leaves a working Undo

**Blocked by:** None

**Status:** done

**Touches:** webapp/static/views/trial.js, walks/

**Kind:** design

**Spec sections (read these, not this ticket's paraphrase):** Findings › F3 to F7 (review changes); exploration defect E-033. Found by the exploration round of ticket 11 (`.scratch/pr-1-review/explore/`).

**What to build:** The Mark reviewed handler in `trial.js` ignores a press while its request is in flight, so one click records one review and the Undo it draws undoes it.

- [x] Walk: a double click on Mark reviewed, then Undo, undoes the review and prints no script error — walk: test_walk_undo_after_a_double_click_on_mark_reviewed_still_undoes_the_review; red: .scratch/pr-1-review/red/15-walks-f59af47.txt

## Comments
