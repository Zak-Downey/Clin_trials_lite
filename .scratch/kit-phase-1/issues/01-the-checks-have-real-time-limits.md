# 01: The checks have real time limits

**What to build:** The unit tests are stopped and called red after 3 minutes and the walks after 8, where today they have 10 and 20. `patterns` and `escapes` keep 1 minute. The test that pins the list of checks pins these numbers too, so changing one is deliberate. `docs/agents/local/repo.md`, and `CLAUDE.md` if it says, agree with the new limits wherever they tell an agent how long to wait for `python3 checks.py`; `repo.md` also says the limits are a product's own and should be about three times a normal run, so a product that grows raises them on purpose. The same line in the skill file is ticket 10's. Spec: `.scratch/kit-phase-1/spec.md`, Solution 3.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Red first: the test that pins the checks fails until `unit` has 3 minutes and `walks` has 8, with `patterns` and `escapes` at 1
- [ ] `python3 checks.py` still ends green in this repo under the new limits
- [ ] `repo.md` states the new limits, the time to allow for a whole run, and that a product sets its own at about three times a normal run
- [ ] No sentence outside `.claude/` still gives the old limits or the old waiting time

## Comments
