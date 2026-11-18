# 02: The unit tests run in parallel

**What to build:** The `unit` check runs the unit suite across the processors the machine has, with `pytest-xdist`, which `requirements-dev.txt` already has for the browser tests. One test is known to fail beside others (`test_this_project_s_programs_still_listening_are_found_on_this_computer_with_their_ports_and_start_times`, which reads the machine's listening programs and finds the other workers'): make it hold in parallel without weakening what it asserts. Run the suite in parallel five times; any other test that fails only in parallel is fixed the same way, never skipped, marked or moved out of the suite. The limits in `CHECKS` do not change. `repo.md` says the unit suite runs in parallel, gives its new time, and says that a unit test must not depend on running alone or in a given order. Spec: `.scratch/kit-phase-3/spec.md`, "Unit tests in parallel" and "Limits".

**Blocked by:** 01

**Status:** done

- [x] Red first: the test that pins the checks fails until the `unit` command runs the suite in parallel
- [x] Five runs of `python3 checks.py unit` in a row are green, and the comments give their times
- [x] The comments name every test changed so that it holds in parallel, and what changed; none was skipped or weakened
- [x] `python3 checks.py` ends green on this ticket's commit

## Comments

**Red first.** `tests/test_checks.py::test_the_unit_check_runs_the_suite_across_the_processors_the_machine_has` failed (no `-n` in the `unit` command) before `checks.py` gained `-n auto`, then passed.

**Timings** (owner's Mac, 10 processors, 2026-11-18, 710 tests). One processor: 37 s. Five runs of `python3 checks.py unit` in a row, all green: 0.14, 0.20, 0.14, 0.20, 0.19 min (8 to 12 s; `.checks/runs.jsonl`). Before this build the check took 1.3 min, 0.6 after ticket 01.

**Tests changed to hold in parallel: one.**
- `tests/test_handover.py::test_this_project_s_programs_still_listening_are_found_on_this_computer_with_their_ports_and_start_times`. It held in 17 parallel runs on the Mac but failed in every parallel run on Linux (a `python:3.12-slim` container: Docker on this Mac), even run alone with `-n 2`. Cause, read from what `lsof` and `ps` returned inside the worker: Linux's `ps` cuts each piped command line at 80 columns, and an xdist worker's temporary folder (`.../popen-gw0/...`) is long enough that the stray program's file path was cut off ("/tmp/pytest-of-root/pyte"), so `handover.listeners` did not find it. A real defect of the hand-over page on Linux, not of the test alone. The test now uses a project folder with a long name and sets `COLUMNS=80`, so it no longer depends on its temporary folder's length or on the terminal; it was red on Linux run alone, then `handover.py` asks `ps -ww` (whole lines; also valid on macOS) and it passed. Its assertions are unchanged. Five parallel runs on Linux then had no failure but `test_ruff_toml_states_the_python_version_of_this_repos_venv`, which only reflects the container's Python 3.12. Defect log: E-041.
- No other test failed in parallel, on the Mac (17 runs) or on Linux (5 runs). None was skipped, marked or moved.

The thread warning in the suite's summary (`test_when_finish_run_raises_the_run_is_no_longer_running_and_a_new_check_is_accepted`) appears on one processor too; it predates this ticket.

**Whole run.** `python3 checks.py` on this commit's tree: green in 2.7 min (unit 0.1, walks 2.5).
