# 10: The build instructions use picked runs

**What to build:** Two changes to `.claude/skills/implement-spec/SKILL.md`, with as few changed words as will do them. First, its line on how long a whole run of the checks can take agrees with the limits in `CHECKS` (it says thirteen minutes; the five limits now add up to fourteen). Second, the run after each ticket and after each fix becomes `python3 checks.py --quick --pick`; the run before the testers and reviewers start, the run after the fixes and the hand-over run stay plain `python3 checks.py`. Nothing else in the file changes, and neither brief beside it. Make the second change only if ticket 09's proof ended 0; if a break was hidden and not fixed, make the first change alone, say so in `now_what`, and the ticket is complete in that form. The session running this build keeps running its checks as the file said when the build started. **If the session is not allowed to edit a file under `.claude/`** (the edit is refused, or stops for an approval nobody is there to give), do not wait and do not try another way round: write the change out in full, old words and new, in `.scratch/kit-phase-3/skill-edits.md` for the owner to apply. The ticket is complete in either form, and `now_what` says which. Spec: `.scratch/kit-phase-3/spec.md`, "Instructions" and "Editing under `.claude/`".

**Blocked by:** 08, 09

**Status:** ready-for-agent

- [ ] The skill's time for a whole run agrees with the limits in `CHECKS`, or `skill-edits.md` holds that edit in full
- [ ] The skill asks for a quick, picked run after each ticket and each fix and names the three full runs, or `skill-edits.md` holds that edit in full, or the comments say the edit was withheld because the proof did not pass
- [ ] No other line of the skill file changed, and neither brief beside it
- [ ] `repo.md` and the skill file agree on when a run is picked
- [ ] `python3 checks.py` ends green on this ticket's commit

## Comments
