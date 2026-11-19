# 01: The test server stops at once

**What to build:** The in-process server that the unit suite's `api` fixture starts (`tests/conftest.py`) takes up to half a second to stop, because it is started with the standard half-second wait between looks for a stop request. Measured on a copy: 97 of the suite's teardowns took half a second, 49 of its 86 seconds. Start it so that stopping takes a few hundredths of a second. A unit test holds it: a server started and stopped the way the fixture does it is done in under 0.2 seconds. Nothing else about the fixture changes, and no test's assertions change. `docs/agents/local/repo.md` gives the unit suite's new time. Spec: `.scratch/kit-phase-3/spec.md`, "The test server".

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Red first: the new test fails while the server is started as it is today, and passes after
- [x] The comments give the unit suite's time before and after, from two runs of `python3 checks.py unit` on this machine
- [x] No other line of the fixture and no assertion of any test changed
- [x] `python3 checks.py` ends green on this ticket's commit

## Comments

- Unit suite time, from `python3 checks.py unit` on this machine (2026-11-18), two runs each: before the fix 78.7 s and 79.9 s (1.31 and 1.33 min); after it 34.7 s and 33.5 s (0.6 min both).
- Red first: `tests/test_api_fixture.py` failed three runs of three with the server started as today (stopping took about half a second), and passed after `serve_in_background` in `tests/conftest.py` gave `serve_forever` a poll interval of 0.01 s. The fixture's two lines that started the thread became one call to that helper, and its now-unused `import threading` went (Ruff flags it); no other fixture line and no assertion changed.
