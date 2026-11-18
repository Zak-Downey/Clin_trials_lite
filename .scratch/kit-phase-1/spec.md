# Spec: A check outside the session, flaky browser tests shown, real time limits, and a quick run

Status: ready-for-agent

Written from `.scratch/kit-phase-1/brief.md`, which holds the evidence and the reasons in full. The owner asked for the spec and tickets to be written for him, without the planning commands and without an interview, on 18 November 2026. Where this spec names a default, it is a recommendation he has not confirmed line by line: use it, and say so in the hand-over.

## Problem Statement

The owner starts a build, leaves, and decides from one page. Four things about the build loop itself make that page worth less than it should be.

1. **The agent that builds is the only judge of the build.** It runs `python3 checks.py`, it can edit `checks.py`, and nothing runs on a pull request. The owner merges on that session's word alone.
2. **A flaky browser test passes without anyone being told.** A walk that fails when run with the others and passes when run alone ends the run green, and the page never mentions it.
3. **The time limits are not limits.** The unit tests may take 10 minutes and the walks 20, on runs that take about 1.0 and 2.4. A check that hangs or slows fivefold still passes.
4. **Checks are about 40% of build time.** Across the last two builds, 59 of 147 minutes went on check runs, most of it walks run at two window sizes after every ticket and every fix.

These are faults of the loop's own files, not of the product. The same files will be copied back into the starter kit, so the fixes must hold in any product.

## Solution

1. **A check on GitHub.** Every pull request runs `python3 checks.py` in full on GitHub's machine, in a job named `checks`. The owner sees green or red where he merges, and can require it on `main`. The run says in words when a pull request changes a file that judges it.
2. **Flaky browser tests are shown.** The walk runner records which walks were red with the others and green alone. The hand-over page counts them among the things to look at and names them.
3. **Limits that are limits.** The unit tests get 3 minutes and the walks 8, about three times a normal run. A test pins the numbers.
4. **A quick run.** `python3 checks.py --quick` runs every check with the walks at one window size. The run log says a run was quick, the page never counts it as a full run, and the instructions use it after a ticket and after a fix. The run before the testers and reviewers start, the run after the fixes and the hand-over run stay full.

## User Stories

1. As the owner, I want every pull request checked on a machine the building agent cannot touch, so that the result I merge on is not only the agent's own.
2. As the owner, I want the check to start by itself when a pull request opens or changes, so that nobody has to remember to run it.
3. As the owner, I want a draft pull request checked like any other, so that no result is green because nothing ran.
4. As the owner, I want the check to run every check at both window sizes, so that it is never weaker than the run on my Mac.
5. As the owner, I want a newer push to cancel the run before it, so that I never read a result for a commit that has been replaced.
6. As the owner, I want a run that takes too long to be red, so that a hung check cannot sit unnoticed.
7. As the owner, I want to read why a check is red from the pull request page, so that I do not need the code open.
8. As the owner, I want to be told in words when a pull request changes the workflow, `checks.py`, the settings file or `pytest.ini`, or removes a test, so that a change to the judge is never quiet.
9. As the owner, I want the agent to give me the pull request link and say the check is running, so that I wait for it before merging.
10. As the owner, I want `repo.md` to say that a workflow now exists and what GitHub's machine might do differently from my Mac, so that the next agent reads the truth.
11. As the owner, I want a flaky browser test counted on the hand-over page, so that I know the green result had a wobble in it.
12. As the owner, I want each flaky test named in my words, so that I can ask for it to be fixed.
13. As the owner, I want the page to look exactly as it does now when nothing was flaky, so that the new line is a signal and not noise.
14. As the owner, I want a flaky test not to turn the build red for now, and that choice to be one line to change, so that I can tighten it later.
15. As the owner, I want the unit tests and the walks held to about three times their normal time, so that a slow or hung check goes red.
16. As the owner, I want those numbers pinned by a test, so that nobody loosens them by accident.
17. As the owner, I want every instruction that says how long to wait for the checks to agree with the new limits, so that an agent does not give up early or wait too long.
18. As the owner, I want a quick run that tests the pages at one window size, so that the runs in the middle of a build take less time.
19. As the owner, I want the run log to say which runs were quick, so that a later tool can tell them apart.
20. As the owner, I want the page never to treat a quick run as the full run it reports, so that "the last full run passed" stays true.
21. As the owner, I want the run before the testers and reviewers start, the run after the fixes and the hand-over run to stay full, so that nothing I merge on has run at one size only.
22. As the owner, I want the tests of the walk guards to run in a quick run too, so that a quick run cannot hide a broken guard.
23. As the owner, I want measured minutes for a full and a quick run, so that I can see what the change saved.
24. As the owner of the starter kit, I want none of the changed loop files to name anything of this product, so that they can be copied into any other product.

## Implementation Decisions

- **Kit files stay product-neutral.** `checks.py`, `handover.py`, the walk runner and fixtures, the build instructions, the workflow and the "Building" section of `CLAUDE.md` read the same in any product. What is particular to this repo goes in `docs/agents/local/repo.md`.
- **The workflow.** One file, one job named `checks`, on a pull request (opened, pushed to, reopened, marked ready) and by hand. No push trigger, no path filter, no condition that skips a draft. It makes the repo's own `.venv`, installs both requirements files and Chromium with its system packages, and runs `python3 checks.py` with no arguments. Packages and the browser are cached on the two requirements files. A newer run on a branch cancels the older. Time limit 20 minutes. On red, the files under `.checks/` are uploaded with the run. It runs on `ubuntu-latest` with the Python version this repo's `.venv` uses.
- **Its starting point.** `.github/workflows/unit-suites.yml` on the branch `feature/gate-backstop-review` of `~/Projects/personal/software factory` (read it with `git show`). Its shape is kept: one named job, the concurrency block, a time limit, a comment recording measured times. Its draft condition is not kept. Nothing else comes from that build.
- **The notice.** One step of the same job lists, in the run's summary on the pull request, the judging files the pull request changes (`.github/workflows/`, `checks.py`, `.claude/settings.json`, `pytest.ini`) and how many tests it removes. It never fails the run. `pull_request_target` is not used and no second workflow is added: both have security consequences the owner decides.
- **Whose copy runs.** GitHub's documentation is checked for whether a pull request runs the branch's copy of the workflow or `main`'s. The answer and its source go in ticket 03's comments and in the hand-over.
- **Flaky walks are data.** The walk runner writes the names of walks that were red with the others and green alone to a small file of its own, for the run they happened in. `checks.py` still decides red or green by exit code and timeout alone and reads no suite's output. The page reads the file. Whether a flaky walk makes the walk run red is one named constant, off by default.
- **Limits.** `CHECKS` gives `unit` 3 minutes and `walks` 8; `patterns` and `escapes` stay at 1.
- **The quick run.** `--quick` is an option of `checks.py`, not a new check: the list of checks is unchanged. It reaches the walks through the environment, and the walk fixtures use only the first window size when it is set. The run's line in `.checks/runs.jsonl` carries a field saying it was quick. Plain `python3 checks.py` behaves exactly as now.
- **The page and quick runs.** A quick run is never the "full run" the page reports, whatever checks it lists. It still appears in the history of runs.
- **Instructions.** `repo.md` says when a quick run is right and which three runs are always full, and that a change to a file under "Shared client plumbing" gets a full run. `.claude/skills/implement-spec/SKILL.md` is changed to match, and its line on how long to wait for the checks is corrected, in the last ticket.
- **This build runs full checks throughout.** The session running this build runs plain `python3 checks.py` every time, whatever the skill file says once it has been edited.
- **Editing under `.claude/`.** Claude Code can stop for a permission prompt on an edit there. If the session is not allowed to make the edit in the last ticket, the two changes are written out in full in `.scratch/kit-phase-1/skill-edits.md` for the owner to apply, and the ticket is complete in that form.
- **Glossary.** No new domain term.

## Testing Decisions

- **What makes a good test here:** it states what the owner or an agent would observe: a run's result and its log line, what the page prints, what a file says. It never states how.
- **Seams:** the unit suite only. No page of the app changes, so no walk is added or changed and no area in `repo.md` is touched. By the build's own rules that means no exploratory tester, and one reviewer for `server-and-checks`.
- **The workflow** cannot be run from here. A unit test reads its text and holds: one job named `checks`; the pull-request and by-hand triggers and no push trigger; no path filter and no draft condition; `python3 checks.py` run with no check named; the concurrency block. Nothing claims it works on GitHub.
- **Flaky walks** are tested with hand-made records and a fake run, as the page's tests already are. No walk is made flaky on purpose.
- **Limits** are pinned in the test that already pins the list of checks.
- **The quick run** is tested by what it runs and what it logs, with stand-in check commands as `tests/test_checks.py` already uses, and by a page test that a quick run after a full one does not replace it.
- **Every new test is seen red first.**

## Out of Scope

- A pre-push hook, new deny lines in `.claude/settings.json`, and any other guard.
- A linter, line ceilings on the instruction files, and a budget for new tests.
- Choosing which tests to run from what a change touched.
- One committed line per build, and a script that breaks the app on purpose.
- Protecting `main` on GitHub: that is the owner's step, after the first run.
- Copying the changed files back into the starter kit: a separate step after this build is merged.
- The larger factory's gate, ticket parser, merge machinery, build-log audit, role files, map and dashboard. If a ticket seems to need one, it is left not done and named first in `now_what`.

## Further Notes

**The brief and the tickets.** The brief suggests nine tickets; there are ten, because the edit to the skill file is a ticket of its own and comes last. Where the two differ, the tickets stand.

**Size.** Each part is one file or a few dozen lines. If the build passes about 400 lines of new code outside tests, `now_what` says so and why. No new dependency.

**Defaults used unless the owner says otherwise.** GitHub time limit 20 minutes, tightened after the first timed run. A flaky walk is shown and counted, not red. Limits of 3 and 8 minutes. `ubuntu-latest`. The Python version of this repo's `.venv`. The option is named `--quick`.

**What `now_what` carries, in this order,** beyond what the page computes for itself:

1. The owner's steps for the first run on GitHub, as short numbered lines: accept the build and open the pull request; watch the `checks` run and note how long it takes; on GitHub, protect `main` (require the `checks` status check, apply it to administrators, allow no direct push); then merge. A later rehearsal with a test broken on purpose confirms that a red pull request is refused.
2. Whose copy of the workflow GitHub runs on a pull request, and what that means for the notice.
3. The measured minutes for a full run and a quick run.
4. Whether the skill file was edited or the edits were left in `skill-edits.md`.
5. Each default above that was used, and anything in the brief or this spec found to be wrong.
