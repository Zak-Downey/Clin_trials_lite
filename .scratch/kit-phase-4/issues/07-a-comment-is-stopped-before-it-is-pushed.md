# 07: A comment is stopped before it is pushed

**What to build:** A git pre-push hook, kept in the repo at `.githooks/pre-push`, so that nothing the cheap checks would refuse reaches GitHub. It runs `python3 checks.py lint patterns escapes` from the repo root, which takes about a second, and nothing slower. When a check is red it prints that check's own lines (the file and line of the comment, and what to do instead) and refuses the push; when all three are green the push goes on with nothing printed beyond git's own lines. Git does not copy hooks with a clone, so the hook is switched on with `git config core.hooksPath .githooks`: run that once in this clone. `python3 checks.py` prints one line, and fails nothing, when a clone has a `.githooks` folder and has not switched it on; it stays silent on GitHub's machine. `docs/agents/local/repo.md`'s "Local hooks" line says what the hook runs, the command that switches it on, and that it judges the working folder as it stands. `.claude/settings.json` gains one deny line that refuses `git push` with `--no-verify`, after the lines that refuse a push to `main`, and the test of the settings pins it. **If the session is not allowed to edit a file under `.claude/`**, do not wait and do not try another way round: write the line and where it goes in `.scratch/kit-phase-4/settings-edit.md` for the owner to apply; the ticket is complete in either form, and `now_what` says which. If the map of the pages needs the new file placed (`tests/test_walk_map.py` says so), place it. Spec: `.scratch/kit-phase-4/spec.md`, "Before a push" and "Editing under `.claude/`".

**Blocked by:** 05

**Status:** ready-for-agent

- [ ] Red first, by a real push from a temporary repo to a temporary remote, with a stand-in `checks.py`: when a check is red the push is refused, the red check's lines are printed and the remote does not have the commit; when all are green the commit arrives
- [ ] Red first: `python3 checks.py` prints its one line in a clone that has `.githooks` and has not switched it on, prints nothing about it once switched on, and prints nothing on GitHub's machine
- [ ] In this clone the hook is switched on. In a copy of this repo in a temporary folder, with a temporary remote and the real `checks.py`, a push with a comment added is refused in about a second; the comments hold what was printed and how long it took. This ticket pushes nothing to GitHub
- [ ] The settings refuse `git push` with `--no-verify`, or `settings-edit.md` holds the edit in full; `repo.md`'s "Local hooks" line is true; `python3 checks.py` ends green on this ticket's commit

## Comments
