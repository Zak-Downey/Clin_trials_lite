# 04: The instructions say the check exists

**What to build:** `CLAUDE.md`, under "When the owner accepts a build", says that after opening the pull request the agent gives the link and says the `checks` run has started on GitHub; it does not call the build safe to merge. `docs/agents/local/repo.md` no longer says there are no workflows: its CI section names the workflow, when it runs and its time limit. Its Stand-ins table gains a row: GitHub's Linux machine stands in for the owner's Mac, with what could differ and what, if anything, checks that. The sentence in `CLAUDE.md` names nothing of this product. Spec: `.scratch/kit-phase-1/spec.md`, user stories 9 and 10.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] `CLAUDE.md` tells the agent to give the pull request link and say the check is running, and not to call the build safe to merge
- [ ] `repo.md`'s CI section describes the workflow and no longer says nothing runs on a pull request
- [ ] The Stand-ins table has a row for GitHub's machine, with its fidelity check or "None" and why
- [ ] A unit test holds that `repo.md` names the workflow file that exists, so the two cannot drift apart

## Comments
