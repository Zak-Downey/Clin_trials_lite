# 08: The stand-in registry stops at once

**What to build:** The browser tests' stand-in for the outside registry (`Registry` in `walks/helper.py`) is started on a thread with the standard half-second wait between looks for a stop request, so each walk that used it waits up to half a second while it shuts: 0.29 seconds a walk when measured, about 27 of a full run's 152 seconds. Start it so that stopping takes a few hundredths of a second, as `kit-phase-3` did for the unit suite's server (`serve_in_background` in `tests/conftest.py`). A test holds it: a stand-in started and stopped the way the helper does it is done in under 0.2 seconds. Nothing else about the stand-in or the helper changes, and no walk's assertions change. Measure one full run of the browser tests before and after. This is written with the comment rule in force: the checks are red on a comment. Spec: `.scratch/kit-phase-4/spec.md`, "The stand-in registry".

**Blocked by:** 05

**Status:** done

- [x] Red first: the new test fails while the stand-in is started as it is today, and passes after
- [x] The comments give the browser tests' time for one full run before and after, on this machine
- [x] No walk's assertions changed, and `python3 checks.py --comments` still lists nothing
- [ ] A full `python3 checks.py`, not quick and not picked, ends green on this ticket's commit

## Comments

- **The stand-in now stops in about 0.02 s.** `Registry` in `walks/helper.py` starts its thread with `poll_interval=0.01`, as `serve_in_background` in `tests/conftest.py` does for the unit suite's server. Nothing else in the helper changed, and no walk changed.
- **Test:** `tests/test_walk_registry.py::test_a_stand_in_registry_started_and_stopped_by_the_helper_is_done_in_under_a_fifth_of_a_second`. Seen red before the change on three runs (about 0.50 s: `assert (366413.87723 - 366413.373508958) < 0.2`), green after on three runs (0.02 s each).
- **Browser tests, one full run each, on this machine (`.venv/bin/python walks/run_walks.py`):** before the change 412 passed in 156.57 s (wall 156.81 s); after it 412 passed in 126.67 s (wall 126.87 s), about 30 s shorter. The after run overlapped for its first ~20 s with `python3 checks.py lint patterns escapes unit`, so if anything it is a little slow.
- `python3 checks.py lint patterns escapes unit` is green; `python3 checks.py --comments` prints "0 comments in 0 files".
