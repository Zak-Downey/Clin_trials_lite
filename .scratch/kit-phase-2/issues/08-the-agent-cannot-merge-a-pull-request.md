# 08: The agent cannot merge a pull request

**What to build:** One line, `Bash(gh pr merge*)`, joins the deny list in `.claude/settings.json`, after the lines that refuse a push to `main`. Nothing else in the file changes. The "CI" section of `docs/agents/local/repo.md` says that merging is the owner's and that the settings refuse `gh pr merge`, in one sentence, without claiming it stops any other way of merging. **If the session is not allowed to edit a file under `.claude/`** (the edit is refused, or stops for an approval nobody is there to give), do not wait and do not try another way round: write the change out in full, the line and where it goes, in `.scratch/kit-phase-2/settings-edit.md` for the owner to apply, and word the sentence in `repo.md` so that it is true either way. The ticket is complete in either form, and `now_what` says which. Spec: `.scratch/kit-phase-2/spec.md`, "The refusal" and "Editing under `.claude/`".

**Blocked by:** 07

**Status:** ready-for-agent

- [ ] `.claude/settings.json` refuses `gh pr merge` and is otherwise unchanged and still valid JSON, or `settings-edit.md` holds the edit in full
- [ ] `repo.md` says merging is the owner's, in a sentence that is true whichever form the ticket took
- [ ] No other file under `.claude/` changed
- [ ] `python3 checks.py` ends green on this ticket's commit

## Comments
