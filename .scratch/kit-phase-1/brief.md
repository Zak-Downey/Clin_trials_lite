# Brief: kit-phase-1

Written on 18 November 2026 for a Claude Code session opened in Clin trials lite. The owner is Zak. He has agreed the direction and asked for a single build; the details below are recommendations he has not confirmed line by line, so where this brief names a default, use it and say so.

**How this is used.** The owner reads this file into the session, then runs `/to-spec`, then `/to-tickets`, then `/implement-spec kit-phase-1` and leaves. This brief is the source for the spec: write the spec from it without an interview, and do not ask him what it already answers.

## What is being built, and why here

Four changes to the build loop's own files: the check runner, the walk runner, the hand-over page and the build instructions. They are kit changes, not product features. They are built in Clin trials lite because the loop's files were proved here, the walk suite is large enough to measure, and the repo is on GitHub.

After the build is merged, the changed kit files are copied back into `starter/` in `~/Projects/personal/software-factory-lite`. That is a separate step and not part of this build. It puts one constraint on every ticket:

- **A kit file names nothing of this product.** `checks.py`, `handover.py`, everything under `walks/` that is not a product walk, `.claude/skills/implement-spec/`, `.github/workflows/checks.yml` and the "Building" section of `CLAUDE.md` must read the same in any product. What is particular to Clin trials lite goes in `docs/agents/local/repo.md`.

No ticket in this build changes an app page.

## The evidence

Measured on 18 November from this repo's two builds on the lite loop (`.checks/runs.jsonl`, `.scratch/*/fates.jsonl`, git):

| Build | Tickets | Build minutes | Full check runs | Minutes in checks | Problems found late | Fixed with a unit test | Fixed with a walk |
|---|---|---|---|---|---|---|---|
| intervention-changes | 2 | 48 | 7 | 24 | 3 | 2 | 1 |
| trial-address-and-port | 4 | 99 | 10 | 35 | 12 | 2 | 10 |
| Both | 6 | 147 | 17 | 59 | 15 | 4 | 11 |

A full run took 3.4 to 3.6 minutes: about 1.0 for the unit tests and 2.4 for the walks. All 39 logged runs were green.

What follows from that, and from the trust audit of the larger factory (`~/Projects/personal/software factory/factory-trust-audit.md`, section 1):

1. **The agent that builds is the only judge of the build.** It runs `checks.py`, it can edit `checks.py`, and nothing runs on a pull request. The audit ranked this gap first. Part 1 closes it.
2. **A flaky walk passes without anyone being told.** `walks/run_walks.py` re-runs a failed walk alone and exits 0 when it passes alone. Part 2 makes that visible.
3. **The time limits are not limits.** `CHECKS` allows 10 and 20 minutes for runs that take 1.0 and 2.4. Part 3 tightens them.
4. **Checks are about 40% of build time.** Most of that is walks, each run at two window sizes after every ticket and every fix. Part 4 halves the walks on the runs in the middle of a build.

## Rules for every ticket

- **Small.** Each part is one file or a few dozen lines. If the whole build passes about 400 lines of new code outside tests, say so in `now_what` and say why.
- **No new dependency.** `pytest`, `playwright` and `pytest-xdist` are what there is.
- **No new instruction sentence where a test can hold the same thing.**
- **The words stay true.** The checks are described in `CLAUDE.md`, `docs/agents/local/repo.md`, `README.md` and the docstring of `checks.py`. A ticket that changes a fact one of them states updates every place, in its own commit.
- **Tests first, and seen red**, as the loop already requires.
- **Do not bring back** the larger factory's gate, ticket parser, merge machinery, build-log audit, role files, map or dashboard. If a ticket seems to need one, leave the ticket not done and say so first in `now_what`.

## Two things this build cannot change about itself

- **The session running this build keeps the instructions it loaded.** Part 4 edits `.claude/skills/implement-spec/SKILL.md`. That edit applies from the next build. During this one, run plain `python3 checks.py` every time, as the loaded instructions say.
- **The new time limits apply at once.** From the ticket that sets them, this build's own runs are held to them. That is intended.

---

## Part 1: a check outside the session

**What must be true when it is done**

1. The repo has `.github/workflows/checks.yml` with one job named `checks`. That name is the status check the owner will require on `main`.
2. It runs on a pull request when it is opened, pushed to, reopened or marked ready, and by hand. There is no push trigger and no path filter of any kind.
3. A draft pull request is checked like any other. No condition lets the job be skipped and still report green.
4. The job makes the repo's own Python (`.venv`), installs `requirements.txt` and `requirements-dev.txt`, installs Chromium with the system packages it needs, and runs `python3 checks.py` with no arguments: every check, walks at both window sizes.
5. The Python packages and the test browser are cached, keyed on the two requirements files.
6. A newer run on the same branch cancels the one before it.
7. The job has a time limit (default 20 minutes, to be tightened once a real run has been timed). A slower run is red. No check is trimmed to fit.
8. When a check is red, the reason can be read from the pull request page: `checks.py` already prints the end of the red check's output, and the files under `.checks/` are uploaded with the run.
9. The run says, in words on the pull request, when the pull request changes a file that judges it (`.github/workflows/`, `checks.py`, `.claude/settings.json`, `pytest.ini`) or removes a test. It lists them. This is a notice, not a failure: such changes can be right, and the owner decides.
10. A unit test holds claims 1 to 4 and 6 against the workflow file's text, since GitHub cannot be run from here.
11. `CLAUDE.md`, under "When the owner accepts a build", says that after opening the pull request the agent gives the link and says the check is running. It does not call the build safe to merge.
12. `repo.md` no longer says there are no workflows. Its Stand-ins table gains a row: GitHub's Linux machine stands in for the owner's Mac, with what could differ.

**Start from**

`.github/workflows/unit-suites.yml` on the branch `feature/gate-backstop-review` of `~/Projects/personal/software factory` (37 lines; read it with `git show`). Keep its shape: one named job, the concurrency block, a time limit, a comment that records measured times. Do not keep its draft condition, which let a skipped run report green. Take nothing else from that build.

**Find out, and put the answer in `now_what`**

Whose copy of the workflow GitHub runs on a pull request: the branch's own or `main`'s. Check GitHub's documentation and say what it means for claim 9. Do not use `pull_request_target`, and do not add a second workflow: both have security consequences the owner should decide.

**What this build cannot prove**

GitHub cannot be run from here. Do not write that the check works. This build's own pull request will be the first one the workflow runs on, so `now_what` gives the owner these steps, in order, as short numbered lines: accept the build and open the pull request; watch the `checks` run on it and note how long it takes; on GitHub, protect `main` (require the `checks` status check, apply it to administrators, allow no direct push); then merge. A later rehearsal with a test broken on purpose confirms that a red pull request is refused.

**Out of scope**

A pre-push hook, new deny lines in `settings.json`.

## Part 2: flaky walks are shown

**What must be true when it is done**

1. A walk that is red when run with the others and green when run alone is recorded, by name, for the run it happened in.
2. `checks.py` still decides red or green by exit code and timeout alone. It does not read a suite's output to do it. Record the flaky walks some other way (for example a small file `run_walks.py` writes beside its output).
3. The hand-over page counts the flaky walks of the build's runs among the things for the owner to look at, and names them under a fold. Its words are the owner's: a browser test that failed when run with the others and passed when run alone.
4. With no flaky walk, the page says nothing new and looks as it does now.
5. By default a flaky walk does not turn the run red. Build it so that changing the default is one line.
6. `repo.md`'s sentence about load-only flakes says where they now show.

**How to prove it**

Unit tests with hand-made records, as `tests/test_handover.py` already does. Do not write a walk that is flaky on purpose.

**Out of scope**

Changing what `run_walks.py` re-runs, or how many times.

## Part 3: time limits that are limits

**What must be true when it is done**

1. `CHECKS` in `checks.py` gives `unit` 3 minutes and `walks` 8. `patterns` and `escapes` stay at 1.
2. The test that pins the list of checks also pins these numbers, so a change to one is deliberate.
3. Every place that tells an agent how long to wait for `checks.py` agrees with the new sum: `repo.md`, `SKILL.md`, and `CLAUDE.md` if it says.
4. `repo.md` says that the limits are a product's own and should be about three times a normal run, so a product that grows raises them on purpose.

**Why these numbers**

About three times the measured run here (1.0 and 2.4 minutes). A walk run with many failures takes longer, because each failure is re-run alone. That is still a red run, and the output file says why.

## Part 4: one window size after each ticket

**What must be true when it is done**

1. `python3 checks.py --quick` runs every check, with the walks at the first window size only (1440 x 900). Plain `python3 checks.py` is unchanged: both sizes.
2. A quick run's line in `.checks/runs.jsonl` says it was quick.
3. The hand-over page never counts a quick run as a full run. Every sentence it prints about the last full run stays true.
4. In `SKILL.md`, the run after each ticket and after each fix is quick. Three runs are always full: the one before the testers and reviewers start, the one after the fixes, and the hand-over run. Change as few words as will do it.
5. A change to any file `repo.md` lists under "Shared client plumbing" still gets a full run.
6. The check on GitHub (part 1) is always full.
7. The tests of the walk guards still run in a quick run.

**Measure, and put the figures in `now_what`**

Minutes for a full run and for a quick run, from real runs in this repo on the build's last commit.

**Why this is safe**

A fault that shows only at the smaller window is found at the next full run, before any tester or reviewer starts, and again at hand-over and on GitHub. Nothing the owner merges on has run at one size only.

**Out of scope**

Choosing which tests to run from what a change touched.

---

## A suggested split into tickets

About nine, in this order. Parts 3 and 1 come first because they are the smallest and the safest; part 4 is last because it changes the loop.

1. Part 3: the limits, the pinned test, the wording.
2. Part 1: the workflow file and the test of its text.
3. Part 1: the notice when a pull request changes a judging file or removes a test.
4. Part 1: `CLAUDE.md` and `repo.md` (claims 11 and 12).
5. Part 2: `run_walks.py` records flaky walks.
6. Part 2: the hand-over page shows them. Blocked by 5.
7. Part 4: the quick option and its line in the run log.
8. Part 4: the hand-over page never counts a quick run as full. Blocked by 7.
9. Part 4: `SKILL.md` and `repo.md` use it. Blocked by 7.

## Defaults used unless the owner says otherwise

| Decision | Default |
|---|---|
| Time limit for the check on GitHub | 20 minutes, tightened after the first timed run |
| Does a flaky walk turn the run red? | No: it is shown and counted |
| Limits for `unit` and `walks` | 3 and 8 minutes |
| Machine the GitHub check runs on | `ubuntu-latest`, with a Stand-ins row for what differs from the Mac |
| Python version on GitHub | The one in this repo's `.venv` |
| Name of the quick option | `--quick` |

## What the hand-over should carry

Beyond what the page computes for itself, `now_what` holds, in this order: the owner's steps for the first run on GitHub and for protecting `main`; the answer on whose copy of the workflow GitHub runs; the measured minutes for a full and a quick run; each default from the table that was used; anything in this brief found to be wrong.

## Later phases: context only, do not build

Know these so this build does not block them.

- **A small guard.** A few more deny lines, and a git pre-push hook that refuses a push unless the last full run in `.checks/runs.jsonl` was green on that commit. This is why part 4 must record quick runs honestly.
- **A linter as a fifth check**, run first.
- **Budgets.** Line ceilings on the instruction files, and a test that holds the prose lists of checks equal to `CHECKS`.
- **One committed line per build.** This is why part 2 must record flaky walks as data.
- **Proof the checks can fail.**
- **Test selection.** Unit tests chosen by what a change reaches, walks chosen from a page map kept as data. The full runs named in part 4 stay full.
