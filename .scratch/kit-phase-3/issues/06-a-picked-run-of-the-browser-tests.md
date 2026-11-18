# 06: `python3 checks.py --pick` runs the picked browser tests

**What to build:** A new option of `checks.py`, `--pick`, not a new check: the list of checks is unchanged. With it, the `walks` check runs only the walk files that ticket 05 picks, through the walk runner's existing way of taking named files; `lint`, `patterns` and `escapes` run whole; the `unit` check runs whole until ticket 07. It combines with `--quick` and with naming checks. The run prints one line for the picked check (how many walk files it ran, out of how many, and the reason), and its line in `.checks/runs.jsonl` carries `"picked": true`, the base and the reason; every other run's line carries `"picked": false`. Plain `python3 checks.py` and `--quick` alone behave exactly as now. The workflow never passes `--pick`, and the test of the workflow holds that. `repo.md` gains a "Picked run" line beside "Quick run": what it is, that it is right after a ticket and after a fix, that the same three runs and the check on GitHub are always whole, and that a picked run is never a full run. Spec: `.scratch/kit-phase-3/spec.md`, "The option", "What a picked run says" and "Full runs".

**Blocked by:** 05

**Status:** ready-for-agent

- [ ] Red first, with stand-in check commands: a picked run passes the picked files to the walk check and logs `"picked": true` with the base and the reason; a plain run and a quick run log `"picked": false` and run what they run today
- [ ] Red first: the test of the workflow fails if the workflow passes `--pick`
- [ ] In this repo, after a change to one page's script, `python3 checks.py --quick --pick walks` runs that area's walks and `always`, and its printed line says how many of how many and why; the comments hold that line and its minutes beside a whole quick run's
- [ ] `repo.md` has the "Picked run" line, and `python3 checks.py` ends green on this ticket's commit

## Comments
