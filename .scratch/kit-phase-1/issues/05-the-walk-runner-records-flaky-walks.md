# 05: The walk runner records flaky walks

**What to build:** When a walk is red with the others and green when run alone, the walk runner records its name for that run in a small file of its own, where the hand-over page can read it. A run with no such walk records that there were none, so "none" can be told from "not recorded". `checks.py` is not changed to read a suite's output: it still decides red or green by exit code and timeout alone. Whether a flaky walk makes the walk run red is one named constant in the runner, off by default, so that the owner can turn it on with one line. Spec: `.scratch/kit-phase-1/spec.md`, Solution 2 and "Flaky walks are data".

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Red first: a unit test with a fake run shows a walk that failed with the others and passed alone is recorded by name
- [ ] A run where every walk passed first time records that none was flaky
- [ ] A walk that is red alone is not recorded as flaky
- [ ] With the constant off, a run whose only failures were flaky still exits 0, as today
- [ ] With the constant on, the same run exits 1
- [ ] `checks.py` reads no suite's output: a test or the diff shows it is unchanged in that respect

## Comments
