# 07: A picked run of the unit tests

**What to build:** `pytest-testmon` joins `requirements-dev.txt`, pinned to one exact version (`pytest-testmon==2.2.0`), and is installed into this repo's `.venv`. In a picked run the `unit` check lets it select the tests that ran the code that changed, but only when every changed file (ticket 05) is a Python file: it cannot see anything else, so any other changed file outside `.scratch/` runs the whole unit suite, and so does "cannot tell". In a run that is not picked, the `unit` check runs everything and refreshes its record without deselecting (`--testmon-noselect`). Its record file is added to `.gitignore`; without a record it runs everything. It needs pytest's cache, so the `unit` command stops switching the cache off (the cache folder is already git-ignored). It keeps running in parallel as ticket 02 left it. The picked run's printed line and its log line say how many unit tests ran, out of how many, and why, as ticket 06's do for the walks. `repo.md`'s "Picked run" line covers the unit tests, including the rule about files that are not Python. Spec: `.scratch/kit-phase-3/spec.md`, "Picking unit tests".

**Blocked by:** 02, 06

**Status:** done

- [x] Red first: a test fails until `requirements-dev.txt` pins `pytest-testmon` to one exact version and `.gitignore` covers its record file
- [x] Red first, with stand-in commands: a picked run whose changed files are all Python asks for selection; one changed file that is not Python, or "cannot tell", runs the whole suite and says why; a run that is not picked deselects nothing
- [x] In this repo, after a change to one function, `python3 checks.py --pick unit` runs fewer tests than the suite has and says how many; after a change to a script under `webapp/static/` it runs them all; the comments hold both lines and their seconds
- [x] After any of these runs `git status` shows nothing new, and `python3 checks.py` ends green on this ticket's commit

## Comments

**2026-11-19, the implementer.** Built in 69820d9, 750575a and d43fc44; `pytest-testmon==2.2.0` is installed in `.venv`.

What a picked run gives the unit check: `--testmon` when every changed file outside `.scratch/` is Python (it selects), else `--testmon-noselect` (the whole suite); a run that is not picked always gets `--testmon-noselect`. The rule is `picker.unit`; `checks.py` adds the flag and no longer passes `-p no:cacheprovider`. `.testmondata*` is git-ignored.

Found while measuring: run across processors, pytest's summary line leaves out the tests the picker deselected ("97 passed", no "670 deselected"), so the first real run said "97 of 97". A selecting run now counts the suite first by collecting it without running (`--collect-only --no-testmon`, about 0.2 s), and the stand-in in `tests/test_checks.py` prints no deselected count, as pytest-xdist does. A second fault: the unit command already has `-q`, and a second `-q` made the collection print a count per file and no total ("97 of ?"), fixed in d43fc44.

Real runs, on the owner's Mac, measured from base d43fc44 (a green run of every check on a clean folder at that commit), each throwaway change undone with `git checkout -- <file>` and `git status` empty afterwards:

- A change to one function (`diff.high_signal`): `unit      picked 97 of 767 unit tests: the tests that ran the changed Python, `diff.py``, green in 0.03 min (1.7 s for the whole command).
- A change to a script (`webapp/static/focus.js`): `unit      picked 767 of 767 unit tests: the whole suite: `webapp/static/focus.js` is not Python, which the record of what each test ran cannot see`, green in 0.18 min (10.6 s for the whole command).

Whole runs of `python3 checks.py`, green: 69820d9 (2.7 min), 750575a (2.8 min), d43fc44 (2.8 min: unit 0.2, walks 2.6), and this record's commit (below).
