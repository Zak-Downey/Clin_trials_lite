# 06: Find trials keeps every sponsor type on edit and shows a refused search by its kind

**Blocked by:** 01, 05

**Status:** done

**Touches:** webapp/static/views/find.js, monitor.py, webapp/api_search.py, webapp/api_saved_search.py

**Kind:** design

**Spec sections (read these, not this ticket's paraphrase):** Findings › F10, F11. Root: User Stories 52–61, 76; Implementation Decisions › API (errors as kinds); Design coverage 7/1, 7/3, 7/F.

**What to build:** Lead sponsor type holds several values, as Trial status does, so a query with two survives Edit search and Replace saved search. `monitor._refuse_unanswerable` raises its two refusals with their own kinds, which the handlers pass through without reading the message. The page shows `nothing_asked` and `bad_dates` beside their fields with the form open, and keeps Retry for `registry_error`.

- [x] Test: an empty query and an inverted start-date window are refused with kinds `nothing_asked` and `bad_dates`, and changing the wording of either message does not change its kind — test: test_the_two_refusals_carry_their_own_kinds_whatever_their_wording_says; test: test_the_refusal_kind_survives_a_reworded_message_on_both_endpoints; red: .scratch/pr-1-review/red/06-unit-454acc3.txt
- [x] Walk: a saved search with lead sponsor types Industry and NIH, opened with Manage saved search, Edit search, then Search trials, still reads "Industry or NIH" and keeps both `sponsor_type` values in the address — walk: test_walk_a_saved_search_with_two_sponsor_types_keeps_both_through_manage_edit_search_and_search_trials; red: .scratch/pr-1-review/red/06-walks-454acc3.txt
- [x] Walk: Search trials with the start dates the wrong way round shows the swap-dates message beside the date fields with More filters open, and no Retry — walk: test_walk_start_dates_the_wrong_way_round_show_the_swap_message_beside_the_dates_with_no_retry; red: .scratch/pr-1-review/red/06-walks-454acc3.txt
- [x] Walk: a registry error still shows the error box with Retry, keeping the form — walk: test_walk_a_registry_error_keeps_the_form_and_retry_runs_the_search_again

## Comments
