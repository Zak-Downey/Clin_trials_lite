# 01: Every comment is counted

**What to build:** `python3 checks.py --comments` lists every comment the rule will not let through and ends 0, whatever it finds. One line each, `<file>:<line>: <the comment's text>`, then a last line with the total and how many files hold one. A function in `checks.py` does the finding, for any repo: in a Python file git tracks outside `.scratch/`, a comment as Python's tokenizer finds it (a `#` inside a string is never one); in a script or a style sheet under `webapp/static/`, a line holding `//` or `/*`; in a page there, `<!--`. Let through, and so not listed: a first line starting `#!`, and a linter directive that names one rule and gives its reason on the same line (the form `tests/test_lint.py` already requires). The kept list is ticket 05's. Nothing fails on a comment yet, and no comment is removed in this ticket. The function names nothing of this product. Spec: `.scratch/kit-phase-4/spec.md`, "What a comment is", "The two forms let through" and "The count".

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Red first, on small hand-made files in a temporary folder: a comment on its own line and one after code are listed with file, line and text; a `#` inside a string, a `#!` first line and a linter directive with its reason are not; a linter directive with no reason is
- [x] Red first: a script and a style sheet under `webapp/static/` holding `//` or `/*`, and a page holding `<!--`, are listed; the same files without them are not; a file under `.scratch/` is never read
- [x] `python3 checks.py --comments` ends 0 in this repo; its last line and the count for the Python and for the scripts and styles apart are in the comments
- [x] `python3 checks.py` ends green on this ticket's commit

## Comments

- `python3 checks.py --comments` ends 0 in this repo (run on the working folder of this ticket's commit). Its last line: `1286 comments in 102 files`.
- Python: 1111 comments in 82 files (the linter directives with their reason, and `#!` first lines, are not counted). Scripts and styles under `webapp/static/`: 175 lines in 20 files.
- Four of the script lines are a comment inside a block that goes on after it (`/* the choice just is not kept */ }` in `webapp/static/app.js:107`, and the like in `views/check.js`, `views/needs_review.js`, `views/new_matches.js`): the line shows the text from the comment's start to the line's end.
- `python3 checks.py` ended green on this ticket's change before commit (lint, patterns, escapes, unit 0.4 min, walks 2.6 min; 3.0 min).
- The tests are in `tests/test_checks.py` (from `test_a_python_comment_on_its_own_line_or_after_code_is_listed_with_its_file_line_and_text` on); each was seen red first (`AttributeError`: no `comment_hits`, and `--comments` was an unknown check).
