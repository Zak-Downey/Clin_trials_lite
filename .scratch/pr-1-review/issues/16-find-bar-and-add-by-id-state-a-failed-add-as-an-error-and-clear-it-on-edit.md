# 16: A wholly failed add from the Find bar is an error with a reason, and an Add by NCT ID error clears when the ID is edited

**Blocked by:** None

**Status:** ready-for-agent

**Touches:** webapp/static/views/find.js, webapp/static/views/add_by_id.js, walks/

**Kind:** design

**Spec sections (read these, not this ticket's paraphrase):** Findings › F9; exploration defects E-034, E-035. Found by the exploration round of ticket 11 (`.scratch/pr-1-review/explore/`).

**What to build:** When every trial in a Find bar add fails, the bar shows an error (not the added-outcome status) with the reason and no Open link, and the Add button stays. The failure sentence beside the Add by NCT ID field is removed when the ID is edited.

- [ ] Walk: a wholly failed add in the Find bar is an error with a reason and no Open link, and Add is still offered — walk: test_explore_a_wholly_failed_add_in_the_bar_is_an_error_with_a_reason_and_no_open_link; todo until this ticket is built: the walk is in the suite as `xfail(strict)` in walks/test_explore_find_and_add_failed_add_in_the_bar_reads_as_an_outcome_with_an_open_link.py against ledger row E-034; remove the mark when it passes
- [ ] Walk: the Add by NCT ID error is cleared when the ID is edited — walk: test_explore_the_add_error_is_cleared_when_the_id_is_edited; todo until this ticket is built: the walk is in the suite as `xfail(strict)` in walks/test_explore_find_and_add_error_after_a_failed_add_by_id_outlives_the_edit.py against ledger row E-035; remove the mark when it passes

## Comments
