# 02: The app's Python holds no comment

**What to build:** Every comment that ticket 01's command lists in a Python file outside `tests/` and `walks/` is removed: the app's modules, `checks.py`, `handover.py`, `prove.py`, `picker.py`, `walk_map.py`, `run.py` and the rest. Removal only: a line that held only a comment goes; a comment after code is cut, with the space before it; nothing else on the line or near it changes. No rename, no re-wrapping, no moved code, no new or longer docstring. Linter directives with their reason stay. Do it with a short script that uses Python's tokenizer, not by hand; the script is not kept. Prove it: for every file changed, the syntax tree (`ast.dump`) at this ticket's commit equals the tree at the commit before it. Do not try to save a comment's meaning here: the reviewer reads the removed lines later, and ticket 05 has the list for the few that must stay. Spec: `.scratch/kit-phase-4/spec.md`, "Removal only" and "Proof for Python".

**Blocked by:** 01

**Status:** done

- [x] `python3 checks.py --comments` lists no Python file outside `tests/` and `walks/`
- [x] The comments hold the command that compared every changed file's syntax tree with its tree at the commit before, and its result: all equal, with the number of files
- [x] The diff of this ticket's commit removes or shortens lines only: no line is added
- [ ] `python3 checks.py` ends green on this ticket's commit

## Comments

- Count before (at 4fc7b46): `python3 checks.py --comments` printed 1286 comments in 102 files; 479 of them in 21 Python files outside `tests/` and `walks/`. After: 807 comments in 81 files, none in a Python file outside `tests/` and `walks/`.
- Removed with a throwaway tokenizer script (not kept): it took the lines `checks.python_comments` reports, so `#!` first lines and linter directives with their reason stay. 398 comment-only lines deleted, 82 lines cut after their code; the diff is 82 insertions (each a cut line, equal to its old self up to the comment) and 480 deletions.
- Proof, run on the working tree before the commit against 4fc7b46: `git diff --name-only 4fc7b46 -- '*.py'`, then for each file `ast.dump(ast.parse(git show 4fc7b46:<file>)) == ast.dump(ast.parse(<file now>))`. Result: 21 files compared, 21 equal.
- `python3 checks.py lint patterns unit` green on the change. No test read a removed comment. Every `find` text in `docs/agents/local/breaks.json` is still in its file, so it was not touched. The full `python3 checks.py` is left to the build's own run.
