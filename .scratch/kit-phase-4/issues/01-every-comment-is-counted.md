# 01: Every comment is counted

**What to build:** `python3 checks.py --comments` lists every comment the rule will not let through and ends 0, whatever it finds. One line each, `<file>:<line>: <the comment's text>`, then a last line with the total and how many files hold one. A function in `checks.py` does the finding, for any repo: in a Python file git tracks outside `.scratch/`, a comment as Python's tokenizer finds it (a `#` inside a string is never one); in a script or a style sheet under `webapp/static/`, a line holding `//` or `/*`; in a page there, `<!--`. Let through, and so not listed: a first line starting `#!`, and a linter directive that names one rule and gives its reason on the same line (the form `tests/test_lint.py` already requires). The kept list is ticket 05's. Nothing fails on a comment yet, and no comment is removed in this ticket. The function names nothing of this product. Spec: `.scratch/kit-phase-4/spec.md`, "What a comment is", "The two forms let through" and "The count".

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Red first, on small hand-made files in a temporary folder: a comment on its own line and one after code are listed with file, line and text; a `#` inside a string, a `#!` first line and a linter directive with its reason are not; a linter directive with no reason is
- [ ] Red first: a script and a style sheet under `webapp/static/` holding `//` or `/*`, and a page holding `<!--`, are listed; the same files without them are not; a file under `.scratch/` is never read
- [ ] `python3 checks.py --comments` ends 0 in this repo; its last line and the count for the Python and for the scripts and styles apart are in the comments
- [ ] `python3 checks.py` ends green on this ticket's commit

## Comments
