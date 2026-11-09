# 13: A late check or review answer never changes the page or the sidebar the analyst moved on to

**Blocked by:** None

**Status:** done

**Touches:** webapp/static/app.js, webapp/static/views/new_matches.js, webapp/static/views/check.js, walks/

**Kind:** design

**Spec sections (read these, not this ticket's paraphrase):** Findings › F4, F5 (the same class); exploration defects E-029, E-030. Found by the exploration round of ticket 11 (`.scratch/pr-1-review/explore/`).

**What to build:** `refresh` in `app.js` asks `alive()` after `await drawSidebar` before it redraws New matches, and New matches sets Find trials' origin only while it is the page drawn. The sidebar redraw on `reviewchange` (and the header re-read in `check.js` `onChange`) drops an answer that a newer request has overtaken.

- [x] Walk: a check that finishes after the analyst left New matches for Find trials does not change where View details came from (the picker offers the Find destination) — walk: test_walk_a_check_finishing_after_leaving_new_matches_does_not_change_where_find_trials_details_came_from; red: .scratch/pr-1-review/red/13-walks-77e0466.txt
- [x] Walk: Mark reviewed then Undo with the first sidebar answer held and released late leaves the badges at the newer counts — walk: test_walk_a_late_older_sidebar_answer_does_not_overwrite_the_newer_badges; red: .scratch/pr-1-review/red/13-walks-77e0466.txt

## Comments
