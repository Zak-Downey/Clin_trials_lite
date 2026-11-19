# 09: The broken pages run once in a run

**What to build:** `walks/test_walk_guards.py` proves each guard by running the deliberately broken pages in `walks/broken/` and reading what that run printed. The run is shared by a fixture that lasts for the file, but the walk runner spreads the guard tests over four workers, and each worker that gets one runs the broken pages again: about 25 seconds each, 102 of a full run's 598 worker-seconds when measured. Make the broken pages run once for the whole run of the suite. Every guard test still asserts exactly what it asserts now, still runs in a quick run and in a picked run (the file is in the map's `always`), and still fails when its guard is taken away. How the one run is shared is your choice (keeping the guard tests on one worker, or sharing the result between workers); the way the walk runner spreads every other walk does not change, and a walk that fails is still run again alone. The change names nothing of this product, so it can go to the starter. Measure one full run of the browser tests before and after, and count the runs of the broken pages. This is written with the comment rule in force. Spec: `.scratch/kit-phase-4/spec.md`, "The walk-guard tests".

**Blocked by:** 05

**Status:** ready-for-agent

- [ ] Red first: a test fails while a run of the suite on four workers runs the broken pages more than once, and passes when it runs them once
- [ ] With one guard switched off in a copy, its guard test is still red: the comments say which guard was tried and what was printed
- [ ] The comments give the browser tests' time for one full run before and after, and the number of runs of the broken pages in each
- [ ] A full `python3 checks.py` and a `python3 checks.py --quick --pick walks` both end green on this ticket's commit, and `python3 checks.py --comments` lists nothing

## Comments
