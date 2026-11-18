# 08: The agent cannot merge a pull request

**What to build:** One line, `Bash(gh pr merge*)`, joins the deny list in `.claude/settings.json`, after the lines that refuse a push to `main`. Nothing else in the file changes. The "CI" section of `docs/agents/local/repo.md` says that merging is the owner's and that the settings refuse `gh pr merge`, in one sentence, without claiming it stops any other way of merging. **If the session is not allowed to edit a file under `.claude/`** (the edit is refused, or stops for an approval nobody is there to give), do not wait and do not try another way round: write the change out in full, the line and where it goes, in `.scratch/kit-phase-2/settings-edit.md` for the owner to apply, and word the sentence in `repo.md` so that it is true either way. The ticket is complete in either form, and `now_what` says which. Spec: `.scratch/kit-phase-2/spec.md`, "The refusal" and "Editing under `.claude/`".

**Blocked by:** 07

**Status:** done

- [x] `.claude/settings.json` refuses `gh pr merge` and is otherwise unchanged and still valid JSON, or `settings-edit.md` holds the edit in full
- [x] `repo.md` says merging is the owner's, in a sentence that is true whichever form the ticket took
- [x] No other file under `.claude/` changed
- [x] `python3 checks.py` ends green on this ticket's commit

## Comments

The ticket took the first form: the edit to `.claude/settings.json` was made directly and was not refused, so no `settings-edit.md` was written. The deny list gains one line, `"Bash(gh pr merge*)",`, right after `"Bash(git push*--mirror*)",`; nothing else in the file changed and `python3 -m json.tool` reads it. `repo.md`'s "CI" section gains a "Merging" line: merging is the owner's, the settings refuse `gh pr merge`, and that refusal stops that command only. A new unit test, `tests/test_settings.py::test_the_settings_refuse_gh_pr_merge_after_the_push_refusals`, was seen red before the edit and green after. No other file under `.claude/` changed. `python3 checks.py` ran on the working tree that became this commit and ended green: lint, patterns, escapes, unit and walks all green, 3.7 min.
