# 03: A pull request that changes its own judge says so

**What to build:** One step in the `checks` job writes a notice to the run's summary on the pull request when the pull request changes a file that judges it (anything under `.github/workflows/`, `checks.py`, `.claude/settings.json`, `pytest.ini`) or removes a test. It lists the files and gives the number of tests removed. It is a notice and never fails the run: such changes can be right, and the owner decides. With nothing to report it says nothing. `pull_request_target` is not used and no second workflow is added. Also find out from GitHub's documentation whose copy of the workflow a pull request runs, the branch's own or `main`'s, and record the answer with its source under Comments below, in one or two plain sentences on what it means for this notice. Spec: `.scratch/kit-phase-1/spec.md`, "The notice" and "Whose copy runs".

**Blocked by:** 02

**Status:** done

- [x] Red first: a unit test fails until the workflow has a step that names the four judging paths
- [x] The step lists each changed judging file and the number of tests removed, in the run's summary
- [x] The step cannot fail the run, and prints nothing when there is nothing to report
- [x] The workflow still has one job and does not use `pull_request_target`
- [x] Comments below say whose copy of the workflow GitHub runs on a pull request, with a link to the documentation, and what that means for the notice

## Comments

**Whose copy runs (from GitHub's documentation, 2026-11-18).** A pull request runs the workflow as it stands on the pull request's own branch, merged with `main`, not `main`'s copy. GitHub's "Events that trigger workflows" page says that for `pull_request` the run's commit is "the last merge commit of the pull request merge branch" (`refs/pull/<number>/merge`), and that `pull_request_target`, by contrast, runs "in the context of the default branch of the base repository"; the "Workflows" page says GitHub looks for workflow files "present in the associated commit SHA or Git ref of the event". Sources: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request and https://docs.github.com/en/actions/concepts/workflows-and-actions/workflows (section "Workflow triggers").

What it means for the notice: a pull request that edits `.github/workflows/checks.yml`, or the notice's own script beside it, is judged by its own edited copy, so it could remove or quiet the notice in the very run that should report it. The notice is therefore something the owner reads, not a guard. Because the script sits under `.github/workflows/`, an edit to it is itself listed as a change to what judges the pull request, as long as the notice still runs. Only `pull_request_target` would run `main`'s copy, and it is not used, as the spec says.

**What "tests removed" counts.** Lines that define a test (`def test_...` or `async def test_...`) taken out of files named `test_*.py` anywhere in the repo, less those put in, never below nought. A deleted test file counts every test in it; a renamed test counts as neither removed nor added. It is compared against the pull request's base (`base...HEAD`); a run started by hand has no base and gets no notice.
