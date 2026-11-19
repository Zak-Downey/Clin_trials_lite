# 05: A fix's test covers every case

**What to build:** One sentence in step 7 of `.claude/skills/implement-spec/SKILL.md`, where it says a check that is red because of the finding goes into the suite before the fix: that check covers every place the rule behind the finding applies, not only the place the finding named (R-006, "Every means every", at the time of the fix). Two builds needed a second review round for want of it: `kit-phase-1` (`review-server-and-checks-04`, then `review-whole-recheck-01`: this product's words in a second part of `handover.py`) and `kit-phase-2` (`early-read-whole-01`, then `review-server-and-checks-02`: a fourth way of excusing code from the linter). Nothing else in the file changes. **If the session is not allowed to edit a file under `.claude/`**, add the sentence and where it goes to `.scratch/kit-phase-5/skill-edits.md`, beside ticket 04's if that is there; the ticket is complete in either form, and `now_what` says which. Spec: `.scratch/kit-phase-5/spec.md`, "A fix's test".

**Blocked by:** 04

**Status:** done

- [x] Step 7 of the skill says the finding's check covers every place its rule applies, in one sentence, or `skill-edits.md` holds that edit in full
- [x] No other line of the skill file changed in this ticket, and neither brief beside it
- [x] `python3 checks.py` ends green on this ticket's commit

## Comments

The edit took the first form: one sentence added to step 7 of the skill file itself, no `skill-edits.md` entry; I ran `python3 checks.py --quick --pick` on it (green), not the full `python3 checks.py`, so the third box stays open for the hand-over's full run.

The full `python3 checks.py` was green on 21f8a53 and later commits, which carry this ticket's change unaltered; it was not run on a7f82b0 itself.
