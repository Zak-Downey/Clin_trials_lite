# 01: The linter's rules are written down and the code passes them

**What to build:** Ruff joins `requirements-dev.txt`, pinned to one exact version (`ruff==0.17.5`), and is installed into this repo's `.venv`. A `ruff.toml` at the repo root selects exactly `E4`, `E7`, `E9`, `F` and `RUF100`, states the Python version of this repo's `.venv`, leaves `.scratch/` unread, and exempts no rule, file or folder. Then the code is cleaned until `.venv/bin/python -m ruff check .` reports nothing: 25 findings when this was written (15 unused imports, 4 unused variables, 3 `# noqa` markers that silence nothing, 1 f-string with no placeholder, 1 lambda assigned to a name, 1 import not at the top). Each is fixed in the code. Where one cannot be fixed without changing what the code does, a `# noqa` naming that one rule, with the reason on the same line, is allowed and counted in this ticket's comments. No fix changes behaviour. This ticket adds no check: `CHECKS` is ticket 02's. Spec: `.scratch/kit-phase-2/spec.md`, "The linter", "Its rules are written out", "What it reads" and "Cleaning up".

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Red first: a test fails until `requirements-dev.txt` pins Ruff to one exact version and `ruff.toml` selects exactly the five rule groups, reads no file under `.scratch/`, and exempts nothing
- [ ] `.venv/bin/python -m ruff check .` reports no finding, and leaves `git status` as it found it
- [ ] The comments list the findings fixed, counted by rule, and every `# noqa` added or removed, with the reason for each one added
- [ ] `python3 checks.py` ends green on this ticket's commit, so no fix changed what the code does

## Comments
