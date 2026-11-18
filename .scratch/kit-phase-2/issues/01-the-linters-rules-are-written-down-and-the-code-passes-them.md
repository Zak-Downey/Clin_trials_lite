# 01: The linter's rules are written down and the code passes them

**What to build:** Ruff joins `requirements-dev.txt`, pinned to one exact version (`ruff==0.17.5`), and is installed into this repo's `.venv`. A `ruff.toml` at the repo root selects exactly `E4`, `E7`, `E9`, `F` and `RUF100`, states the Python version of this repo's `.venv`, leaves `.scratch/` unread, and exempts no rule, file or folder. Then the code is cleaned until `.venv/bin/python -m ruff check .` reports nothing: 25 findings when this was written (15 unused imports, 4 unused variables, 3 `# noqa` markers that silence nothing, 1 f-string with no placeholder, 1 lambda assigned to a name, 1 import not at the top). Each is fixed in the code. Where one cannot be fixed without changing what the code does, a `# noqa` naming that one rule, with the reason on the same line, is allowed and counted in this ticket's comments. No fix changes behaviour. This ticket adds no check: `CHECKS` is ticket 02's. Spec: `.scratch/kit-phase-2/spec.md`, "The linter", "Its rules are written out", "What it reads" and "Cleaning up".

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Red first: a test fails until `requirements-dev.txt` pins Ruff to one exact version and `ruff.toml` selects exactly the five rule groups, reads no file under `.scratch/`, and exempts nothing
- [x] `.venv/bin/python -m ruff check .` reports no finding, and leaves `git status` as it found it
- [x] The comments list the findings fixed, counted by rule, and every `# noqa` added or removed, with the reason for each one added
- [x] `python3 checks.py` ends green on this ticket's commit, so no fix changed what the code does

## Comments

Ruff 0.17.5 is pinned in `requirements-dev.txt` and installed in `.venv`. `ruff.toml` selects exactly `E4`, `E7`, `E9`, `F`, `RUF100`, sets `target-version = "py313"` (the `.venv` is Python 3.13.15) and excludes only `.scratch/` (`extend-exclude`, so Ruff's own default excludes, `.venv` among them, still apply). `tests/test_lint.py` holds this: all five of its tests were seen red before `ruff.toml` and the pin existed. One of them runs `ruff check --no-cache --show-files .` and holds that every tracked Python file outside `.scratch/` is read and nothing under `.scratch/` or `.venv/` is.

The 25 findings, all fixed in the code, by rule (the same 25 the spec counted):

- **F401, unused import: 15.** `os` in `walks/run_walks.py` and `webapp/instance.py`; `time` in `tests/test_api_new_matches.py`; `pytest` in six `walks/test_explore_*` files; `walks.helper` in `walks/test_add_by_id_walk.py`, `walks/test_explore_summary_and_export_summary_explore.py`, `walks/test_find_trials_walk.py`, `walks/test_standin_registry.py`; `dialog` and `results` in `walks/test_explore_saved_search_and_new_matches_saved_search_new_matches.py`. I searched for uses through the module (a monkeypatch of `instance.os` and the like) and found none; `walks.helper` is still loaded by `walks/conftest.py`, and `dialog`/`results` are plain functions, not fixtures.
- **F841, unused variable: 4.** `walks/test_acceptance_walk.py`: `field = self.focus(target)` became `self.focus(target)` (the focus still happens); `pending = []` removed; `links = page...get_by_role("link")` removed (building a Playwright locator does nothing until it is used). `walks/test_saved_search_walk.py`: `mine = next(...)` became `assert any(w["name"] == "Myeloma" ...)`, so the seed still stops if the find seed made no Myeloma watchlist (an AssertionError where it was a StopIteration).
- **RUF100, `# noqa` that silenced nothing: 3.** Removed `# noqa: E402` from `tests/conftest.py` (`import storage`) and from both imports in `walks/serve.py`: Ruff accepts an import after `sys.path.insert` without one.
- **F541, f-string with no placeholder: 1.** `walks/test_acceptance_walk.py`, the `.badge[title="0 to review"]` selector lost its `f`.
- **E731, lambda assigned to a name: 1.** `entry` in `tests/test_handover.py` is now a `def` with the same defaults.
- **E402, import not at the top: 1.** `import ssl` in `ctgov.py` moved up with the other standard imports; its comment stays with the `truststore` block it explains.

`# noqa` markers: 3 removed (above), none added. Every marker left outside `.scratch/` silences a finding of a selected rule: RUF100 reports any that does not, and it reports none.

`.venv/bin/python -m ruff check .` reports "All checks passed!" and `git status` is the same before and after it: Ruff writes `.ruff_cache/`, which carries its own `.gitignore` (I deleted it afterwards). This ticket adds no check to `CHECKS` (ticket 02's).
