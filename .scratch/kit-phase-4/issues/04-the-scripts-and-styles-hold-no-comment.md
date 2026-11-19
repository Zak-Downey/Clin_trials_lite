# 04: The scripts and styles hold no comment

**What to build:** Every comment in the scripts, style sheets and pages under `webapp/static/` is removed: today about 164 lines with `//` (123 comment-only lines and 41 after code) and a handful of `/* */` blocks. Removal only: a comment-only line goes; a comment after code is cut, with the space before it; a block comment goes whole. No statement, selector or rule is touched, reordered or re-wrapped. Before cutting, confirm that no `//` or `/*` in these files sits inside a string, a regular expression or an address; if one does, stop and say so in the comments rather than cut it. Prove it: a short script, not kept, shows that every changed line either was a comment-only line and is gone, or equals its old self up to where the comment began. Run the full `python3 checks.py` (every browser test, both window sizes) on the commit before and on this ticket's commit. Spec: `.scratch/kit-phase-4/spec.md`, "Removal only" and "Proof for scripts and styles".

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] `python3 checks.py --comments` lists no file under `webapp/static/`
- [ ] The comments hold the command that compared each changed line with its old self, and its result, with the number of lines removed and the number cut
- [ ] The diff of this ticket's commit removes or shortens lines only: no line is added
- [ ] A full `python3 checks.py`, not quick and not picked, ends green on this ticket's commit

## Comments
