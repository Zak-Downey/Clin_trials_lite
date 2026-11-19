# 06: The pull request and the proof know the rule

**What to build:** Two things that keep the rule honest. First, `docs/agents/local/comments-kept.json` decides what the rule lets through, so it joins the files whose change the pull-request notice reports, as `ruff.toml` did: one more path on the notice step of `.github/workflows/checks.yml`, the same path where that file's opening lines list them, in the tests that hold the list (`tests/test_workflow.py`, `tests/test_judge_notice.py`) and in the "Workflows" line of `repo.md`. Nothing else in the workflow changes. Second, `docs/agents/local/breaks.json` gains a break that adds a comment to a line of the app's code and is proved by the `patterns` check. Any break whose `find` or `replace` text held a comment that tickets 02 to 04 removed is rewritten to the text as it now is; the cheap test of the list names them. Then `python3 prove.py` is run once: every break is caught. If the map of the pages needs the new file placed (`tests/test_walk_map.py` says so), place it. Spec: `.scratch/kit-phase-4/spec.md`, "The pull-request notice" and "The proof".

**Blocked by:** 05

**Status:** done

- [x] Red first: the test that holds the list of judging files fails until `docs/agents/local/comments-kept.json` is among them, in the workflow and in the notice's own tests
- [x] The trigger, the job name, the steps that install and run the checks, and the time limit of the workflow are unchanged
- [x] `python3 prove.py` ends 0 with the new break caught by `patterns`; its printed lines are in the comments, with each break that had to be rewritten
- [ ] `python3 checks.py` ends green on this ticket's commit

## Comments
- **Built (06).** `docs/agents/local/comments-kept.json` is now one of the files the pull-request notice names: on the notice step's run line, in the workflow's opening lines, in the "Workflows" line of `repo.md`, and in `JUDGING` of `tests/test_workflow.py` and `tests/test_judge_notice.py`. Red first: `tests/test_workflow.py::test_a_step_names_the_six_files_that_judge_a_pull_request_and_no_other` (renamed from `..._five_files_...`) failed until the workflow step named the file. Added `tests/test_judge_notice.py::test_a_pull_request_that_changes_the_comments_the_rule_keeps_is_told_so_by_name` (green at once: the notice takes its paths from the step). Nothing else in the workflow changed. The map of the pages already places the file (`docs/*`).
- **The proof (06).** New break `comment-left-in-the-app`: adds `# newest first` to `return {"changes": out}` in `webapp/api_trials.py`, proved by `patterns`. No break had to be rewritten: `tests/test_prove.py::test_this_repos_list_of_breaks_is_current` was green before and after. `python3 prove.py` ended 0 in 25 s:

```
summary-one-day-range-refused  tests/test_api_summary.py::test_a_custom_range_is_inclusive_and_validated  caught
summary-import-left-unused  lint  caught
foreign-origin-write-accepted  tests/test_api_review_queue.py::test_a_write_from_a_foreign_origin_or_without_json_is_refused  caught
second-undo-wrong-status  tests/test_api_review.py::test_a_review_applies_in_every_watchlist_records_its_time_and_ids_and_undo_returns_exactly_those  caught
walk-compares-a-value-with-itself  patterns  caught
defect-log-line-names-a-missing-check  escapes  caught
double-click-marks-twice  walks/test_explore_wr_double_click_mark_reviewed_leaves_an_undo_that_fails.py::test_walk_undo_after_a_double_click_on_mark_reviewed_still_undoes_the_review  caught
add-error-outlives-the-edit  walks/test_explore_find_and_add_error_after_a_failed_add_by_id_outlives_the_edit.py::test_explore_the_add_error_is_cleared_when_the_id_is_edited  caught
refused-page-read-as-registry-error  walks/test_explore_find_and_add_page_out_of_range_is_not_a_registry_error.py::test_explore_page_11_is_a_refusal_with_no_retry_and_keeps_the_query_in_the_form  caught
sidebar-not-redrawn-after-a-review  walks/test_explore_wr_an_older_sidebar_answer_overwrites_a_newer_one.py::test_walk_a_late_older_sidebar_answer_does_not_overwrite_the_newer_badges  caught
comment-left-in-the-app  patterns  caught
proof: 11 of 11 breaks caught
```
- **Checks (06).** `python3 checks.py lint patterns escapes unit` green (unit 0.3 min).
