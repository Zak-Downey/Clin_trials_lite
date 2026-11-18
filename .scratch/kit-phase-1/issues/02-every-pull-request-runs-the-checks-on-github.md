# 02: Every pull request runs the checks on GitHub

**What to build:** A workflow file that runs `python3 checks.py` in full on GitHub's machine for every pull request, in one job named `checks`. It runs when a pull request is opened, pushed to, reopened or marked ready, and by hand; it has no push trigger, no path filter, and nothing that skips a draft. The job makes the repo's own `.venv`, installs both requirements files and Chromium with its system packages, caches the packages and the browser on the two requirements files, and runs every check with the walks at both window sizes. A newer run on the same branch cancels the older one. The job has a 20-minute limit, and on red the files under `.checks/` are uploaded with the run. Start from `.github/workflows/unit-suites.yml` on the branch `feature/gate-backstop-review` of `~/Projects/personal/software factory`, keeping its shape and not its draft condition. The file names nothing of this product. Spec: `.scratch/kit-phase-1/spec.md`, Solution 1 and "The workflow".

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Red first: a unit test reads `.github/workflows/checks.yml` and fails until it has one job named `checks`
- [x] The test holds the triggers: pull request (opened, pushed to, reopened, marked ready) and by hand, and no push trigger
- [x] The test holds that there is no path filter and no condition that skips a draft
- [x] The test holds that `python3 checks.py` is run with no check named
- [x] The test holds the block that cancels an older run on the same branch
- [x] The file sets a 20-minute limit, caches on the two requirements files, and uploads `.checks/` when the run is red
- [x] A comment at the top of the file says why it is shaped as it is and leaves a place for the first measured run time
- [x] Nothing in the file or the test names this product

## Comments
