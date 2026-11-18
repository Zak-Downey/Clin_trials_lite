# 05: The walks a change can reach

**What to build:** Two functions, kit files that name nothing of this product. The first says what changed: the files that differ between a base commit and the working folder, uncommitted and untracked files included, with a renamed file counted under both names. The base is the commit of the last green run in `.checks/runs.jsonl` that ran every check, on a clean folder, at a commit this branch still contains; with none, the point where the branch left `main`; when neither can be found it says it cannot tell, and why. The second is pure: given the changed files and a map, it returns the walk files to run and the reason in one sentence. A changed file in `shared`, or one the map places nowhere, or "cannot tell": every walk. Otherwise the walk files of each area a changed file belongs to, any changed walk file itself, and `always`. Changed files that are all in `none`, and no changed files at all, give `always` alone, and the reason says so. It reads no test output and uses no model. Spec: `.scratch/kit-phase-3/spec.md`, "What changed" and "Picking browser tests".

**Blocked by:** 04

**Status:** ready-for-agent

- [ ] Red first, as a table on a hand-made map: a file of one area, files of two areas, a shared file, a file placed nowhere, a new file, a deleted file, a renamed file, a changed walk file, only-docs changes, nothing changed, and "cannot tell"; each row gives the walk files and a reason that names the file or area behind it
- [ ] Red first, on small repos made in a temporary folder: the base is the last green run of every check on a clean folder that the branch contains; a red run, a run of one named check, a run on a dirty folder and a run at a commit the branch no longer contains do not move it; with no such run it is where the branch left `main`
- [ ] The pick is never empty: `always` is in every answer
- [ ] `python3 checks.py` ends green on this ticket's commit

## Comments
