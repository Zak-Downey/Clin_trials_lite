# 02: The linter is the first check

**What to build:** `python3 checks.py` runs a check named `lint` before the others: Ruff over the repo, with a limit of 1 minute and its output in `.checks/lint.txt`. It leaves no cache folder or other file behind. Red is still a non-zero exit code or a timeout, and nothing reads Ruff's output to decide. The test that pins the names and limits of the checks pins the new one. The docstring at the top of `checks.py` says what the check is. `python3 checks.py lint` and `python3 checks.py --quick` work as they do for any other check. Spec: `.scratch/kit-phase-2/spec.md`, "The check".

**Blocked by:** 01

**Status:** done

- [x] Red first: the test that pins the checks fails until `lint` is first, with a limit of 1 minute, ahead of `patterns`, `escapes`, `unit` and `walks` unchanged
- [x] Red first: in a copy of a small repo, a Python file with an unused import turns `lint` red and the run stops there; without it the check is green
- [x] After `python3 checks.py lint`, `git status` shows nothing new, and the run's line in `.checks/runs.jsonl` lists `lint` like any other check
- [x] `python3 checks.py` ends green in this repo, and the comments give the minutes the linter took

## Comments

The linter now runs first in every `python3 checks.py`, and the full run on this ticket's code was green in 3.8 minutes (lint 0.0, patterns 0.0, escapes 0.0, unit 1.18, walks 2.62). I ran it on the working tree before committing.

- **Minutes the linter took:** under 0.01 minutes. The run log rounds it to 0.0; Ruff alone over the repo took 0.04 seconds (`time`, real).
- **The check:** `("lint", [PYTHON, "-m", "ruff", "check", "--no-cache", "."], 1)`, first in `CHECKS`. Red is still exit code or timeout only. The docstring of `checks.py` says what it is.
- **Tests, each seen red first:** `tests/test_checks.py::test_every_check_this_repo_lists_has_a_name_a_command_and_a_time_limit` (pins `lint` first with 1 minute); `test_the_lint_check_is_red_on_an_unused_import_and_the_run_stops_there` and `test_the_lint_check_is_green_on_clean_code_and_leaves_no_file_behind` (red without the check; the second also went red when `--no-cache` was taken out, because Ruff then leaves `.ruff_cache`).
- **No file left behind:** `git status --short --ignored` was the same before and after `python3 checks.py lint`, and the run's line in `.checks/runs.jsonl` lists `lint` like the others. `--quick lint` works the same way.
- **Part of ticket 03 done here, because a test forced it.** `handover.py` reads its list of checks from `CHECKS`, so adding `lint` turned 10 hand-over tests red, among them the existing test that every check has words for the owner. I gave `lint` the words "the read of the code for common mistakes" in `CHECK_GLOSS`, and updated the hand-over tests that quote the list of checks to the five. Left for 03: `repo.md`, the test holding its "Every check" line to `CHECKS`, and a dedicated red-first test that a page names `lint` in the owner's words (the existing gloss test covered it here).
- **A stale `.ruff_cache`** was in the repo root, dated 20:32, before this check first ran (20:37); some earlier Ruff run without `--no-cache` left it. I deleted it, ran `python3 checks.py lint` again, and none came back. Ruff writes a `.gitignore` inside that folder, so `git status` alone does not show one.
