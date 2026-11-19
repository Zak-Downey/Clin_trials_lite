# 03: The browser tests' time is measured

**What to build:** Nobody knows where the browser tests' time goes: a full run is about 410 walk runs in about two and a half minutes on four workers. Measure one full run of the walks on this machine and record the time of each walk file (its tests summed, set-up and tear-down included), the ten slowest single walks, and how the total splits between set-up, the walk itself and tear-down. The figures go in this ticket's comments, and a short table (the ten slowest files, and the split) goes in `docs/agents/local/repo.md` with the date. Nothing about how the walks run changes in this ticket. If the measurement shows a cheap fix, as ticket 01's did for the unit suite, name it first in `now_what` with the seconds it would save; do not make it here. Spec: `.scratch/kit-phase-3/spec.md`, "The browser tests are measured, not changed".

**Blocked by:** None (can start immediately)

**Status:** done

- [x] The comments hold the time of every walk file from one full run, the ten slowest walks, and the split between set-up, walk and tear-down
- [x] `repo.md` has the short table, dated
- [x] No file under `walks/` changed
- [x] `python3 checks.py` ends green on this ticket's commit

## Comments

- **Two cheap fixes, for `now_what` (not made here).** (1) The stand-in registry's server (`helper.Registry` in `walks/helper.py`) runs `serve_forever` at its default half-second poll, so closing it after every walk waits 0.29 s on average (0.30 s median, 0.51 s at most, over 386 walk tear-downs). Starting it with `poll_interval=0.01`, the fix ticket 01 made for the unit suite's server, takes that to 0.006 s (timed alone, 20 closes each way): about 110 of the 117 seconds of tear-down, about 27 seconds off a full run on four workers. One line, but in `walks/helper.py`, a shared file, so its change runs every walk. (2) `walks/test_walk_guards.py` runs the deliberately broken pages (`walks/broken/`, 12 walks at two sizes, one after the other) once per worker that gets one of its tests, because its fixture is module-wide and the four workers split the file: 4 runs of 25.5 s, 102 seconds where one run would do. Keeping the file's tests on one worker (an `xdist_group` mark and `--dist loadgroup` in `walks/run_walks.py`) saves about 77 worker-seconds, about 19 seconds of a full run (an estimate: the one remaining run then sits on one worker). Together, about 45 seconds of a 152-second run.
- **The run.** One full run of the walks as `walks/run_walks.py` runs them (four workers, both window sizes, the acceptance walk also in WebKit), on the owner's 10-processor Mac on 2026-11-18 at commit 7ae2bbb, with `--junitxml` (time per test, set-up and tear-down included) and `--durations=0`: 412 walk runs passed in 151.7 s (2.5 minutes), nothing re-run. The 412 runs took 598 worker-seconds in all, which is about four workers kept busy the whole time.
- **The split** (from `--durations`, which leaves out phases under 0.005 s): set-up 106.2 s (18%), the walks themselves 374.6 s (63%), tear-down 116.6 s (20%). Of the set-up, 102.3 s is the walk-guard tests' run of the broken pages (above); every other walk starts its app and registry inside the walk, so app start-up counts as walk time. Tear-down is almost all the registry's shutdown (above): 0.29 s a walk.
- **The ten slowest single walks:** the four walk-guard tests that each ran the broken pages, 25.5 to 25.6 s each (`test_walk_guard_fails_a_walk_on_an_uncaught_page_error`, `..._on_a_console_error`, `test_walk_guard_keeps_the_first_of_two_pages_and_a_closed_pages_findings`, `..._on_a_failed_request_or_one_to_somewhere_else`; set-up, the test itself takes no time); `test_all_trials_walk.py::test_walk_a_watchlist_opens_on_needs_review_and_remembers_all_trials` 10.2 s at 1440 x 900 and 10.1 s at 1024 x 768; `test_acceptance_walk.py::test_walk_the_whole_journey_by_keyboard_alone` 9.8 s (Chromium 1440), 9.5 s (Chromium 1024), 9.2 s (WebKit 1440); `test_check_walk.py::test_walk_during_a_check_progress_shows_and_the_queue_and_a_trial_stay_usable[1440x900]` 8.3 s. The next ones are the other three `test_check_walk.py` runs at 8.2 to 8.3 s.
- **Every walk file**, from the junit report (tests run, seconds summed with set-up and tear-down):

| File | Tests | Seconds |
|---|---|---|
| `test_walk_guards.py` | 11 | 103.3 |
| `test_check_walk.py` | 20 | 57.8 |
| `test_acceptance_walk.py` | 15 | 49.4 |
| `test_new_matches_walk.py` | 18 | 36.9 |
| `test_explore_find_trials_stale_response_overwrites_view.py` | 6 | 28.4 |
| `test_all_trials_walk.py` | 16 | 28.3 |
| `test_trial_address_walk.py` | 36 | 24.2 |
| `test_explore_watchlists_and_review_focus_and_state_kept.py` | 6 | 20.9 |
| `test_summary_walk.py` | 14 | 19.3 |
| `test_late_answer_walk.py` | 20 | 18.6 |
| `test_explore_summary_and_export_summary_explore.py` | 22 | 17.5 |
| `test_find_trials_walk.py` | 22 | 16.6 |
| `test_run_walks.py` | 14 | 15.0 |
| `test_watchlist_menu_walk.py` | 8 | 13.6 |
| `test_trial_details_walk.py` | 18 | 13.2 |
| `test_saved_search_walk.py` | 14 | 12.0 |
| `test_find_select_walk.py` | 14 | 11.7 |
| `test_explore_wr_check_for_updates_gives_up_keyboard_focus.py` | 2 | 10.4 |
| `test_add_by_id_walk.py` | 12 | 9.8 |
| `test_trial_page_walk.py` | 16 | 8.9 |
| `test_explore_dialogs_and_administration_dialogs_and_administration.py` | 10 | 8.8 |
| `test_needs_review_walk.py` | 16 | 8.4 |
| `test_origin_walk.py` | 10 | 7.7 |
| `test_explore_saved_search_and_new_matches_saved_search_new_matches.py` | 8 | 7.4 |
| `test_standin_registry.py` | 9 | 5.2 |
| `test_explore_find_trials_focus_lost_after_redraw.py` | 8 | 4.9 |
| `test_explore_wr_check_refresh_clobbers_trial_origin.py` | 2 | 4.8 |
| `test_intervention_changes_walk.py` | 8 | 4.5 |
| `test_explore_wr_view_dismissed_parks_focus_on_the_summary_tab.py` | 2 | 4.1 |
| `test_explore_wr_an_older_sidebar_answer_overwrites_a_newer_one.py` | 2 | 4.1 |
| `test_explore_trial_page_menu_keyboard.py` | 6 | 3.4 |
| `test_explore_trial_page_tab_focus.py` | 4 | 3.3 |
| `test_explore_wr_double_click_mark_reviewed_leaves_an_undo_that_fails.py` | 2 | 3.1 |
| `test_explore_watchlists_and_review_failed_check_is_not_an_all_clear.py` | 2 | 2.4 |
| `test_explore_watchlists_and_review_long_name_overflow.py` | 4 | 2.1 |
| `test_explore_find_and_add_failed_add_in_the_bar_reads_as_an_outcome_with_an_open_link.py` | 2 | 1.9 |
| `test_explore_find_and_add_error_after_a_failed_add_by_id_outlives_the_edit.py` | 2 | 1.5 |
| `test_explore_find_and_add_page_beyond_the_last.py` | 2 | 1.3 |
| `test_explore_find_trials_long_unbroken_query_widens_the_page.py` | 2 | 1.3 |
| `test_explore_trial_page_many_watchlists.py` | 2 | 1.1 |
| `test_explore_find_and_add_page_out_of_range_is_not_a_registry_error.py` | 2 | 1.0 |
| `test_fidelity_check.py` | 3 | 0.0 |
