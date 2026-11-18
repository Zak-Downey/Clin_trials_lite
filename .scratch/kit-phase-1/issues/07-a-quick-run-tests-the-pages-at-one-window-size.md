# 07: A quick run tests the pages at one window size

**What to build:** `python3 checks.py --quick` runs every check, with the walks at the first window size only (1440 x 900). Plain `python3 checks.py` is unchanged: both sizes. The quick option reaches the walks through the environment, and the walk fixtures use only the first size when it is set. The run's line in `.checks/runs.jsonl` says it was quick; a full run's line says it was not. The tests of the walk guards still run in a quick run. `--quick` can be combined with naming checks. Spec: `.scratch/kit-phase-1/spec.md`, Solution 4 and "The quick run".

**Blocked by:** 01

**Status:** done

- [x] Red first: a unit test shows a quick run tells the walks to use one window size, and a plain run does not
- [x] A quick run's line in the run log says it was quick; a plain run's line says it was not
- [x] With the quick setting, the walk fixtures give one window size, the first; without it, both
- [x] The walk-guard tests are collected and run in a quick run
- [x] `python3 checks.py` with no option behaves as before this ticket
- [x] Under Comments: the measured minutes of one full run and one quick run in this repo

## Comments

**Measured (2026-11-18, this repo, uncommitted ticket 07 work on fa23f19).** Full run `python3 checks.py`: green in 3.7 min (patterns 0.0, escapes 0.0, unit 1.1, walks 2.6). Quick run `python3 checks.py --quick`: green in 2.6 min (patterns 0.0, escapes 0.0, unit 1.2, walks 1.4; 224 walks passed). The quick run saves about 1.1 minutes a run, all of it in the walks; the unit suite is now the larger half of a quick run.

**What a quick run keeps.** The setting is `WALK_QUICK=1`, which `checks.py --quick` sets for its checks and a plain run removes, so the log's `"quick"` field (true or false on every line) cannot be wrong. The walk fixtures (`helper.window_sizes()`, used by `conftest.py`'s `viewport`) then give only 1440 x 900. The acceptance walk keeps its WebKit run in a quick run: it is at 1440 x 900, the first size, and it is the only Safari stand-in, so a quick run drops only its Chromium 1024 x 768 run. The walk-guard tests are not parametrized on the window size (one, `test_walk_second_page_shots_keep_their_own_names`, uses `viewport` and keeps its first-size run); the broken pages they run inherit the setting and are checked at the first size. `tests/test_quick_walks.py` holds all three by collecting the walk files with and without the setting. README.md does not describe how to run the checks, so only the docstring of `checks.py` changed; `repo.md` is left to ticket 09.
