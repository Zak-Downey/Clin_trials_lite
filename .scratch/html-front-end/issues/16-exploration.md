# 16: Exploration: one round of trying to break it

**Blocked by:** 15

**Status:** done

**Touches:** *

**Kind:** exploration

**Spec sections (read these, not this ticket's paraphrase):** End State 5; Further Notes (areas).

**What to build:** One exploratory walker per area, once: watchlists and review; trial page; find trials; saved search and new matches; summary and export; dialogs and administration. Then one implementer fixes, starting from each walker's red check, only the findings that break an acceptance box of this spec, an In or Partly-in row of the Design coverage table, or a walk guard. Every other finding is added to the spec's Further Notes for the follow-up spec and is not fixed. No second round.

- [x] One findings file per area — doc: .scratch/html-front-end/explore/watchlists-and-review.md; doc: .scratch/html-front-end/explore/trial-page.md; doc: .scratch/html-front-end/explore/find-trials.md; doc: .scratch/html-front-end/explore/saved-search-and-new-matches.md; doc: .scratch/html-front-end/explore/summary-and-export.md; doc: .scratch/html-front-end/explore/dialogs-and-administration.md
- [x] Every defect found is fixed, and the check that found it is in the walk suite and green — check: walks; walk: test_explore_focus_stays_in_the_page_after_next_and_previous; walk: test_walk_an_unbroken_name_does_not_widen_the_trial_page; walk: test_explore_a_slow_search_does_not_draw_over_the_watchlist_the_analyst_went_to; walk: test_walk_a_typed_filter_and_sort_survive_a_check_finishing; walk: test_walk_a_check_where_every_trial_failed_is_not_an_all_clear; walk: test_explore_an_empty_watchlist_can_be_renamed_and_deleted; walk: test_explore_full_recheck_while_a_check_runs_says_why_nothing_started; walk: test_undo_that_the_server_refuses_says_so_and_can_be_pressed_again; walk: test_escape_closes_the_menu_while_focus_is_still_on_its_button; walk: test_copy_summary_does_not_collapse_the_open_trial; walk: test_the_review_bar_stays_small_and_the_page_does_not_scroll_sideways_with_many_long_named_lists; red: .scratch/html-front-end/red/16-walks-ef08ff1.txt
- [x] Each defect has a row in the escape ledger — doc: docs/agents/local/escapes.jsonl (E-001 to E-011, each with its row under ## Escapes in docs/agents/local/ledger.md)
- [x] Every finding that is not a defect against this spec is listed under the spec's Further Notes as follow-up, not fixed — doc: .scratch/html-front-end/spec.md#follow-up-from-the-exploration-round

## Comments
