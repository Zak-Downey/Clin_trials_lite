# 02: The unit tests run in parallel

**What to build:** The `unit` check runs the unit suite across the processors the machine has, with `pytest-xdist`, which `requirements-dev.txt` already has for the browser tests. One test is known to fail beside others (`test_this_project_s_programs_still_listening_are_found_on_this_computer_with_their_ports_and_start_times`, which reads the machine's listening programs and finds the other workers'): make it hold in parallel without weakening what it asserts. Run the suite in parallel five times; any other test that fails only in parallel is fixed the same way, never skipped, marked or moved out of the suite. The limits in `CHECKS` do not change. `repo.md` says the unit suite runs in parallel, gives its new time, and says that a unit test must not depend on running alone or in a given order. Spec: `.scratch/kit-phase-3/spec.md`, "Unit tests in parallel" and "Limits".

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Red first: the test that pins the checks fails until the `unit` command runs the suite in parallel
- [ ] Five runs of `python3 checks.py unit` in a row are green, and the comments give their times
- [ ] The comments name every test changed so that it holds in parallel, and what changed; none was skipped or weakened
- [ ] `python3 checks.py` ends green on this ticket's commit

## Comments
