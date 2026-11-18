# 06: `prove.py` breaks the code in a copy and says what stayed green

**What to build:** `python3 prove.py` proves the breaks in the list. It copies the files git tracks, as they are on disk, into a temporary folder, and changes nothing outside it. The copy reaches this repo's `.venv` (a link is enough), because `checks.py` and some tests start `.venv/bin/python` from the folder they are in. A list with a fault (ticket 05) stops it before anything runs. For each break it runs the named test or check unbroken, which must be green; makes the change in the copy; and runs it again, which must be red. For a test, red means pytest ran it and it failed (exit code 1): a change that stops the tests being collected or run is not proof and is reported as such. For a check, red means `python3 checks.py <name>` ends 1 in the copy. Each break starts from an unbroken copy. It prints one line per break (its id, what proves it, and one of: caught, stayed green, red before the change, could not run) and a last line with the count; it ends 0 only when every break was caught and the list is not empty. Each run inside it has a limit of two minutes, and no process it starts outlives it, as in `checks.py`. One line per run is appended to `.checks/proof.jsonl` with the time, the commit, the result and each break's outcome. It is a kit file: it names nothing of this product. Spec: `.scratch/kit-phase-2/spec.md`, "`prove.py`" and "When the proof runs".

**Blocked by:** 05

**Status:** done

- [x] Red first, on a small hand-made repo in a temporary folder: a break its test catches is reported caught and the command ends 0; a break its test misses is reported as stayed green and the command ends 1
- [x] Red first: a test that is red before the break, a break that stops collection, a run that passes its time limit, and an empty list each end 1 and say which
- [x] Red first: a break proved by a check is caught when that check goes red in the copy
- [x] After any of these, the folder it was run in is byte for byte as before (only `.checks/proof.jsonl` gains a line), and nothing it started is still running
- [x] `python3 prove.py` ends 0 on this repo's two entries from ticket 05, and `python3 checks.py` ends green

## Comments

- `python3 prove.py` (prove.py is now 213 lines, 05's 80 included, against the spec's "about 150"): it stops on a list with a fault or an empty list before anything runs; otherwise, for each break, it copies the files `git ls-files` names, as they are on disk, into a fresh temporary folder with `.venv` a link to this repo's, runs the test (`.venv/bin/python -m pytest -q -p no:cacheprovider <id>`) or the check (`python3 checks.py <name>`) unbroken and then broken, and prints `<id>  <test or check>  <outcome>`, with the reason and the last 20 lines of output for anything not caught, then `proof: <n> of <m> breaks caught`. Outcomes: caught (exit 1 after the change), stayed green, red before the change, could not run (stopped at the limit, or any exit code other than 0 and 1, such as pytest's 4 when the named test cannot be collected). The limit is `prove(root, minutes=2, out=print)`; each run kills its whole process group as `checks.run_one` does. One line per run goes to `.checks/proof.jsonl`: `at`, `commit`, `dirty` (the copy is taken from disk, so a dirty run is not the commit's), `result`, `breaks` (id and outcome each).
- Every run in the copy has `PYTHONDONTWRITEBYTECODE=1`. Without it the first test stayed green: a change of the same length (`a + b` to `a - b`) in the same second as the unbroken run leaves the cached bytecode looking current, so the broken run imported the unbroken module. The same would happen in this repo (`>` to `>=` is not the same length, but other breaks will be).
- Tests in `tests/test_prove_runs.py` (8), on a small committed git repo in a temporary folder holding a module, a test, the real `checks.py` and a list, with `.venv` linked to this repo's; every case also checks that the folder is byte for byte as before apart from `.checks/proof.jsonl`. Red first: caught (then the log line's commit and time, red by making the commit blank), red before the change, a break that stops collection, a run past its limit, an empty list, a list with a fault, and a break proved by the `unit` check (caught, and a missed one stayed green). Two were green on first run because the code already did it, so I saw each red by breaking the code on purpose and restoring it: stayed green (with every outcome forced to caught) and that nothing outlives a timeout (with `os.killpg` replaced by killing only the first process: the test's child process survived and the test went red).
- `python3 prove.py` on this repo at 16dcb14 plus this change, uncommitted: exit 0 in 2 seconds (0.03 minutes).

```
summary-one-day-range-refused  tests/test_api_summary.py::test_a_custom_range_is_inclusive_and_validated  caught
summary-import-left-unused  lint  caught
proof: 2 of 2 breaks caught
```

  `git status --porcelain` was the same before and after it.
- For ticket 07: the two-minute limit applies to each run inside the proof, and `checks.py walks` took 2.6 minutes when last measured, so a break proved by the `walks` check would be stopped and reported as could not run. A break proved by one walk, named as a test, runs in seconds. I left the limit at the spec's two minutes.
- A full `python3 checks.py` on the uncommitted change ended green in 3.8 minutes (lint, patterns, escapes, unit 1.2, walks 2.6); `checks.py lint` and `unit` also ended green on their own.
