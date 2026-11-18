# Edits to `.claude/skills/implement-spec/SKILL.md` (ticket 10)

The build was not allowed to edit this file, so the two changes are written out here for the owner to apply. Each is an exact replacement: the old words occur once in the file. Nothing else in the file changes, and neither `reviewer.md` nor `walker.md` beside it.

## 1. How long to wait for the checks (line 18)

Agrees with ticket 01's limits: patterns and escapes 1 minute, unit 3, walks 8, so a whole run ends within 13 minutes (`docs/agents/local/repo.md`, "Every check").

Old:

> It takes about four minutes: give it a ten-minute timeout or run it in the background.

New:

> It takes about four minutes and ends within thirteen: give it a fifteen-minute timeout or run it in the background.

## 2. Quick runs after each ticket and each fix; three full runs named

The "When it is red" paragraph is unchanged: its "run the command again" repeats whichever command turned red, quick or full.

Step 4 (after each ticket). Old:

> 4. When the implementer reports, run `python3 checks.py`. Start the next ticket only on green.

New:

> 4. When the implementer reports, run `python3 checks.py --quick`. Start the next ticket only on green.

Step 6 (the full run before the testers and reviewers start). Old:

> Once every ticket is done and the checks are green (with a ticket not done, go to step 9), in parallel:

New:

> Once every ticket is done and a full run of `python3 checks.py` is green (with a ticket not done, go to step 9), in parallel:

Step 7 (after each fix, and the full run after the fixes; steps 5 and 8 fix by step 7's rules, so they follow it too). Old:

> Run `python3 checks.py` after each implementer reports.

New:

> Run `python3 checks.py --quick` after each implementer reports, and a full `python3 checks.py` after the last.

Step 9 (the hand-over run). Old:

> - Run `python3 checks.py` on that commit. If it is red and the build did not stop at step 4,

New:

> - Run the full `python3 checks.py` on that commit. If it is red and the build did not stop at step 4,
