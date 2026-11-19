# 04: The scripts and styles hold no comment

**What to build:** Every comment in the scripts, style sheets and pages under `webapp/static/` is removed: today about 164 lines with `//` (123 comment-only lines and 41 after code) and a handful of `/* */` blocks. Removal only: a comment-only line goes; a comment after code is cut, with the space before it; a block comment goes whole. No statement, selector or rule is touched, reordered or re-wrapped. Before cutting, confirm that no `//` or `/*` in these files sits inside a string, a regular expression or an address; if one does, stop and say so in the comments rather than cut it. Prove it: a short script, not kept, shows that every changed line either was a comment-only line and is gone, or equals its old self up to where the comment began. Run the full `python3 checks.py` (every browser test, both window sizes) on the commit before and on this ticket's commit. Spec: `.scratch/kit-phase-4/spec.md`, "Removal only" and "Proof for scripts and styles".

**Blocked by:** 01

**Status:** done

- [x] `python3 checks.py --comments` lists no file under `webapp/static/`
- [x] The comments hold the command that compared each changed line with its old self, and its result, with the number of lines removed and the number cut
- [x] The diff of this ticket's commit removes or shortens lines only: no line is added
- [ ] A full `python3 checks.py`, not quick and not picked, ends green on this ticket's commit

## Comments

- **Count.** `python3 checks.py --comments` listed 175 comment lines under `webapp/static/` before (in 20 files: 129 comment-only lines, 46 lines with code before the comment) and 0 after. The whole repo's count is now `0 comments in 0 files`, because tickets 02 and 03 had already emptied the Python.
- **Strings checked first.** No `//` or `/*` in these files sits inside a string, a regular expression or an address. Every one opens a comment, so nothing was held back. Every `/* */` closes on the line it opens, so the files hold no block that spans several lines. No page holds a `<!--`.
- **Removal.** A script outside the repo (`strip_static.py`, not kept) removed each comment-only line. On a line with code it cut from the first mark to the end of the line, together with the spaces before the mark. On a `/* */` it cut only the comment and kept the code after it: four lines (`app.js:107`, `views/check.js:209`, `views/needs_review.js:28`, `views/new_matches.js:30`) now end `catch { }`.
- **Line comparison.** `python3 compare_static.py . HEAD` (not kept) walks each changed file's old lines against its new ones in order. Each old line has to be one of three things: unchanged, a comment-only line now gone, or a line whose new text equals the old text up to the comment's first mark (trailing spaces dropped) plus anything after a closing `*/`. Any other line counts as an error. Result: `files 20, lines removed 129, lines cut 46, unchanged 2458, any other change 0`.
- **Breaks.** No `find` text in `docs/agents/local/breaks.json` held a comment from these files, and each `find` text still occurs exactly once in its file. breaks.json is unchanged.
- **Checks.** `python3 checks.py lint patterns unit` is green on the working tree that was committed. The full run is left to the coordinator.
