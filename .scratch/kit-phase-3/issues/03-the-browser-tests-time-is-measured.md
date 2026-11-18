# 03: The browser tests' time is measured

**What to build:** Nobody knows where the browser tests' time goes: a full run is about 410 walk runs in about two and a half minutes on four workers. Measure one full run of the walks on this machine and record the time of each walk file (its tests summed, set-up and tear-down included), the ten slowest single walks, and how the total splits between set-up, the walk itself and tear-down. The figures go in this ticket's comments, and a short table (the ten slowest files, and the split) goes in `docs/agents/local/repo.md` with the date. Nothing about how the walks run changes in this ticket. If the measurement shows a cheap fix, as ticket 01's did for the unit suite, name it first in `now_what` with the seconds it would save; do not make it here. Spec: `.scratch/kit-phase-3/spec.md`, "The browser tests are measured, not changed".

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] The comments hold the time of every walk file from one full run, the ten slowest walks, and the split between set-up, walk and tear-down
- [ ] `repo.md` has the short table, dated
- [ ] No file under `walks/` changed
- [ ] `python3 checks.py` ends green on this ticket's commit

## Comments
