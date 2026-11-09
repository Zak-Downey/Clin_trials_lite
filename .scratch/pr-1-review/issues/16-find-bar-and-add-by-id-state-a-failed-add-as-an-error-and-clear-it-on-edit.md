# 16: A wholly failed add from the Find bar is an error with a reason, and an Add by NCT ID error clears when the ID is edited

**Blocked by:** None

**Status:** ready-for-agent

**Touches:** webapp/static/views/find.js, webapp/static/views/add_by_id.js, walks/

**Kind:** design

**Spec sections (read these, not this ticket's paraphrase):** Findings › F9; exploration defects E-034, E-035. Found by the exploration round of ticket 11 (`.scratch/pr-1-review/explore/`).

**What to build:** When every trial in a Find bar add fails, the bar shows an error (not the added-outcome status) with the reason and no Open link, and the Add button stays. The failure sentence beside the Add by NCT ID field is removed when the ID is edited.

- [x] Walk: a wholly failed add in the Find bar is an error with a reason and no Open link, and Add is still offered — walk: test_explore_a_wholly_failed_add_in_the_bar_is_an_error_with_a_reason_and_no_open_link; red: .scratch/pr-1-review/red/16-walks-a7f99be.txt; green at both viewports, xfail mark removed
- [x] Walk: the Add by NCT ID error is cleared when the ID is edited — walk: test_explore_the_add_error_is_cleared_when_the_id_is_edited; red: .scratch/pr-1-review/red/16-walks-a7f99be.txt; green at both viewports, xfail mark removed

## Comments
