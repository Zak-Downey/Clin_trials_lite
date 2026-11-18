# 07: A picked run of the unit tests

**What to build:** `pytest-testmon` joins `requirements-dev.txt`, pinned to one exact version (`pytest-testmon==2.2.0`), and is installed into this repo's `.venv`. In a picked run the `unit` check lets it select the tests that ran the code that changed, but only when every changed file (ticket 05) is a Python file: it cannot see anything else, so any other changed file outside `.scratch/` runs the whole unit suite, and so does "cannot tell". In a run that is not picked, the `unit` check runs everything and refreshes its record without deselecting (`--testmon-noselect`). Its record file is added to `.gitignore`; without a record it runs everything. It needs pytest's cache, so the `unit` command stops switching the cache off (the cache folder is already git-ignored). It keeps running in parallel as ticket 02 left it. The picked run's printed line and its log line say how many unit tests ran, out of how many, and why, as ticket 06's do for the walks. `repo.md`'s "Picked run" line covers the unit tests, including the rule about files that are not Python. Spec: `.scratch/kit-phase-3/spec.md`, "Picking unit tests".

**Blocked by:** 02, 06

**Status:** ready-for-agent

- [ ] Red first: a test fails until `requirements-dev.txt` pins `pytest-testmon` to one exact version and `.gitignore` covers its record file
- [ ] Red first, with stand-in commands: a picked run whose changed files are all Python asks for selection; one changed file that is not Python, or "cannot tell", runs the whole suite and says why; a run that is not picked deselects nothing
- [ ] In this repo, after a change to one function, `python3 checks.py --pick unit` runs fewer tests than the suite has and says how many; after a change to a script under `webapp/static/` it runs them all; the comments hold both lines and their seconds
- [ ] After any of these runs `git status` shows nothing new, and `python3 checks.py` ends green on this ticket's commit

## Comments
