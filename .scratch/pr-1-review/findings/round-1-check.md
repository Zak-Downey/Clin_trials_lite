# Round 1 check: scoped re-check of ticket 18

Diff read: `git diff 0312f9b..a7a2d4e -- . ':!.scratch'` (two files: `webapp/api_checks.py`, `tests/test_api_checks.py`). I checked it against round 1 findings 1 and 2. Finding 3 is Open list item 21 and is not re-read here. Per-ticket reviews: none for ticket 18 (`reviews/` holds only 01, 01-foundation and 01-followup).

Runs made here, output outside the worktree:
- Unit suite at a7a2d4e: 472 passed (`/tmp/r1check/unit.txt`).
- Red evidence read: `.scratch/pr-1-review/red/18-unit-0312f9b.txt`. Both new tests fail at 0312f9b for the reason the findings give: `('complete', 2, 3)`, and `last_checked` moved.
- One probe against the `api` fixture, kept in `/tmp/r1check/` (nothing added to `tests/`). Output: `/tmp/r1check/probe.txt`.

Counts: blocking 0 · sweep 1 · design 0 · nit 0.

## Did each fix land

| Round 1 | Fix | Landed | How I know |
|---|---|---|---|
| 1. "2 of 3 checked" after a removal mid-run | `Run.skipped` is counted on both skip paths (`api_checks.py:75,89`), and `total` is `len(trial_steps) - run.skipped` (`api_checks.py:171`) | yes | The test fails at 0312f9b and passes at the tip. Read: `processed` and `checked` come from `results`, which a skipped step never joins, so the running line "N of total" stays consistent too. `steps`/`steps_done` (the progress bar) still count the skipped step. They advance together, so the bar still ends full. |
| 2. Trial removed during its own fetch still marked checked and given changes | `held_fetch` re-reads `is_member` once `_unlocked` has retaken the lock and raises `_Removed` (a `BaseException`); `_work` catches it, counts a skip and moves on (`api_checks.py:80-91`) | yes, for a fetch that succeeds | The test fails at 0312f9b and passes at the tip. Read: `monitor.check` (`monitor.py:874-880`) only reads before `_fetch_record`, so raising there leaves no half-written state. `_fetch_record`'s `except Exception` (`monitor.py:71`) and `check_one`'s `except MonitorError` do not catch a `BaseException`, so `_Removed` reaches `_work` intact. The re-read and the writes after it run under the same lock hold, so no window is left between them. |

## Sweep

### 1. A trial removed during its own fetch, when that fetch fails, still shows as a failure and gets a failure stamp

- **What happens.** `held_fetch` re-reads membership only after `fetch` returns. When the fetch raises (unreachable, 404, a server error), the exception goes past the re-read: `_fetch_record` turns it into `MonitorError`, and `check_one` records `mark_check_failed` for the trial (`monitor.py:951-952`; `remove_member` keeps the trial row, `storage.py:328-338`) and returns an error result. The finished panel reads "Check incomplete / 2 of 3 trials checked · 1 trial could not be checked" and "Previous data for the failed trials are retained.", but offers no Retry, because `failed_in_last_run` filters to trials the list still holds. `finish_run` also writes the removed trial into the run's `failed` list. This is the same window as round 1 finding 2. It is closed for the success path only.
- **Who.** An analyst who removes a trial while its own fetch is in flight, at a moment the registry fails for that trial. The panel says the check is incomplete over a trial they just removed, and gives them no action.
- **How I know.** Reproduced at the API: `/tmp/r1check/test_probe_failed_fetch_removed.py` removes NCT00000003 inside its own fetch, then raises `URLError`. Result: `{'state': 'incomplete', 'checked': 2, 'total': 3, 'processed': 3, 'failed': 1, 'retryable': 0}`, and the trial's `check_failed_at` is set (`/tmp/r1check/probe.txt`). I did not walk how the page draws it. I inferred it from `check.js` `drawDone` (lines 88-94).
- **Where.** `webapp/api_checks.py:80-84`: the membership re-read is not in a `finally`, or around the fetch's exception path.
- **Fix shape.** Re-read membership whether or not the fetch raised. For example: `try: record = fetch(n)` then `finally: if not is_member(...): raise _Removed(nct)`. A `_Removed` raised from `finally` replaces the fetch's exception.
- **Class.** Sweep. It needs two rare events at once: a removal inside one registry call, and that call failing. Nothing is lost, and the stray failure stamp is cleared by the trial's next successful check if it is re-added. It is new only in the sense that ticket 18 drew the line at the success path. Round 1 finding 2 named only the success path.

## Nothing new blocks

The diff is limited to the run's own counting and the trial step. `find_new` (round 1 nit 5) is untouched and stays as logged. `_Removed` is defined and caught in `_work` only. No other caller of `check_one` passes `held_fetch`.

## Not read

- The walks: I ran none. The check walk (`walks/test_check_walk.py`) was not re-run at this tip, and the panel text above is read from `check.js`, not seen.
- Round 1 finding 3 / Open item 21 (Undo guard): the diff does not touch it.
- Anything outside the two changed files, beyond `monitor.check`, `check_one`, `_fetch_record`, `storage.remove_member`/`is_member` and `check.js` `drawRunning`/`drawDone`.
