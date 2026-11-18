# 07: A quick run tests the pages at one window size

**What to build:** `python3 checks.py --quick` runs every check, with the walks at the first window size only (1440 x 900). Plain `python3 checks.py` is unchanged: both sizes. The quick option reaches the walks through the environment, and the walk fixtures use only the first size when it is set. The run's line in `.checks/runs.jsonl` says it was quick; a full run's line says it was not. The tests of the walk guards still run in a quick run. `--quick` can be combined with naming checks. Spec: `.scratch/kit-phase-1/spec.md`, Solution 4 and "The quick run".

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Red first: a unit test shows a quick run tells the walks to use one window size, and a plain run does not
- [ ] A quick run's line in the run log says it was quick; a plain run's line says it was not
- [ ] With the quick setting, the walk fixtures give one window size, the first; without it, both
- [ ] The walk-guard tests are collected and run in a quick run
- [ ] `python3 checks.py` with no option behaves as before this ticket
- [ ] Under Comments: the measured minutes of one full run and one quick run in this repo

## Comments
