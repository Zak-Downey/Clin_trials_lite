# 03: The tests and the browser tests hold no comment

**What to build:** The same removal for every Python file under `tests/` and `walks/`: every comment ticket 01's command lists there is removed, and nothing else changes. A line that held only a comment goes; a comment after code is cut, with the space before it. No test is renamed, split, merged or reworded, and no assertion changes. Linter directives with their reason stay. Use the same kind of tokenizer script as ticket 02, and the same proof: for every file changed, the syntax tree at this ticket's commit equals the tree at the commit before it. If a test reads another file's text and went red because a comment it looked for is gone, say so in the comments and fix the test to look for what the code does, not for the comment. Spec: `.scratch/kit-phase-4/spec.md`, "Removal only" and "Proof for Python".

**Blocked by:** 02

**Status:** done

- [x] `python3 checks.py --comments` lists no Python file at all
- [x] The comments hold the command that compared every changed file's syntax tree with its tree at the commit before, and its result: all equal, with the number of files; any test changed beyond that is named, with the reason
- [x] The number of tests the unit suite and the browser tests collect is the same before and after, and both numbers are in the comments
- [ ] `python3 checks.py` ends green on this ticket's commit

## Comments

- Count before (at de58f98): `python3 checks.py --comments` printed 807 comments in 81 files; 632 of them in 61 Python files under `tests/` and `walks/`. After: 175 comments in 20 files, none in a Python file. No comment was listed under `walks/broken/`, so the deliberately broken pages are untouched.
- Removed with a throwaway tokenizer script (outside the repo, not kept): it took the lines `checks.python_comments` reports, so `#!` first lines and linter directives with their reason stay. 250 comment-only lines deleted, 382 lines cut after their code; the diff is 382 insertions (each a cut line, equal to its old self up to the comment) and 632 deletions. Every added line holding a `#` holds it inside a string (CSS selectors, `#/` routes, `&#x27;`).
- Proof, run on the working tree before the commit against de58f98: `git diff --name-only HEAD -- '*.py'`, then for each file `ast.dump(ast.parse(git show HEAD:<file>)) == ast.dump(ast.parse(<file now>))`. Result: 61 files compared, 61 equal.
- Tests collected, before and after: unit suite (`.venv/bin/python -m pytest --collect-only -q tests`) 791 and 791; browser tests (`... walks`) 412 and 412.
- No test changed beyond comment removal: no test read a removed comment. `python3 checks.py lint patterns unit` green on the change. Every `find` text in `docs/agents/local/breaks.json` is still in its file. The full `python3 checks.py` is left to the build's own run.
