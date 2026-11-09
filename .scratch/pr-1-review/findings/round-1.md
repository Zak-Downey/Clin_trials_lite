# Round 1: scoped re-read of the pr-1-review fixes

Diff read: `git diff 5c258ce..feature/pr-1-review -- . ':!.scratch'` (tip 73b36b5, fix tickets 01-17). Against `ranked.md` blocking rows 1-17 (F1-F17) and the fix spec's Open list. Per-ticket reviews read: `reviews/01.md`, `01-foundation.md`, `01-followup.md`. Already logged and not repeated: the `check.js` `onChange` overtaken-re-read guard has no walk (build log, ticket 13 observation).

Runs made here, output outside the worktree:
- Unit suite: 470 passed (`/tmp/r1-unit.txt`).
- Walks the fixes touch (late answer, origin, check, summary, new matches, find trials, saved search): 116 passed, 3 workers (`/tmp/r1-walks.txt`). Not the whole walk suite.
- Probes against the `api` fixture, written in `/tmp/r1probe/` (nothing added to `tests/`): outputs `/tmp/r1-probe3.txt`, `/tmp/r1-probe4.txt`.

Counts: blocking 1 · sweep 2 · design 0 · nit 3.

## Did each blocking fix land

| F | Fix | Landed | How I know |
|---|---|---|---|
| F1 | Alone re-run passes only the node id | yes | `walks/run_walks.py:30-38,88-90`: targets are `(nodeid,)`, options carried. Follow-up review's two surviving mutants were closed with red runs (`red/01-walks-9255def-*.txt`). Read, not re-run. |
| F2 | `_latest` takes the max `detected` | yes | `webapp/api_summary.py:52`; test with a high-signal field in the older check, red at 37ea56c. Unit suite green. |
| F3 | Refresh reads the period from the address; Summary and New matches keep state per watchlist | yes | `app.js:180` reads `location.hash` at draw time; `summary.js:64-79`, `new_matches.js:16-24` module maps. `test_walk_a_finished_check_keeps_summary_period_and_typed_dates` and the New matches walks ran green here. |
| F4 | Every render takes `alive` | yes, for the four named | `app.js:137-205`; `trial.js:16`, `needs_review.js:15,28`, `all_trials.js:24`, `summary.js:75`. New matches still takes none, but it draws into `#queue`, which a new route detaches, so a late answer lands off-page. Its refresh path is guarded (`app.js:198`). |
| F5 | Sidebar keeps its mark on `reviewchange` | yes | `app.js:92` passes `undefined`; `drawSidebar` reads the id from the address (`app.js:45-48`). |
| F6 | Failed poll is stated and frees the button; `el` takes children | yes | `check.js:130-165` (`unreadable` calls `setBusy(false)`); `app.js:20-25`. |
| F7 | Header re-read on `reviewchange` | yes | `check.js:201-211`. Its overtaken guard has no walk (logged). |
| F8 | Details preset to the originating watchlist; Back returns there | yes | `registry_trial.js:13-26`; origin set by `find.js:206` and `new_matches.js:20`; ticket 13 guards the late-refresh case. `test_origin_walk.py` green here. |
| F9 | A failed add is an error beside the control, ID kept | yes | `add_by_id.js:43,51`; `registry_trial.js:35-50`. |
| F10 | Lead sponsor type is a checkbox group | yes | `find.js:86-90,126`; `test_saved_search_walk.py` green here. |
| F11 | Refusals carry their kind; the page shows them beside the fields with no Retry | yes | `monitor.py:458,467`; `api_search.py:30`, `api_saved_search.py:57` pass `err.kind`; `find.js:312-314`. `as_query` cannot raise, so no refusal falls through as kind `error`. |
| F12 | `add_trials` re-reads the watchlist after the fetch | yes | `api_membership.py:52-53`; test red at 37ea56c. |
| F13 | `_work` re-reads membership before each step; inner `finally` | landed as the spec wrote it, with a gap (finding 2) and a new miscount (finding 1) | `api_checks.py:66-71,81-88`; probes below. |
| F14 | CSV starts with U+FEFF | yes | `briefing.py:349`; unit test reads with `utf-8-sig`. No walk checks the downloaded bytes (see Not read). |
| F15 | Summary walk asserts the count, seeds inside the period | yes | `walks/test_summary_walk.py:22,40-49,82,90`. |
| F16 | Acceptance walk measures on every keyboard move | yes | `walks/test_acceptance_walk.py:95,103-113,134-147`; its own failing-case walk at line 441. |
| F17 | Every stop passed is checked | yes | `walks/test_acceptance_walk.py:96-97,115-121`; failing-case walk at line 456. |

## Blocking

### 1. A finished check reads "2 of 3 checked" after a trial was removed while the check ran

- **What happens.** Ticket 07 now skips a trial removed from the watchlist mid-run (`webapp/api_checks.py:69-71`). The run's state still counts it in `total` (`api_checks.py:153`, `len(trial_steps)`), so the panel reads "Check complete · No new changes detected / 2 of 3 checked at …" (`check.js` `drawDone`, `${state.checked} of ${state.total} checked`). The check is complete and nothing failed, but the line says one trial was not checked and gives no reason. The header above it says 2 trials monitored.
- **Who.** An analyst who removes a trial (trial page menu, or Remove from this list) while a check of that watchlist runs.
- **How I know.** Reproduced at the API: probe `/tmp/r1probe/test_probe_removed_during_fetch.py` removes NCT00000003 during NCT00000001's fetch. The finished state is `{'state': 'complete', 'checked': 2, 'total': 3, 'processed': 2}` (`/tmp/r1-probe4.txt`). Inferred that the page draws it as above (read from `check.js`, not walked).
- **Where it was made.** `api_checks._work`/`_state`: a skipped step is neither a result nor dropped from the total.
- **Status.** fixed — test: test_a_finished_check_counts_only_the_trials_it_still_held_after_one_was_removed — red: .scratch/pr-1-review/red/18-unit-0312f9b.txt
- **Class.** Blocking: it is new in this diff (the F13 fix), and it is a count the analyst reads on the check panel. It happens only on a rare ordering; the merger may downgrade it.

## Sweep

### 2. A trial removed during its own fetch is still marked checked and given changes (F13 narrowed, not closed)

- **What happens.** The membership re-read runs before the step (`api_checks.py:69`). `monitor.check_one` then fetches with the lock released (`_unlocked`, `api_checks.py:46-55`) and writes after the fetch with no second look (`monitor.py` `check`: `add_change`, `add_snapshot`, `mark_checked`). A removal that lands during that trial's own fetch gives an unmonitored trial a change row and a new `last_checked`. The spec's "skipped by every check" still fails, though only inside one fetch's window rather than the whole run. R-003's proposed line ("a write after a registry call made outside the lock re-reads the rows it writes to") is the rule this misses.
- **How I know.** Reproduced: the same probe, removing NCT00000003 during its own fetch with the registry stamp bumped, gives `members 0 … changes 1`, with `last_checked` moved from 2026-11-01 to now (`/tmp/r1-probe3.txt`).
- **Why the ticket's test passes.** `test_a_trial_removed_while_a_check_runs_is_not_fetched_marked_checked_or_given_changes` (`tests/test_api_checks.py:243`) removes the trial during a different trial's fetch, so it never exercises this window.
- **Status.** fixed — test: test_a_trial_removed_during_its_own_fetch_is_not_marked_checked_or_given_changes — red: .scratch/pr-1-review/red/18-unit-0312f9b.txt
- **Class.** Sweep: the window is one registry call, and the fix is a membership re-read after the fetch inside the trial step (for example a fetch wrapper that raises a "no longer held" sentinel once the lock is retaken). Nothing the analyst sees changes except the absence of a stray change.

### 3. Undo after Mark reviewed has no in-flight guard, so a double click shows "That review was already undone."

- **What happens.** Ticket 15 guards Mark reviewed (`webapp/static/views/trial.js:156-158`). The Undo it creates (`trial.js:166-175`) sends `POST /api/reviews/<id>/undo` on every click. The second request answers 409 `already_undone` (`webapp/api_trials.py:135`), and `fail(err)` shows that sentence while the undo did succeed. This is the same class as E-033, on the next button in the same bar.
- **How I know.** Inferred from the code and the endpoint. Not walked.
- **Class.** Sweep: a one-line guard of the same shape as ticket 15's.

## Nit

### 4. The ticket 07 test's "no change rows" assertion cannot fail as written

`tests/test_api_checks.py:248-260` revises `overallStatus` without bumping `lastUpdatePostDateStruct`. The check therefore records no change for any trial, removed or not: in my probe with the same revision, NCT00000001, which stayed in the list, also got 0 changes. The test's `"NCT00000003" not in asked` assertion still covers the box's claim, so nothing goes unproved. The changes clause is decoration. Reproduced (first probe run, `other 0`).

### 5. A watchlist deleted during its check's saved-search step still gets offers written

`monitor.find_new` (`monitor.py:675-697`) writes `set_search_capped` and `add_found` for `list_id` after the search fetch, with no re-read. `_work`'s list check (`api_checks.py:67`) runs only before the step. The rows are orphans, and `lists.id` is `AUTOINCREMENT` (`storage.py:45`), so no later watchlist inherits them. Inferred.

### 6. New matches' pending "Yes, dismiss N" and ticks, and Summary's open Custom dates form, outlive leaving the tab

The per-watchlist maps (`new_matches.js:16-24`, `summary.js:64-79`) are never cleared on navigation. An analyst who ticks matches, presses Dismiss, goes to Needs review and comes back finds the confirmation still offered. Open item 1 accepted "kept per watchlist", and All trials' filter already lives this long. The lifetime beyond a refresh was not stated, and a destructive confirmation shown again unasked is the one case that may be worth narrowing. Inferred from the code.

## Not read

- The whole walk suite (I ran the seven walk files listed above, not `run_walks.py` over everything), and the WebKit run.
- `walks/run_walks.py` was not re-run against a real failing walk. I relied on the follow-up review's red runs.
- Docs and ledger diffs (`README.md`, `repo.md`, `ledger.md`, `escapes.jsonl`, `requirements-dev.txt`): read the stat only.
- The exploration walks added by ticket 11, beyond checking that they no longer carry `todo`. One still has an unused `import pytest`.
- `walks/test_walk_guards.py`, `walks/test_run_walks.py` and `walks/test_late_answer_walk.py` bodies: run green, not read line by line.
- That a downloaded CSV starts with the BOM bytes. The walks decode the file as `utf-8`, so they accept it with or without the mark; only the unit test pins it.
- Excel, Safari, a screen reader.
