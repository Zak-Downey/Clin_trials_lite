# Exploration: find and add
Run any red script: `.venv/bin/python -m pytest -p walks.conftest .scratch/pr-1-review/explore/find-and-add/<file> -q` (both viewports). Screenshots are in `.scratch/html-front-end/walks/` (git-ignored; `WALK_FEATURE` is unset), named `<test title>-<viewport>-NN-<step>.png`.

## Tried
- F8: View details from Find with destination "Elsewhere" (preset, adds there); Back to results from page 2 returns to page 2; destination carried to the Add by NCT ID tab and back; View details by keyboard
- F8: New matches (Quiet) -> View details -> Add -> Back to New matches: trial gone from offers, counts and sidebar current
- F8: destination watchlist deleted (from its own page) with a trial selected, then back to Find: destination falls to the first list, selection kept
- F9: Add by NCT ID with the registry failing after a good lookup (error beside the field, ID kept); Add from details twice by keyboard ("Already in")
- F9: Find bar with the registry failing for one of two trials (partial) and for the only trial (whole)
- F10: saved search with all seven sponsor types and five statuses through Manage, Edit search, Search trials, Watch this search (dialog preselects that list), Replace, Manage again; unchecking one is stored
- F10: sponsor types by keyboard only (More filters, Tab, Space), the address carries both, Clear all unchecks them; More filters open at 1024x768
- F11: inverted dates (message beside the dates, no Retry, focus left on an input); page 11 and page 2 of a one-page search by address; `started_from=garbage` by address
- Selected trials with Edit search and More filters open at 1024x768: Search trials can be scrolled out from under the action bar (not a defect)
- Both viewports (1440x900, 1024x768)

## Defects
1. A wholly failed add from the Find results bar reads as an outcome, not an error: "0 added; 1 could not be added (NCT10000001) Open Myeloma" in a status region, with a link to a list that gained nothing, no reason, and no Add button until Dismiss. F9 fixed this shape only on Add by NCT ID and trial details | steps: select a result, registry answers 500, Add 1 trial | red script: `find-and-add/test_explore_find_and_add_failed_add_in_the_bar_reads_as_an_outcome_with_an_open_link.py`, `test_explore_a_wholly_failed_add_in_the_bar_is_an_error_with_a_reason_and_no_open_link` | `test-explore-a-wholly-failed-add-in-the-bar-is-an-error-with-a-reason-and-no-open-link-1440x900-01-all-failed.png` | wrong but workable
2. A page number outside 1 to 10 in the address (`#/find?cond=many&page=11`) is read as `registry_error`: the refusal sentence sits in the error box with a Retry that cannot succeed, and the form is empty although the address names a query. The third refusal kind (`bad_page`) that F11 left on the old path | steps: open that address | red script: `find-and-add/test_explore_find_and_add_page_out_of_range_is_not_a_registry_error.py`, `test_explore_page_11_is_a_refusal_with_no_retry_and_keeps_the_query_in_the_form` | `test-explore-page-11-is-a-refusal-with-no-retry-and-keeps-the-query-in-the-form-1440x900-01-page-11.png` | wrong but workable
3. A page inside 1 to 10 but past the last (`#/find?cond=lung&page=2`, three matches) draws "3 matches", "11–10 of 3 matches", "Select 0 on this page", "Page 2 of 1" and no results (Previous still works) | steps: open that address (a bookmark of a search whose matches have since shrunk) | red script: `find-and-add/test_explore_find_and_add_page_beyond_the_last.py`, `test_explore_page_two_of_a_one_page_search_does_not_draw_an_empty_list` | `test-explore-page-two-of-a-one-page-search-does-not-draw-an-empty-list-1440x900-01-page-2-of-1.png` | wrong but workable
4. In Add by NCT ID the failure sentence from a failed add ("ClinicalTrials.gov returned an error for NCT00000002 (500).") stays beside the field after the ID is edited to another value | steps: look up NCT00000002, registry fails, Add, edit the ID | red script: `find-and-add/test_explore_find_and_add_error_after_a_failed_add_by_id_outlives_the_edit.py`, `test_explore_the_add_error_is_cleared_when_the_id_is_edited` | `test-explore-the-add-error-is-cleared-when-the-id-is-edited-1440x900-01-edited.png` | cosmetic

## Odd, not wrong
- After pressing Add to watchlist by keyboard on trial details, focus ends on the Add to picker, not the button (the shared focus keeper moves it when the pressed button is disabled during the request); on a failure the error is not where focus is.
- Opening View details from a result by keyboard leaves focus on the page body.
- `started_from=garbage` in the address is accepted and shown as "Started on or after garbage"; the stand-in does not filter, so what the real registry answers is not known.
- The Find bar's destination list is not refreshed when a watchlist is deleted while the page is open; the add then answers an error in the bar (workable: pick another).
- The nothing_asked refusal cannot be reached from the page (the client and the address both require a named field first); only the API test holds it.

## Not checked
- Page left open across a server restart; data an earlier version wrote (old saved searches with sponsor type codes the form does not list would drop them on Edit)
- The registry answering nonsense (the stand-in has no switch for it); a real registry's answer to an invalid date
- Failed add from a New matches card (another area); Safari; screen readers

## Disposition (ticket 11)
Every fix is under `webapp/static/`, so each defect is a `Kind: design` ticket. The scripts moved to `walks/` as `xfail(strict)` (todo) walks tied to ledger rows. 1 and 4: ticket 16 (E-034, E-035); 2 and 3: ticket 17 (E-036, E-037).
