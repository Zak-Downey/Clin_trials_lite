# 03: The tests and the browser tests hold no comment

**What to build:** The same removal for every Python file under `tests/` and `walks/`: every comment ticket 01's command lists there is removed, and nothing else changes. A line that held only a comment goes; a comment after code is cut, with the space before it. No test is renamed, split, merged or reworded, and no assertion changes. Linter directives with their reason stay. Use the same kind of tokenizer script as ticket 02, and the same proof: for every file changed, the syntax tree at this ticket's commit equals the tree at the commit before it. If a test reads another file's text and went red because a comment it looked for is gone, say so in the comments and fix the test to look for what the code does, not for the comment. Spec: `.scratch/kit-phase-4/spec.md`, "Removal only" and "Proof for Python".

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] `python3 checks.py --comments` lists no Python file at all
- [ ] The comments hold the command that compared every changed file's syntax tree with its tree at the commit before, and its result: all equal, with the number of files; any test changed beyond that is named, with the reason
- [ ] The number of tests the unit suite and the browser tests collect is the same before and after, and both numbers are in the comments
- [ ] `python3 checks.py` ends green on this ticket's commit

## Comments
