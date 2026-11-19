# 06: `python3 checks.py --pick` runs the picked browser tests

**What to build:** A new option of `checks.py`, `--pick`, not a new check: the list of checks is unchanged. With it, the `walks` check runs only the walk files that ticket 05 picks, through the walk runner's existing way of taking named files; `lint`, `patterns` and `escapes` run whole; the `unit` check runs whole until ticket 07. It combines with `--quick` and with naming checks. The run prints one line for the picked check (how many walk files it ran, out of how many, and the reason), and its line in `.checks/runs.jsonl` carries `"picked": true`, the base and the reason; every other run's line carries `"picked": false`. Plain `python3 checks.py` and `--quick` alone behave exactly as now. The workflow never passes `--pick`, and the test of the workflow holds that. `repo.md` gains a "Picked run" line beside "Quick run": what it is, that it is right after a ticket and after a fix, that the same three runs and the check on GitHub are always whole, and that a picked run is never a full run. Spec: `.scratch/kit-phase-3/spec.md`, "The option", "What a picked run says" and "Full runs".

**Blocked by:** 05

**Status:** done

- [x] Red first, with stand-in check commands: a picked run passes the picked files to the walk check and logs `"picked": true` with the base and the reason; a plain run and a quick run log `"picked": false` and run what they run today
- [x] Red first: the test of the workflow fails if the workflow passes `--pick`
- [x] In this repo, after a change to one page's script, `python3 checks.py --quick --pick walks` runs that area's walks and `always`, and its printed line says how many of how many and why; the comments hold that line and its minutes beside a whole quick run's
- [x] `repo.md` has the "Picked run" line, and `python3 checks.py` ends green on this ticket's commit

## Comments

A picked quick run of the walks took 0.6 minutes against 1.4 for a whole quick run, after a one-line change to the Summary page's script. Both were run on 2026-11-19 on the owner's Mac, at commit facd7ee, whose run of every check (`python3 checks.py`, on a clean folder) was green in 2.7 minutes (unit 0.2, walks 2.5) and was the picked run's base. The throwaway line was undone afterwards with `git checkout -- webapp/static/views/summary.js`.

| Run | Printed line for the walks | Walk tests | Minutes |
|---|---|---|---|
| `python3 checks.py --quick --pick walks` | `walks     picked 4 of 42 walk files: Summary, because `webapp/static/views/summary.js` changed; and the walks that always run` | 38 passed | 0.6 |
| `python3 checks.py --quick walks` | (no picked line) | 226 passed | 1.4 |

The four files were the Summary area's two (`walks/test_summary_walk.py`, `walks/test_explore_summary_and_export_summary_explore.py`) and `always` (`walks/test_walk_guards.py`, `walks/test_acceptance_walk.py`). The picked run's line in `.checks/runs.jsonl` read `"picked": true`, `"base": "since the last green run of every check, at facd7ee"`, `"picks": [{"check": "walks", "ran": 4, "of": 42, "why": "Summary, because ... changed; and the walks that always run"}]`; the whole quick run's read `"picked": false`.

While the code was uncommitted, a pick would have run every walk, because `checks.py` is in the map's `shared` list: that is the picker working as the map says, so the code was committed and its whole run made the base before measuring.

The first whole run after adding `--pick` was red: three tests in `tests/test_prove_runs.py` build a small repo holding `checks.py` alone, and `checks.py` then imported `picker.py` at the top. It now loads the picker only in a picked run, so a plain run needs nothing new; the commit was amended before the green run above.

