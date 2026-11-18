# 03: A pull request that changes its own judge says so

**What to build:** One step in the `checks` job writes a notice to the run's summary on the pull request when the pull request changes a file that judges it (anything under `.github/workflows/`, `checks.py`, `.claude/settings.json`, `pytest.ini`) or removes a test. It lists the files and gives the number of tests removed. It is a notice and never fails the run: such changes can be right, and the owner decides. With nothing to report it says nothing. `pull_request_target` is not used and no second workflow is added. Also find out from GitHub's documentation whose copy of the workflow a pull request runs, the branch's own or `main`'s, and record the answer with its source under Comments below, in one or two plain sentences on what it means for this notice. Spec: `.scratch/kit-phase-1/spec.md`, "The notice" and "Whose copy runs".

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Red first: a unit test fails until the workflow has a step that names the four judging paths
- [ ] The step lists each changed judging file and the number of tests removed, in the run's summary
- [ ] The step cannot fail the run, and prints nothing when there is nothing to report
- [ ] The workflow still has one job and does not use `pull_request_target`
- [ ] Comments below say whose copy of the workflow GitHub runs on a pull request, with a link to the documentation, and what that means for the notice

## Comments
