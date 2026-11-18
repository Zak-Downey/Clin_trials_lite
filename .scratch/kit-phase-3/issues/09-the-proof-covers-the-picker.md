# 09: The proof covers the picker

**What to build:** `python3 prove.py --pick` proves that picking does not hide a real change. For each break in the list that is proved by a test, it makes the change in the copy and then runs `python3 checks.py --quick --pick` for that test's check (`unit` or `walks`) in place of naming the test: the result must be red. The run is a quick one so that it fits the proof's two-minute limit for each run; a pick that cannot finish inside the limit is reported as that, never as hidden or caught. The copy carries what the picker needs to pick as it would in the working folder (the base from the run log, and the unit record), or the pick is everything and proves nothing. Each printed line says how many tests the pick ran out of how many, and a break whose pick ran everything is reported as "caught, but nothing was picked", so it is not mistaken for proof of picking. It ends 1 when any break was hidden. Breaks proved by a check (`lint`, `patterns`, `escapes`) are left to plain `python3 prove.py`, which is unchanged. **A break the picker hides is a finding:** fix the map or the rule, never the list of breaks; if it cannot be fixed in this ticket, name it first in `now_what` and say that `--pick` should not be used until it is. Run it once for real here. `repo.md`'s line for the proof says when to run this form: after a change to the map or the picker. Spec: `.scratch/kit-phase-3/spec.md`, "Proof".

**Blocked by:** 07

**Status:** ready-for-agent

- [ ] Red first, on a small hand-made repo in a temporary folder: a break whose test the pick includes is reported caught with its count; a break the pick leaves out is reported hidden and the command ends 1; a break whose pick ran everything is reported as such
- [ ] `python3 prove.py --pick` ends 0 on this repo's list, with at least one unit break and at least three walk breaks caught by a pick smaller than the whole; its printed lines and minutes are in the comments
- [ ] Plain `python3 prove.py` prints and ends as it did before this ticket
- [ ] `python3 checks.py` ends green on this ticket's commit

## Comments
