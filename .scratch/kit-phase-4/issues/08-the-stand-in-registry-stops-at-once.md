# 08: The stand-in registry stops at once

**What to build:** The browser tests' stand-in for the outside registry (`Registry` in `walks/helper.py`) is started on a thread with the standard half-second wait between looks for a stop request, so each walk that used it waits up to half a second while it shuts: 0.29 seconds a walk when measured, about 27 of a full run's 152 seconds. Start it so that stopping takes a few hundredths of a second, as `kit-phase-3` did for the unit suite's server (`serve_in_background` in `tests/conftest.py`). A test holds it: a stand-in started and stopped the way the helper does it is done in under 0.2 seconds. Nothing else about the stand-in or the helper changes, and no walk's assertions change. Measure one full run of the browser tests before and after. This is written with the comment rule in force: the checks are red on a comment. Spec: `.scratch/kit-phase-4/spec.md`, "The stand-in registry".

**Blocked by:** 05

**Status:** ready-for-agent

- [ ] Red first: the new test fails while the stand-in is started as it is today, and passes after
- [ ] The comments give the browser tests' time for one full run before and after, on this machine
- [ ] No walk's assertions changed, and `python3 checks.py --comments` still lists nothing
- [ ] A full `python3 checks.py`, not quick and not picked, ends green on this ticket's commit

## Comments
