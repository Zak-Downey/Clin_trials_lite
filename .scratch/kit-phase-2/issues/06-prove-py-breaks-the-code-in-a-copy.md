# 06: `prove.py` breaks the code in a copy and says what stayed green

**What to build:** `python3 prove.py` proves the breaks in the list. It copies the files git tracks, as they are on disk, into a temporary folder, and changes nothing outside it. The copy reaches this repo's `.venv` (a link is enough), because `checks.py` and some tests start `.venv/bin/python` from the folder they are in. A list with a fault (ticket 05) stops it before anything runs. For each break it runs the named test or check unbroken, which must be green; makes the change in the copy; and runs it again, which must be red. For a test, red means pytest ran it and it failed (exit code 1): a change that stops the tests being collected or run is not proof and is reported as such. For a check, red means `python3 checks.py <name>` ends 1 in the copy. Each break starts from an unbroken copy. It prints one line per break (its id, what proves it, and one of: caught, stayed green, red before the change, could not run) and a last line with the count; it ends 0 only when every break was caught and the list is not empty. Each run inside it has a limit of two minutes, and no process it starts outlives it, as in `checks.py`. One line per run is appended to `.checks/proof.jsonl` with the time, the commit, the result and each break's outcome. It is a kit file: it names nothing of this product. Spec: `.scratch/kit-phase-2/spec.md`, "`prove.py`" and "When the proof runs".

**Blocked by:** 05

**Status:** ready-for-agent

- [ ] Red first, on a small hand-made repo in a temporary folder: a break its test catches is reported caught and the command ends 0; a break its test misses is reported as stayed green and the command ends 1
- [ ] Red first: a test that is red before the break, a break that stops collection, a run that passes its time limit, and an empty list each end 1 and say which
- [ ] Red first: a break proved by a check is caught when that check goes red in the copy
- [ ] After any of these, the folder it was run in is byte for byte as before (only `.checks/proof.jsonl` gains a line), and nothing it started is still running
- [ ] `python3 prove.py` ends 0 on this repo's two entries from ticket 05, and `python3 checks.py` ends green

## Comments
