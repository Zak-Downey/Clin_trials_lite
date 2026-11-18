# 01: The test server stops at once

**What to build:** The in-process server that the unit suite's `api` fixture starts (`tests/conftest.py`) takes up to half a second to stop, because it is started with the standard half-second wait between looks for a stop request. Measured on a copy: 97 of the suite's teardowns took half a second, 49 of its 86 seconds. Start it so that stopping takes a few hundredths of a second. A unit test holds it: a server started and stopped the way the fixture does it is done in under 0.2 seconds. Nothing else about the fixture changes, and no test's assertions change. `docs/agents/local/repo.md` gives the unit suite's new time. Spec: `.scratch/kit-phase-3/spec.md`, "The test server".

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Red first: the new test fails while the server is started as it is today, and passes after
- [ ] The comments give the unit suite's time before and after, from two runs of `python3 checks.py unit` on this machine
- [ ] No other line of the fixture and no assertion of any test changed
- [ ] `python3 checks.py` ends green on this ticket's commit

## Comments
