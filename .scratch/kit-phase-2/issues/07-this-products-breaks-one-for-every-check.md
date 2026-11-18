# 07: This product's breaks: one for every check, and the proof passes

**What to build:** This repo's list grows until every check is proved able to fail: at least one break each for `lint`, `patterns`, `escapes`, a unit test and a walk, and at least three proved by a walk. A break proved by a unit test or a walk changes the app's code, never a test, and is a mistake a build could plausibly make: a refusal removed, a wrong status, a field dropped, a page not redrawn after a change. The cheap test of the list (ticket 05) now also holds that every check in `CHECKS` has a break, so a sixth check cannot join without one; for `unit` and `walks`, a break whose test is under `tests/` or `walks/` is that check's break. **A break the checks miss is a finding:** if a plausible break stays green, do not delete it to make the proof pass. Write the missing test, seen red first, if it is small; otherwise leave the break out of the list and name it first in `now_what`. `docs/agents/local/repo.md` gains a line for the command: what `python3 prove.py` does, where the list is, how long it took here, that it is run by hand (after a change to a check, and before a retro) and is not part of `python3 checks.py`, and that a new check needs a break. Spec: `.scratch/kit-phase-2/spec.md`, "This product's list" and "A break the checks miss is a finding".

**Blocked by:** 03, 06

**Status:** done

- [x] Red first: the test of the list fails until every check in `CHECKS` has at least one break
- [x] `python3 prove.py` ends 0 on the whole list, with at least three breaks caught by a walk; its printed lines and its minutes are in the comments
- [x] The comments name every break that was tried and stayed green, and what was done about each
- [x] `repo.md` has the line for the command, and `python3 checks.py` ends green on this ticket's commit

## Comments

The proof caught all ten breaks: `python3 prove.py` ended 0 on the whole list in 0.43 minutes (about 26 seconds, 2026-11-18, on the uncommitted work over 09dc704). Every check now has a break: `lint` 1, `patterns` 1, `escapes` 1, the unit suite 3, the walks 4. The four walk breaks each run one walk, not the whole `walks` check, so that each run stays under the two-minute limit.

### Breaks the checks missed

None. Every break that was tried was caught on the first run, and none was left out of the list.

### What was added

- Red first: `tests/test_prove.py::test_every_check_in_checks_py_has_a_break_in_this_repos_list` failed with "no break proves these checks can fail: patterns, escapes, walks" before the list grew.
- Unit: `foreign-origin-write-accepted` (the server's refusal of a write from another site's page is removed) and `second-undo-wrong-status` (a second undo of a review answers 404 instead of 409).
- Patterns: `walk-compares-a-value-with-itself` reintroduces E-026 in `walks/test_summary_walk.py`. The only forbidden pattern (R-005) looks at `walks/` and `tests/` only, so this break changes a walk, not the app's code; no app-code text can match a pattern today.
- Escapes: `defect-log-line-names-a-missing-check` points E-038's `check` at a walk file that does not exist.
- Walks: `double-click-marks-twice` (E-033 guard removed), `add-error-outlives-the-edit` (E-035), `refused-page-read-as-registry-error` (E-036) and `sidebar-not-redrawn-after-a-review` (the sidebar's redraw after a review change removed).
- `docs/agents/local/repo.md` gained the line for `python3 prove.py`.

### The run's printed lines

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
exit 0 minutes .43
```
