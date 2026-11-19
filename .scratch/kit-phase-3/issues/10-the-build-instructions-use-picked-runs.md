# 10: The build instructions use picked runs

**What to build:** Two changes to `.claude/skills/implement-spec/SKILL.md`, with as few changed words as will do them. First, its line on how long a whole run of the checks can take agrees with the limits in `CHECKS` (it says thirteen minutes; the five limits now add up to fourteen). Second, the run after each ticket and after each fix becomes `python3 checks.py --quick --pick`; the run before the testers and reviewers start, the run after the fixes and the hand-over run stay plain `python3 checks.py`. Nothing else in the file changes, and neither brief beside it. Make the second change only if ticket 09's proof ended 0; if a break was hidden and not fixed, make the first change alone, say so in `now_what`, and the ticket is complete in that form. The session running this build keeps running its checks as the file said when the build started. **If the session is not allowed to edit a file under `.claude/`** (the edit is refused, or stops for an approval nobody is there to give), do not wait and do not try another way round: write the change out in full, old words and new, in `.scratch/kit-phase-3/skill-edits.md` for the owner to apply. The ticket is complete in either form, and `now_what` says which. Spec: `.scratch/kit-phase-3/spec.md`, "Instructions" and "Editing under `.claude/`".

**Blocked by:** 08, 09

**Status:** done

- [x] The skill's time for a whole run agrees with the limits in `CHECKS`, or `skill-edits.md` holds that edit in full
- [x] The skill asks for a quick, picked run after each ticket and each fix and names the three full runs, or `skill-edits.md` holds that edit in full, or the comments say the edit was withheld because the proof did not pass
- [x] No other line of the skill file changed, and neither brief beside it
- [x] `repo.md` and the skill file agree on when a run is picked
- [x] `python3 checks.py` ends green on this ticket's commit

## Comments

**2026-11-19, the implementer.** The skill file was edited directly; the edit under `.claude/` was not refused, so no `skill-edits.md` was written. Ticket 09's proof ended 0 with no break hidden, so both changes were made. Three words changed in `.claude/skills/implement-spec/SKILL.md` and nothing else in it or in `walker.md` and `reviewer.md`:

- The time for a whole run now says it "ends within fourteen" (was thirteen), matching the limits in `CHECKS`: 1 + 1 + 1 + 3 + 8 = 14 minutes.
- Step 4 (after each ticket) and step 7 (after each fix implementer reports) now run `python3 checks.py --quick --pick` (was `--quick`). The run before the testers and reviewers (step 6), the run after the last fix (step 7) and the hand-over run (step 9) stay plain `python3 checks.py`.

`docs/agents/local/repo.md` already agreed ("A picked run is right after a ticket and after a fix", with the same three runs whole), so it was not changed. `python3 checks.py` ended green on the edited files (2.9 minutes: unit 0.3, walks 2.6).
