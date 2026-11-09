# 14: Keyboard focus stays on Check for updates while it runs, and off the tab bar after View dismissed

**Blocked by:** None

**Status:** done

**Touches:** webapp/static/focus.js, webapp/static/views/check.js, webapp/static/views/new_matches.js, walks/

**Kind:** design

**Spec sections (read these, not this ticket's paraphrase):** Findings › F6; exploration defects E-031, E-032 (the focus class of ticket 16 of html-front-end). Found by the exploration round of ticket 11 (`.scratch/pr-1-review/explore/`).

**What to build:** `focus.js` treats an `aria-disabled` button as usable, so focus stays on Check for updates through the run and after it. View dismissed and Back to new matches put focus on a control of the redrawn view, not on the Summary tab.

- [x] Walk: Enter on Check for updates keeps focus on it while the check runs and after it ends, on Needs review, All trials and Summary — walk: test_walk_check_for_updates_keeps_keyboard_focus_while_it_runs_and_after; red: .scratch/pr-1-review/red/14-walks-e492d7e.txt
- [x] Walk: View dismissed, then Back to new matches, never leave focus on a tab — walk: test_walk_view_dismissed_and_back_to_new_matches_do_not_leave_focus_on_a_tab; red: .scratch/pr-1-review/red/14-walks-e492d7e.txt

## Comments
