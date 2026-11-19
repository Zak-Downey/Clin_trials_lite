# 05: The walks a change can reach

**What to build:** Two functions, kit files that name nothing of this product. The first says what changed: the files that differ between a base commit and the working folder, uncommitted and untracked files included, with a renamed file counted under both names. The base is the commit of the last green run in `.checks/runs.jsonl` that ran every check, on a clean folder, at a commit this branch still contains; with none, the point where the branch left `main`; when neither can be found it says it cannot tell, and why. The second is pure: given the changed files and a map, it returns the walk files to run and the reason in one sentence. A changed file in `shared`, or one the map places nowhere, or "cannot tell": every walk. Otherwise the walk files of each area a changed file belongs to, any changed walk file itself, and `always`. Changed files that are all in `none`, and no changed files at all, give `always` alone, and the reason says so. It reads no test output and uses no model. Spec: `.scratch/kit-phase-3/spec.md`, "What changed" and "Picking browser tests".

**Blocked by:** 04

**Status:** done

- [x] Red first, as a table on a hand-made map: a file of one area, files of two areas, a shared file, a file placed nowhere, a new file, a deleted file, a renamed file, a changed walk file, only-docs changes, nothing changed, and "cannot tell"; each row gives the walk files and a reason that names the file or area behind it
- [x] Red first, on small repos made in a temporary folder: the base is the last green run of every check on a clean folder that the branch contains; a red run, a run of one named check, a run on a dirty folder and a run at a commit the branch no longer contains do not move it; with no such run it is where the branch left `main`
- [x] The pick is never empty: `always` is in every answer
- [x] `python3 checks.py` ends green on this ticket's commit

## Comments

**Built.** `picker.py` (kit file, names nothing of this product; 96 lines for the picker and the base together):
- `walks(changed, the_map, every, walk_files=WALKS) -> (list[str], str)`: pure. `changed` is the changed files or `None` ("cannot tell"); `every` is every walk file there is. Returns the sorted walk files to run and the reason in one sentence. `None`, a file in `shared` or a file the map places nowhere (a new file the map does not place yet included): every walk ("every walk: `app/shell.js` is shared", "every walk: the map places `lib/util.py` nowhere", "every walk: cannot tell what changed"). Otherwise each touched area's walks, each changed walk file that still exists, and `always` ("Page A, because `app/page_a.js` changed; the changed walk file `walks/test_x.py`; and the walks that always run"). Only `none` files, a deleted walk file, or nothing changed: `always` alone, and the reason says so. `always` is in every answer.
- `changed(root, main="main") -> (list[str] | None, str)`: the files that differ between the base and the working folder (`git diff --no-renames <base>` plus untracked files git does not ignore), so a rename counts under both names and a deleted file is listed; `None` with the reason when it cannot tell. The string says the base in words.
- `base(root, main="main", log=".checks/runs.jsonl") -> (str | None, str)`: the full hash of the last run in the log that is green, ran every check, on a clean folder, not picked, at a commit the checked-out branch contains; with none, `git merge-base main HEAD`; with neither, `None` and why.

**A new log field.** `checks.py` now writes `"every": true` on a run's line when every check was asked for (no names, or all of them named), `false` otherwise; `tests/test_checks.py::test_a_run_line_says_whether_the_run_asked_for_every_check` holds it. Older lines have no `every`, so they never count as a base: until this branch's first whole green run with the field, the base is where the branch left `main`. A line with `"picked": true` (ticket 06 adds the field) is never a base either.

**Tests.** `tests/test_picker.py`: a table of 12 rows on a hand-made map (one area, two areas, a deleted area file, a rename under both names, a changed walk file, a deleted walk file, only docs, nothing changed, a shared file, a file placed nowhere, a new file, cannot tell), each row seen red first; the "never empty" check over the same rows, seen red against a picker made to drop `always`; on small git repos, the base moving to the last whole green run, five kinds of run that do not move it (red, one named check, dirty folder, picked, a commit the branch no longer has), the fall-back to where the branch left `main`, "cannot tell" with its reason, and what changed (uncommitted, untracked, deleted, renamed). Each seen red first.

**Checks.** Full `python3 checks.py` green before the commit (2.8 min: unit 0.2, walks 2.6).

**The map.** `picker.py` went into `shared`, beside `checks.py`, out of doubt: it decides which walks a picked run runs.

