# 09: The proof covers the picker

**What to build:** `python3 prove.py --pick` proves that picking does not hide a real change. For each break in the list that is proved by a test, it makes the change in the copy and then runs `python3 checks.py --quick --pick` for that test's check (`unit` or `walks`) in place of naming the test: the result must be red. The run is a quick one so that it fits the proof's two-minute limit for each run; a pick that cannot finish inside the limit is reported as that, never as hidden or caught. The copy carries what the picker needs to pick as it would in the working folder (the base from the run log, and the unit record), or the pick is everything and proves nothing. Each printed line says how many tests the pick ran out of how many, and a break whose pick ran everything is reported as "caught, but nothing was picked", so it is not mistaken for proof of picking. It ends 1 when any break was hidden. Breaks proved by a check (`lint`, `patterns`, `escapes`) are left to plain `python3 prove.py`, which is unchanged. **A break the picker hides is a finding:** fix the map or the rule, never the list of breaks; if it cannot be fixed in this ticket, name it first in `now_what` and say that `--pick` should not be used until it is. Run it once for real here. `repo.md`'s line for the proof says when to run this form: after a change to the map or the picker. Spec: `.scratch/kit-phase-3/spec.md`, "Proof".

**Blocked by:** 07

**Status:** done

- [x] Red first, on a small hand-made repo in a temporary folder: a break whose test the pick includes is reported caught with its count; a break the pick leaves out is reported hidden and the command ends 1; a break whose pick ran everything is reported as such
- [x] `python3 prove.py --pick` ends 0 on this repo's list, with at least one unit break and at least three walk breaks caught by a pick smaller than the whole; its printed lines and minutes are in the comments
- [x] Plain `python3 prove.py` prints and ends as it did before this ticket
- [x] `python3 checks.py` ends green on this ticket's commit

## Comments

**2026-11-19, the implementer.** The picker hid none of the seven breaks proved by a test. `python3 prove.py --pick` ended 0 in 4.3 minutes (260 s), run on a clean folder at 4914b5c, right after a whole green `python3 checks.py` there (2.8 minutes), so each break was the only change the picker saw. Three unit breaks were caught by picks of 12, 97 and 2 of 776 unit tests, and three walk breaks by picks of 12, 14 and 14 of 42 walk files.

- One walk break was not proved by picking: `sidebar-not-redrawn-after-a-review` changes `webapp/static/app.js`, which the map lists as shared, so its pick is all 42 walk files, and a quick run of them did not finish inside the two-minute limit. That is the picker working as specified (a shared file runs everything), not a break it hid; no map or rule change was made. The plain proof catches it with its named walk.
- The first real run (at 6420bfe) ended 1 because that stopped pick counted as a failure, though the ticket says the proof ends 1 when a break is hidden. Commit 4914b5c reports a pick of everything stopped at the limit as `could not run, but nothing was picked` and does not count it against the proof; a stopped pick smaller than the whole still makes it end 1. Its test: `tests/test_prove_runs.py::test_a_pick_of_everything_stopped_at_the_limit_is_reported_so_and_does_not_fail_the_picked_proof`.
- How the copy carries what the picker needs: it is a `git clone --shared` of the repo (with the repo's branches, so the base commit and `main` are there), its files are the working folder's as on disk, and `.checks/runs.jsonl` and `.testmondata*` are copied in. A run made on a dirty folder, or after commits since the last whole green run, sees those changes too and its picks widen.
- Plain `python3 prove.py` printed and ended as before: 10 of 10 caught, ended 0, in 23 seconds.

The real `python3 prove.py --pick` at 4914b5c:

```
summary-one-day-range-refused  unit  caught  picked 12 of 776 unit tests: the tests that ran the changed Python, `webapp/api_summary.py`
summary-import-left-unused  lint  left to python3 prove.py: it is proved by a check, which runs whole
foreign-origin-write-accepted  unit  caught  picked 97 of 776 unit tests: the tests that ran the changed Python, `webapp/server.py`
second-undo-wrong-status  unit  caught  picked 2 of 776 unit tests: the tests that ran the changed Python, `webapp/api_trials.py`
walk-compares-a-value-with-itself  patterns  left to python3 prove.py: it is proved by a check, which runs whole
defect-log-line-names-a-missing-check  escapes  left to python3 prove.py: it is proved by a check, which runs whole
double-click-marks-twice  walks  caught  picked 12 of 42 walk files: The trial page, because `webapp/static/views/trial.js` changed; and the walks that always run
add-error-outlives-the-edit  walks  caught  picked 14 of 42 walk files: Find trials, because `webapp/static/views/add_by_id.js` changed; and the walks that always run
refused-page-read-as-registry-error  walks  caught  picked 14 of 42 walk files: Find trials, because `webapp/static/views/find.js` changed; and the walks that always run
sidebar-not-redrawn-after-a-review  walks  could not run, but nothing was picked (stopped after 2 minutes)  picked 42 of 42 walk files: every walk: `webapp/static/app.js` is shared
proof --pick: 6 of 7 breaks caught, 6 by a pick smaller than the whole; 1 stopped at the limit, but its pick ran everything; 3 proved by a check left to python3 prove.py
ended 0 in 260 s
```

The first real run, at 6420bfe (before 4914b5c):

```
summary-one-day-range-refused  unit  caught  picked 12 of 775 unit tests: the tests that ran the changed Python, `webapp/api_summary.py`
summary-import-left-unused  lint  left to python3 prove.py: it is proved by a check, which runs whole
foreign-origin-write-accepted  unit  caught  picked 97 of 775 unit tests: the tests that ran the changed Python, `webapp/server.py`
second-undo-wrong-status  unit  caught  picked 2 of 775 unit tests: the tests that ran the changed Python, `webapp/api_trials.py`
walk-compares-a-value-with-itself  patterns  left to python3 prove.py: it is proved by a check, which runs whole
defect-log-line-names-a-missing-check  escapes  left to python3 prove.py: it is proved by a check, which runs whole
double-click-marks-twice  walks  caught  picked 12 of 42 walk files: The trial page, because `webapp/static/views/trial.js` changed; and the walks that always run
add-error-outlives-the-edit  walks  caught  picked 14 of 42 walk files: Find trials, because `webapp/static/views/add_by_id.js` changed; and the walks that always run
refused-page-read-as-registry-error  walks  caught  picked 14 of 42 walk files: Find trials, because `webapp/static/views/find.js` changed; and the walks that always run
sidebar-not-redrawn-after-a-review  walks  could not run (stopped after 2 minutes)
    walks     picked 42 of 42 walk files: every walk: `webapp/static/app.js` is shared
proof --pick: 6 of 7 breaks caught, 6 by a pick smaller than the whole; 3 proved by a check left to python3 prove.py
ended 1 in 259 s
```

Plain `python3 prove.py` at 4914b5c:

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
proof: 10 of 10 breaks caught
ended 0 in 23 s
```
