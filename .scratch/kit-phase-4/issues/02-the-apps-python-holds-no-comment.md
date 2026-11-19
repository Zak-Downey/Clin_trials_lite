# 02: The app's Python holds no comment

**What to build:** Every comment that ticket 01's command lists in a Python file outside `tests/` and `walks/` is removed: the app's modules, `checks.py`, `handover.py`, `prove.py`, `picker.py`, `walk_map.py`, `run.py` and the rest. Removal only: a line that held only a comment goes; a comment after code is cut, with the space before it; nothing else on the line or near it changes. No rename, no re-wrapping, no moved code, no new or longer docstring. Linter directives with their reason stay. Do it with a short script that uses Python's tokenizer, not by hand; the script is not kept. Prove it: for every file changed, the syntax tree (`ast.dump`) at this ticket's commit equals the tree at the commit before it. Do not try to save a comment's meaning here: the reviewer reads the removed lines later, and ticket 05 has the list for the few that must stay. Spec: `.scratch/kit-phase-4/spec.md`, "Removal only" and "Proof for Python".

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] `python3 checks.py --comments` lists no Python file outside `tests/` and `walks/`
- [ ] The comments hold the command that compared every changed file's syntax tree with its tree at the commit before, and its result: all equal, with the number of files
- [ ] The diff of this ticket's commit removes or shortens lines only: no line is added
- [ ] `python3 checks.py` ends green on this ticket's commit

## Comments
