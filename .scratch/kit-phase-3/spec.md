# Spec: Faster checks, and running only the tests a change can reach

Status: ready-for-agent

Written on 18 November 2026, while `kit-phase-2` was being built, and checked against what that build made once it was merged (`6ea354a`). The owner asked for the kit to cope with a product whose tests keep growing, agreed the plan in conversation, and asked for the spec and tickets to be written for him, without the planning commands and without an interview. Where this spec names a default, it is a recommendation he has not confirmed line by line: use it, and say so in the hand-over.

The figures below were measured on this repo at `1d828fa`. The run log and the build records are from the owner's Mac. The timings of single tests were taken on a copy on a Linux machine with Python 3.10, so their seconds will differ on the Mac and their proportions should not.

## Problem Statement

The owner starts a build, leaves, and decides from one page. The build waits on its checks more than on anything else, and the wait grows with every test a feature adds.

1. **Checks are about half of a build.** In `kit-phase-1`, 22 check runs took 68 of about 130 minutes: 46 in the browser tests and 22 in the unit tests.
2. **Most of the unit suite's time is not testing.** Of 86 seconds, 13 are the tests. 49 are the test server waiting half a second to stop, 97 times. The suite also runs on one processor.
3. **Every run after a ticket runs everything.** A ticket that changes one page runs all 42 files of browser tests and all 662 unit tests, whatever it touched.
4. **Nothing says which tests a change can reach.** The lists "Areas" and "Shared client plumbing" are prose in `repo.md`, read by agents and by no program.

These are faults of the loop's own files, not of the product. The same files will be copied back into the starter kit, so they must hold in any product.

## Solution

1. **Faster with nothing skipped.** The test server stops at once, and the unit tests run on several processors. On the copy this took the unit suite from 86 seconds to 43, then to about 10.
2. **A map of the pages, as data.** One file says which source files belong to which page area, which browser tests cover each area, and which files every page shares.
3. **A picked run.** `python3 checks.py --pick` runs the browser tests of the areas a change touched, and the unit tests that ran the code that changed. Whatever it cannot place runs everything, and it says why in one line.
4. **Full runs where they matter.** The run before the testers and reviewers start, the run after the fixes, the hand-over run and the check on GitHub are never picked.
5. **Proof.** The deliberate breaks of `prove.py` are run through the picker: each must still go red.

## User Stories

1. As the owner, I want the unit tests to take seconds, so that a build is not waiting on a test server to shut.
2. As the owner, I want a test that holds the fix, so that the half-second wait cannot come back unnoticed.
3. As the owner, I want the unit tests to use the processors the machine has, so that the suite's time grows slower than its size.
4. As the owner, I want to know where the browser tests' time goes, so that the next speed-up is chosen from a measurement.
5. As the owner, I want one file a program reads to say which tests cover which pages, so that the lists in prose cannot drift from the truth.
6. As the owner, I want a new source file or a new browser test that the map does not place to turn the ordinary checks red, so that the map is kept current.
7. As the owner, I want the run after a ticket to run only what the ticket's change can reach, so that a small change gets a quick answer.
8. As the owner, I want any change the picker cannot place to run everything, so that a gap in the map costs time and never a missed test.
9. As the owner, I want every picked run to say what it ran, out of how many, and why, so that I can see it was not empty.
10. As the owner, I want a picked run that would run nothing to run a fixed small set and say so, so that green never means nothing ran.
11. As the owner, I want the page never to count a picked run as a full run, so that "the last full run passed" stays true.
12. As the owner, I want the check on GitHub never to pick, so that the judge outside the session is always whole.
13. As the owner, I want the picker proved with the same deliberate breaks as the checks, so that I know it does not hide a real change.
14. As the owner, I want to turn picking off with one word in the instructions, so that I can go back to whole runs if it misleads.
15. As the owner of the starter kit, I want the picker's code to name nothing of this product, so that it can be copied into any other product.

## Implementation Decisions

- **Kit files stay product-neutral.** `checks.py`, `handover.py`, `prove.py`, the walk runner, the picker and their tests read the same in any product. What is particular to this repo goes in `docs/agents/local/`: `repo.md`, and the map.
- **The test server.** The in-process server of the unit suite's `api` fixture is started so that stopping it takes a few hundredths of a second, not up to half a second. A unit test holds that starting and stopping it takes under 0.2 seconds.
- **Unit tests in parallel.** The `unit` check runs with `pytest-xdist`, which the repo already has for the browser tests, using the processors the machine has. One test fails beside others today (`test_this_project_s_programs_still_listening_are_found_on_this_computer_with_their_ports_and_start_times` reads the machine's listening programs): it is made to hold in parallel without weakening what it asserts. Any other test found to depend on running alone is fixed the same way, never skipped.
- **Limits.** The time limits in `CHECKS` stay as they are in this build. `now_what` gives the new timings so the owner can tighten them.
- **The browser tests are measured, not changed.** The time of each walk file in one full run goes into the ticket's comments and a short table in `repo.md`. A cheap fix that the measurement shows is named in `now_what`, not made here.
- **The map.** `docs/agents/local/walk-map.json`, the product's own. It holds: `shared` (files every page depends on: a change to one runs every walk), `always` (walk files that run in every picked run: the walk-guard tests and the acceptance walk), `areas` (each with a name, the source files that belong to it, and the walk files that cover it), and `none` (files that reach no walk: records, docs, the unit tests). Files are given as paths or glob patterns.
- **The map is kept current by a cheap test.** It runs in the unit suite, so in every `python3 checks.py`. It holds that every walk file is in `always` or at least one area; every file git tracks is placed by `shared`, an area or `none`; every pattern matches at least one file; and no walk file is listed that does not exist. The prose lists "Areas" and "Shared client plumbing" in `repo.md` give way to one line that points to the map.
- **What changed.** The files that differ between a base commit and the working folder, uncommitted and untracked files included. The base is the commit of the last green run in `.checks/runs.jsonl` that ran every check, on a clean folder, at a commit this branch still contains; when there is none, the point where the branch left `main`; when that cannot be found, the picker cannot tell.
- **Picking browser tests.** A changed file in `shared`, or placed nowhere, or a failure to tell what changed: every walk. Otherwise the walk files of every area a changed file belongs to, the changed walk files themselves, and `always`. Changed files that are all in `none` pick `always` alone. The pick is a pure function of the changed files and the map, with no reading of test output and no model.
- **Picking unit tests.** `pytest-testmon`, pinned as `pytest-testmon==2.2.0` in `requirements-dev.txt`. It records which test ran which code and selects the tests a change reaches. It sees only Python: tried on this repo, a change to one function ran 12 of 662 tests, and a change to a script or a data file ran none. So it selects only when every changed file is a Python file; any other changed file outside `.scratch/` runs the whole unit suite. A full run refreshes its record without deselecting anything. Its record file is git-ignored, and without one it runs everything. It works beside `pytest-xdist` (tried: yes). It needs pytest's cache, so the `unit` command no longer switches the cache off; the cache folder is already git-ignored.
- **The option.** `python3 checks.py --pick`. It combines with `--quick` and with naming checks. `lint`, `patterns` and `escapes` always run whole. It reaches the walk runner and the unit command as `--quick` does today. Plain `python3 checks.py` behaves exactly as now, and so does `--quick` alone.
- **What a picked run says.** One printed line per picked check: how many it ran, out of how many, and the reason in words ("3 of 42 walk files: Summary, because `webapp/static/views/summary.js` changed"; "every walk: `storage.py` is shared"). The run's line in `.checks/runs.jsonl` carries `"picked": true` or `false`, the base, and those reasons.
- **Full runs.** A picked run is never the full run the hand-over page reports, whatever it happened to run. The workflow never passes `--pick`, and a test holds that.
- **Proof.** `python3 prove.py --pick` makes each break that is proved by a test, then runs `python3 checks.py --pick` for that test's check in the copy, in place of naming the test. The result must be red. The line for each break says how many tests the pick ran, so a pick that ran everything is not mistaken for proof of picking. The copy carries what the picker needs to pick (the run log's base and the unit record). The picked run is a quick one (`--quick --pick`), so that it fits the proof's two-minute limit for each run; a pick that cannot finish inside the limit is reported as that, never as hidden or caught.
- **Instructions.** `repo.md` says what a picked run is, when it is right (after a ticket and after a fix) and which runs are always full. `.claude/skills/implement-spec/SKILL.md` asks for `python3 checks.py --quick --pick` after a ticket and after a fix, in the last ticket. To turn picking off, the owner removes `--pick` from that line.
- **This build runs without picking.** The session running this build runs its checks as the skill file says when the build starts, whatever the file says once it has been edited.
- **Editing under `.claude/`.** If the session is not allowed to make the edit in the last ticket, the change is written out in full in `.scratch/kit-phase-3/skill-edits.md` for the owner to apply, and the ticket is complete in that form.
- **Glossary.** No new domain term.

## Testing Decisions

- **What makes a good test here:** it states what the owner or an agent would observe: what a run ran and logged, what a command prints and how it ends, what a file says. It never states how.
- **Seams:** the unit suite only. No page of the app changes, so no walk is added or changed. By the build's own rules that means no exploratory tester, and one reviewer for `server-and-checks`.
- **The picker for walks** is a pure function and is tested as a table: one row per rule above, on a hand-made map and hand-made lists of changed files. The rows include a shared file, a file placed nowhere, a new file, a deleted file, a renamed file, a changed walk file, only-docs changes, and no base.
- **The base** is tested on small repos made in a temporary folder with hand-made run logs.
- **`--pick`** is tested by what it runs and what it logs, with stand-in check commands as `tests/test_checks.py` already uses.
- **The unit picker** is not tested by re-testing `pytest-testmon`. The tests hold what this repo decides: the version is pinned to one exact version; a changed file that is not Python runs the whole suite; a full run deselects nothing.
- **The proof** is run once for real in ticket 09, and its output is kept in the ticket's comments.
- **Every new test is seen red first.**

## Out of Scope

- A picker of the kit's own that traces which function each test ran. The larger factory built one (about 1,220 lines); its rules are taken here and its code is not.
- Choosing tests with a trained model, or ordering them by likelihood of failure.
- Recording which script each browser test ran. Every page loads every script today, so a map is used.
- Tightening the time limits, and line ceilings on the instruction files.
- Picking on GitHub, and running the proof there.
- Splitting the browser tests across more workers or machines.
- One committed line per build.
- Copying the changed files back into the starter kit: a separate step after this build is merged.
- The larger factory's gate, guard, ticket parser and dashboard. If a ticket seems to need one, it is left not done and named first in `now_what`.

## Further Notes

**Three rules from the larger factory's picker,** each from a fault the trust audit found in it. It never selects nothing without saying so. A new file widens the run. Its proof shows the picker works, not that the tests are strong, so the plain `python3 prove.py` stays.

**Size.** The picker for walks and the base should be about 150 lines together. If the build passes about 500 lines of new code outside tests, `now_what` says so and why. One new dependency: `pytest-testmon`, for development only.

**Defaults used unless the owner says otherwise.** The option is named `--pick`. The map is `docs/agents/local/walk-map.json`. `pytest-testmon` 2.2.0. The unit tests use as many workers as the machine has processors. The limits in `CHECKS` are unchanged. Picking is used after a ticket and after a fix only.

**What `now_what` carries, in this order,** beyond what the page computes for itself:

1. Any break that the picker hid in ticket 09, and what was done about it.
2. The measured minutes: the unit suite before, after the server fix and in parallel; a full run and a quick run before and after; a picked run after a one-page change and after a one-function change.
3. The slowest browser tests, and any cheap fix the measurement shows.
4. Every test changed so that it holds in parallel, and how.
5. Whether the skill file was edited or the edit was left in `skill-edits.md`.
6. Each default above that was used, and anything in this spec found to be wrong.
