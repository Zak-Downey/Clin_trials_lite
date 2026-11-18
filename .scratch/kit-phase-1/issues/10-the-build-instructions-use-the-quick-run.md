# 10: The build instructions use the quick run

**What to build:** Two changes to `.claude/skills/implement-spec/SKILL.md`, with as few changed words as will do them. First, its line on how long to wait for `python3 checks.py` agrees with ticket 01's limits. Second, the run after each ticket and after each fix is `python3 checks.py --quick`; the run before the testers and reviewers start, the run after the fixes and the hand-over run stay plain `python3 checks.py`. Nothing else in the file changes, and neither brief beside it. The session running this build keeps running plain `python3 checks.py` every time, whatever this file says once edited. **If the session is not allowed to edit a file under `.claude/`** (the edit is refused, or stops for an approval nobody is there to give), do not wait and do not try another way round: write the two changes out in full, old words and new, in `.scratch/kit-phase-1/skill-edits.md` for the owner to apply. The ticket is complete in either form, and `now_what` says which. Spec: `.scratch/kit-phase-1/spec.md`, "Instructions" and "Editing under `.claude/`".

**Blocked by:** 01, 09

**Status:** ready-for-agent

- [ ] The skill's waiting time for the checks agrees with the limits of ticket 01, or `skill-edits.md` holds that edit in full
- [ ] The skill asks for a quick run after each ticket and each fix and names the three full runs, or `skill-edits.md` holds that edit in full
- [ ] No other line of the skill file changed, and neither brief beside it
- [ ] `python3 checks.py` ends green on this ticket's commit

## Comments
