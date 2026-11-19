# 07: A comment is stopped before it is pushed

**What to build:** A git pre-push hook, kept in the repo at `.githooks/pre-push`, so that nothing the cheap checks would refuse reaches GitHub. It runs `python3 checks.py lint patterns escapes` from the repo root, which takes about a second, and nothing slower. When a check is red it prints that check's own lines (the file and line of the comment, and what to do instead) and refuses the push; when all three are green the push goes on with nothing printed beyond git's own lines. Git does not copy hooks with a clone, so the hook is switched on with `git config core.hooksPath .githooks`: run that once in this clone. `python3 checks.py` prints one line, and fails nothing, when a clone has a `.githooks` folder and has not switched it on; it stays silent on GitHub's machine. `docs/agents/local/repo.md`'s "Local hooks" line says what the hook runs, the command that switches it on, and that it judges the working folder as it stands. `.claude/settings.json` gains one deny line that refuses `git push` with `--no-verify`, after the lines that refuse a push to `main`, and the test of the settings pins it. **If the session is not allowed to edit a file under `.claude/`**, do not wait and do not try another way round: write the line and where it goes in `.scratch/kit-phase-4/settings-edit.md` for the owner to apply; the ticket is complete in either form, and `now_what` says which. If the map of the pages needs the new file placed (`tests/test_walk_map.py` says so), place it. Spec: `.scratch/kit-phase-4/spec.md`, "Before a push" and "Editing under `.claude/`".

**Blocked by:** 05

**Status:** done

- [x] Red first, by a real push from a temporary repo to a temporary remote, with a stand-in `checks.py`: when a check is red the push is refused, the red check's lines are printed and the remote does not have the commit; when all are green the commit arrives
- [x] Red first: `python3 checks.py` prints its one line in a clone that has `.githooks` and has not switched it on, prints nothing about it once switched on, and prints nothing on GitHub's machine
- [x] In this clone the hook is switched on. In a copy of this repo in a temporary folder, with a temporary remote and the real `checks.py`, a push with a comment added is refused in about a second; the comments hold what was printed and how long it took. This ticket pushes nothing to GitHub
- [ ] The settings refuse `git push` with `--no-verify`, or `settings-edit.md` holds the edit in full; `repo.md`'s "Local hooks" line is true; `python3 checks.py` ends green on this ticket's commit

## Comments

- **2026-11-19, the build.** The hook is `.githooks/pre-push`; it runs `python3 checks.py lint patterns escapes` from the repo root and prints only when one is red. `git config core.hooksPath .githooks` was run in this clone. `.claude/settings.json` was edited in place (the edit was allowed): `"Bash(git push*--no-verify*)"` sits right after the three lines that refuse a push to `main`, and `tests/test_settings.py` pins it there; no `settings-edit.md` was needed. `python3 checks.py` says when a clone has `.githooks` and has not switched it on, unless `GITHUB_ACTIONS` is `true`. `.githooks/*` is placed in the map's `none`. Tests, each seen red first (the two green-path ones by breaking the code on purpose): `tests/test_pre_push.py` (two real pushes to a temporary bare remote with a stand-in `checks.py`), the three `githooks` tests at the end of `tests/test_checks.py`, and `test_the_settings_refuse_a_push_that_skips_the_hook_right_after_the_refusals_of_a_push_to_main`.
- **2026-11-19, the timed trial.** A copy of this working folder in a temporary folder (the repo's `.venv` linked in), a temporary bare remote, the real `checks.py` and the hook switched on. A commit adding `x = 1  # a comment` to `webapp/__init__.py` was refused in 0.42 seconds, and the remote got nothing. Printed:

  ```
  lint      green    0.0 min  .checks/lint.txt
  patterns  red      0.0 min  .checks/patterns.txt
      webapp/__init__.py:2: say it in a name, or in a test that fails without it; a comment is checked by nothing (# a comment)
  escapes   not run (patterns was red)
  checks: red (patterns) in 0.0 min
  error: failed to push some refs to '<temporary folder>/remote.git'
  ```

  With the comment taken out again, the push went through in 1.15 seconds with only git's own lines. The temporary folder was deleted; nothing was pushed to GitHub.
