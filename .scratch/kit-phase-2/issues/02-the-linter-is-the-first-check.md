# 02: The linter is the first check

**What to build:** `python3 checks.py` runs a check named `lint` before the others: Ruff over the repo, with a limit of 1 minute and its output in `.checks/lint.txt`. It leaves no cache folder or other file behind. Red is still a non-zero exit code or a timeout, and nothing reads Ruff's output to decide. The test that pins the names and limits of the checks pins the new one. The docstring at the top of `checks.py` says what the check is. `python3 checks.py lint` and `python3 checks.py --quick` work as they do for any other check. Spec: `.scratch/kit-phase-2/spec.md`, "The check".

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Red first: the test that pins the checks fails until `lint` is first, with a limit of 1 minute, ahead of `patterns`, `escapes`, `unit` and `walks` unchanged
- [ ] Red first: in a copy of a small repo, a Python file with an unused import turns `lint` red and the run stops there; without it the check is green
- [ ] After `python3 checks.py lint`, `git status` shows nothing new, and the run's line in `.checks/runs.jsonl` lists `lint` like any other check
- [ ] `python3 checks.py` ends green in this repo, and the comments give the minutes the linter took

## Comments
