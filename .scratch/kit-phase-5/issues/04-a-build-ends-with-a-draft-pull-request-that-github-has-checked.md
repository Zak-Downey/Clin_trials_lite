# 04: A build ends with a draft pull request that GitHub has checked

**What to build:** Three changes that together make GitHub run the checks once for a build, before the owner sees the page.

**The skill's last step** (`.claude/skills/implement-spec/SKILL.md`), with as few changed words as will do it. After the hand-over run of `python3 checks.py` is green and before `python3 handover.py <feature>`: push the feature branch (`git push -u origin feature/<feature>`); open a draft pull request for it (`gh pr create --draft`), its text saying in one line that the owner has not yet accepted it; wait for the `checks` run on that pull request to end, in the background, since a run has taken 6 to 17 minutes. Green: go on. Red: read from the run which check failed, fix it by the skill's own rule for a red check, run the local checks and push, which starts the run again; wait once more; red a second time: go on, and say it first in `now_what`. If the push or the draft cannot be made (no network, not signed in, a plan without drafts), go on and say that first in `now_what`. The sentence that forbids pushing is narrowed to what still holds: the builder never marks the draft ready, never pushes to `main` and never merges.

**`CLAUDE.md`'s line on what happens when the owner accepts.** The session marks the draft ready (`gh pr ready`) and gives the link; the owner merges on GitHub; no run starts, so there is nothing to wait for; if the page said GitHub had not passed, the session says so again with the link. When the owner refuses, the session closes the draft and says so, and deletes no branch.

**The workflow.** `ready_for_review` leaves the trigger of `.github/workflows/checks.yml`, so marking a draft ready starts no run; the test that pins the trigger (`tests/test_workflow.py`) is changed on purpose, and its name with it. A draft is still checked when it is opened and at every push, and starting the workflow by hand stays. Nothing else in the workflow changes: the job's name, its steps and its limit of 20 minutes. Its opening lines say when it runs now, and give measured times in place of "not yet": the four runs the retro looked up took 6 to 17 minutes. `docs/agents/local/repo.md`'s "Workflows" line says the same, and that a build opens the draft before the hand-over.

**If the session is not allowed to edit a file under `.claude/`**, do not wait and do not try another way round: write the skill's changes out in full, old words and new, in `.scratch/kit-phase-5/skill-edits.md`; the ticket is complete in that form, and `now_what` says which. Spec: `.scratch/kit-phase-5/spec.md`, "The last step of a build", "When the owner accepts or refuses" and "One run for a commit".

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] Red first: the test that pins the workflow's trigger fails until it is opened, pushed to and reopened, with no run on being marked ready, and still by hand and never on a push
- [ ] The skill's last step pushes the branch, opens the draft, waits, and says what to do on green, on red, on red twice and when it cannot be made, or `skill-edits.md` holds that edit in full
- [ ] The skill and `CLAUDE.md` agree: the builder opens only a draft, and marking it ready, `main` and the merge wait for the owner's yes; no sentence still says the builder never pushes or opens no pull request
- [ ] The workflow's job name, steps and limit are unchanged and its opening lines give measured times; `repo.md` agrees; `python3 checks.py` ends green on this ticket's commit

## Comments
