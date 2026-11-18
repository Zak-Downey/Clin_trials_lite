# 07: This product's breaks: one for every check, and the proof passes

**What to build:** This repo's list grows until every check is proved able to fail: at least one break each for `lint`, `patterns`, `escapes`, a unit test and a walk, and at least three proved by a walk. A break proved by a unit test or a walk changes the app's code, never a test, and is a mistake a build could plausibly make: a refusal removed, a wrong status, a field dropped, a page not redrawn after a change. The cheap test of the list (ticket 05) now also holds that every check in `CHECKS` has a break, so a sixth check cannot join without one; for `unit` and `walks`, a break whose test is under `tests/` or `walks/` is that check's break. **A break the checks miss is a finding:** if a plausible break stays green, do not delete it to make the proof pass. Write the missing test, seen red first, if it is small; otherwise leave the break out of the list and name it first in `now_what`. `docs/agents/local/repo.md` gains a line for the command: what `python3 prove.py` does, where the list is, how long it took here, that it is run by hand (after a change to a check, and before a retro) and is not part of `python3 checks.py`, and that a new check needs a break. Spec: `.scratch/kit-phase-2/spec.md`, "This product's list" and "A break the checks miss is a finding".

**Blocked by:** 03, 06

**Status:** ready-for-agent

- [ ] Red first: the test of the list fails until every check in `CHECKS` has at least one break
- [ ] `python3 prove.py` ends 0 on the whole list, with at least three breaks caught by a walk; its printed lines and its minutes are in the comments
- [ ] The comments name every break that was tried and stayed green, and what was done about each
- [ ] `repo.md` has the line for the command, and `python3 checks.py` ends green on this ticket's commit

## Comments
