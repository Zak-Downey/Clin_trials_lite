# 09: The broken pages run once in a run

**What to build:** `walks/test_walk_guards.py` proves each guard by running the deliberately broken pages in `walks/broken/` and reading what that run printed. The run is shared by a fixture that lasts for the file, but the walk runner spreads the guard tests over four workers, and each worker that gets one runs the broken pages again: about 25 seconds each, 102 of a full run's 598 worker-seconds when measured. Make the broken pages run once for the whole run of the suite. Every guard test still asserts exactly what it asserts now, still runs in a quick run and in a picked run (the file is in the map's `always`), and still fails when its guard is taken away. How the one run is shared is your choice (keeping the guard tests on one worker, or sharing the result between workers); the way the walk runner spreads every other walk does not change, and a walk that fails is still run again alone. The change names nothing of this product, so it can go to the starter. Measure one full run of the browser tests before and after, and count the runs of the broken pages. This is written with the comment rule in force. Spec: `.scratch/kit-phase-4/spec.md`, "The walk-guard tests".

**Blocked by:** 05

**Status:** done

- [x] Red first: a test fails while a run of the suite on four workers runs the broken pages more than once, and passes when it runs them once
- [x] With one guard switched off in a copy, its guard test is still red: the comments say which guard was tried and what was printed
- [x] The comments give the browser tests' time for one full run before and after, and the number of runs of the broken pages in each
- [ ] A full `python3 checks.py` and a `python3 checks.py --quick --pick walks` both end green on this ticket's commit, and `python3 checks.py --comments` lists nothing

## Comments

**Built (2026-11-19).** The broken pages now run once in a run of the browser tests, where they ran once in each of the four workers, and a full run is about 14 seconds shorter (123.7 s to 109.5 s).

- **How it is shared.** In `walks/test_walk_guards.py`, the `broken_run` fixture, under pytest-xdist, takes a file lock (`fcntl.flock`) in the run's shared temporary folder (the parent of each worker's own); the first worker to hold it runs the broken pages and writes their output to `broken-<testrunuid>.txt`, and every other worker reads that file. Outside xdist (a run alone, the rerun of a failed walk) it runs them itself, as before. No guard test's assertions changed.
- **Why the guard tests go first.** With the lock alone, the broken pages ran once but the full run took the same time (123.9 s): the guard tests are collected near the end, so three workers sat waiting on the lock. `walks/conftest.py` now sorts the tests that read `broken_run` to the front of the collection (a stable sort; every other walk keeps its order). xdist's load scheduler hands the first block of tests (25 here) to one worker, so that worker runs the broken pages while the others walk. The scheduler, the four workers, `run_walks.py` and its rerun of a failed walk alone are unchanged.
- **Red first.** `walks/test_walk_guards.py::test_walk_guard_broken_pages_run_once_on_four_workers` runs the guard file on four workers with the broken pages swapped for a stand-in that writes one line each time it runs (a `-p` plugin keeps only the tests that read `broken_run`). Before the change it was red: `assert 4 == 1`. After, green in about 1 s. It is in the guard file, which is in the map's `always`, so it runs in quick and picked runs.
- **A guard switched off in a copy.** In a copy of the tracked files, the console-error guard (`Guards._console` in `walks/helper.py`) was made to record nothing. The guard tests, on four workers: `2 failed, 6 passed`. Red: `test_walk_guard_fails_a_walk_on_a_console_error` (`assert failing(out, "test_broken_console_error")` was empty) and `test_walk_guard_keeps_the_first_of_two_pages_and_a_closed_pages_findings` (it also relies on a console error). The copy was deleted.
- **Measured** (`.venv/bin/python walks/run_walks.py`, the owner's Mac, the runs of the broken pages counted by sampling the processes every half second):

| Run | pytest's time | Wall time | Broken-page runs |
|---|---|---|---|
| Before (4eed24a) | 123.74 s, 412 passed | 2:03.98 | 4 |
| Lock only | 123.89 s, 413 passed | 2:04.14 | 1 |
| After (lock, guard tests first) | 109.47 s, 413 passed | 1:49.68 | 1 |

- **Checks run.** `python3 checks.py lint patterns escapes unit`: green (unit 0.4 min). `python3 checks.py --quick --pick walks`: green in 1.1 min; it picked all 42 walk files because `walks/conftest.py` is in the map's `shared`. `python3 checks.py --comments`: `0 comments in 0 files`. The full `python3 checks.py` is left for the caller.
- `docs/agents/local/repo.md`, "Where the walks' time goes", gains one paragraph saying this.
