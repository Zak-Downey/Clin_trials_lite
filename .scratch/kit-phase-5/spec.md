# Spec: What the first retro found: Linux before the hand-over, a wobbling test, and three rules

Status: ready-for-agent

Written on 19 November 2026, after the first retro, which read the records of `kit-phase-1` to `kit-phase-4`. The retro proposed five changes and one removal. The owner took four as proposed, changed one, and refused the removal. He asked for the spec and tickets to be written for him, without the planning commands and without an interview. Where this spec names a default, it is a recommendation he has not confirmed line by line: use it, and say so in the hand-over.

## Problem Statement

The owner starts a build, leaves, and decides from one page. The records of four builds show five ways that page has been wrong, or will be.

1. **Linux is first seen after the owner has decided.** `kit-phase-1` and `kit-phase-2` passed every check on the Mac and failed on their first run on GitHub (runs 44377053041 and 44411871654). The defect log holds four faults that showed only on Linux (E-038 to E-041): a font, two pages read before they had drawn, and `ps` cutting a long command line. The builder cannot see a Linux result: Docker is refused to it, and it may not push.
2. **One browser test wobbles, and nothing makes anyone fix it.** `test_walk_the_action_bar_states_its_scope_stays_visible_and_leaves_the_last_change_clear` failed beside the others and passed alone in `kit-phase-2` (at 1024 x 768) and again in `kit-phase-4` (at 1440 x 900). A wobble is shown on the page and fails nothing. E-039 and E-040 were the same kind of fault, and on GitHub's slower machine they failed outright.
3. **A fix's test covers the one place the finding named.** Twice a second review round found the same fault somewhere else: this product's words in a second part of `handover.py` (`kit-phase-1`), and a fourth way round the linter after three were closed (`kit-phase-2`).
4. **A reason that no test holds is now lost.** `kit-phase-4` removed every comment. Four of them were the only record of why a line had to stay as it was, and no test failed when the line was changed. With comments refused, a builder's reason has nowhere to go unless it becomes a test.
5. **Code that nothing uses is still there.** The same review found three settings in `display.py` that no page has used for some time.

## Solution

1. **The checks run on GitHub before the hand-over, once.** As its last step before the page, the builder pushes the feature branch and opens a draft pull request. GitHub runs the checks on it, and the builder waits. A red run is treated like any red check: fixed, or left and said first. When the owner accepts, the draft is marked ready and nothing runs again: that commit is already checked. GitHub does not let a draft be merged, so the owner's yes is still what lets the work in.
2. **The page says what GitHub's machine found.** One line, computed by asking GitHub about the build's last commit: passed, failed, still running, never run, or could not ask. It gives the draft pull request's address when there is one.
3. **The wobbling test is fixed, and a wobble now fails the browser tests.** The one known wobble is fixed first. Then the setting that already exists is switched on, so a test that fails beside the others and passes alone turns the `walks` check red.
4. **Three rules, each one sentence.** A fix's test covers every place its rule covers. A reason the code depends on is held by a test. The repo's notes say how GitHub's machine differs.
5. **The unused settings go.**

## User Stories

1. As the owner, I want the checks run on GitHub's machine before I am shown the page, so that I do not accept a build and then watch it fail.
2. As the owner, I want a failure there fixed by the builder like any other, so that I am not the one who starts the job again.
3. As the owner, I want the page to say what GitHub found for the exact commit I am judging, so that I know before I say yes.
4. As the owner, I want the page to say so plainly when GitHub was not asked or had not finished, so that silence is never read as a pass.
5. As the owner, I want GitHub to run the checks once for a commit and not again when I accept, so that I do not wait twice for the same answer.
6. As the owner, I want nothing to reach `main` until I have said yes, so that a pull request opened before I judged cannot be merged by anyone, the agent included.
7. As the owner, I want the one test known to wobble fixed, so that it stops being noise on every page.
8. As the owner, I want a test that wobbles to fail the build, so that the builder fixes the race while it still has the code open.
9. As the owner, I want the test written for a finding to cover every place the same rule applies, so that the re-check does not find its twin.
10. As the owner, I want a reviewer to ask of an odd-looking line what would fail if it changed, so that a reason which used to be a comment becomes a test.
11. As the owner, I want a builder told in one line how GitHub's machine differs from mine, so that it writes a browser test that holds on both.
12. As the owner, I want settings that nothing uses removed, so that the next agent does not copy or maintain them.
13. As the owner, I want this build itself to end by the new last step, so that the step is tried before another build relies on it.
14. As the owner of the starter kit, I want the changed loop files to name nothing of this product, so that they can be copied into any other product.

## Implementation Decisions

- **Kit files stay product-neutral.** `handover.py`, `walks/run_walks.py`, the build instructions, the workflow, the "Building" section of `CLAUDE.md` and their tests read the same in any product. What is particular to this repo goes in `docs/agents/local/repo.md`, `CODING_STANDARDS.md` and the app's own files.
- **The wobbling test.** It is a walk of the trial page that reads positions on the screen straight after the page opens and after each scroll. Find what it reads too early and make it wait for that, as E-039 and E-040 were fixed: a walk waits for the thing it is about to read. Its assertions keep their meaning. It is shown red first by slowing what it races, in a new walk or a changed one; running it many times and seeing green is not proof.
- **A wobble is red.** `FLAKY_IS_RED` in `walks/run_walks.py` becomes true: a walk that is red beside the others and green alone ends the `walks` check red, and the runner's printed line names it and says it wobbled. The record `flaky.jsonl` and the page's list of wobbling tests stay as they are. This is on trial: the next retro reads how many runs it turned red and whether each was a real race.
- **Asking GitHub.** `handover.py` asks GitHub, through the `gh` command, for the runs of the `checks` workflow on the build's last commit, and says one of five things on the page, in the owner's words: it passed (with the run's number and how long it took), it failed (with the run's address), it is still running, no run was made for this commit, or GitHub could not be asked (and why: `gh` is missing, not signed in, or gave an error). Only "passed" is said as good news; each of the others is one more thing to look at in the page's own count. A run of an earlier commit of the branch is never reported as this commit's. Building the page never fails because GitHub could not be asked.
- **The last step of a build.** In `.claude/skills/implement-spec/SKILL.md`, after the hand-over run of `python3 checks.py` is green and before `python3 handover.py`: push the feature branch (`git push -u origin feature/<feature>`) and open a draft pull request for it (`gh pr create --draft`), whose text says in one line that the owner has not yet accepted it. Wait for the `checks` run on that pull request to end, in the background (a run has taken 6 to 17 minutes). Green: go on. Red: read which check failed from the run, fix it by the skill's own rule for a red check, run the local checks, and push, which starts the run again; wait once more, and if it is red again, go on and say so first in `now_what`. If the push or the draft cannot be made (no network, not signed in, a plan without drafts), go on and say so first in `now_what`; the page will say the same. The builder never marks the draft ready, never pushes to `main` and never merges: the sentence that forbids pushing is narrowed to say exactly that, in the skill and in `CLAUDE.md`.
- **When the owner accepts or refuses.** `CLAUDE.md`'s line on accepting changes to match: the session marks the draft ready (`gh pr ready`) and gives the link; the owner merges it on GitHub. No run starts, so there is nothing to wait for; if the page said GitHub had not passed, the session says so again with the link. When the owner refuses, the session closes the draft and says so; it deletes no branch.
- **One run for a commit.** Marking a draft ready no longer starts the workflow: `ready_for_review` leaves the workflow's trigger, and the test that pins the trigger is changed on purpose. A draft is still checked like any other pull request, when it is opened and at every push, so nothing reaches `main` unchecked. Starting the workflow by hand stays possible.
- **The workflow's opening lines** give the measured times of real runs in place of "not yet", from this build's own run and the four the retro looked up, and say when it now runs. Its limit stays 20 minutes: one run took about 17.
- **A fix's test.** Step 7 of the skill gains one sentence: the check written for a finding covers every place the rule behind it applies, not only the place the finding named (R-006, "Every means every", at the time of the fix).
- **R-007.** `CODING_STANDARDS.md` gains one line: a constraint the code depends on, which no name states, is held by a test that fails when it is broken. It cites the four findings of `kit-phase-4` it came from, in the form the file already uses; if the defect log does not hold them, they are added by the log's own rules.
- **GitHub's machine.** `docs/agents/local/repo.md` gains one line where a builder writing a walk will meet it: GitHub runs the checks on Linux, where text is drawn in another font and pages draw later under load, so a walk waits for what it reads and never measures by a font's size; it points at E-038 to E-040.
- **The unused settings.** `DATE_FORMAT`, `INPUT_DATE_FORMAT` and `COLUMN_WIDTHS` leave `display.py`, with anything that exists only to serve them. First show that nothing reads them: the app, the tests, the walks and the scripts of the pages.
- **Editing under `.claude/`.** If the session is not allowed to edit the skill file, the changes are written out in full, old words and new, in `.scratch/kit-phase-5/skill-edits.md` for the owner to apply, and the ticket is complete in that form.
- **This build ends by the new last step,** whether the skill file was edited or the edit was left for the owner: after its own hand-over run it pushes its branch, opens its own draft pull request, waits for GitHub and then builds the page, as written above.
- **The picker stays.** The retro proposed removing `--pick`, because the three picked runs of `kit-phase-4` each ran everything. The owner refused: that build changed the files every page shares, which is when a pick must widen. It is judged after two builds that change a page, from the `picks` in the run log.
- **Glossary.** No new domain term.

## Testing Decisions

- **What makes a good test here:** it states what the owner or an agent would observe: what a run printed and how it ended, what the page says, what a file says. It never states how.
- **Seams:** the unit suite for the page and the walk runner; the walks for the trial page's test. Ticket 01 changes a walk of the trial page, so by the build's own rules that area gets its exploratory tester and its reviewer. The other tickets change no page.
- **Asking GitHub** is tested with a stand-in for the `gh` command, as the page's tests already stand in for git and for the opener: one case for each of the five things the page can say, one for a run that belongs to an earlier commit, and one where the command is missing. No test talks to GitHub.
- **A wobble is red** is tested as the runner's tests already do, with a hand-made first run and re-run: red beside the others and green alone now ends red and is named.
- **The rules** in the skill file and the standards are sentences. No test pins their wording.
- **The unused settings:** the full `python3 checks.py` is green before and after, and the ticket's comments hold the search that found no reader.
- **Every new test is seen red first.**

## Out of Scope

- Removing or changing `--pick`, the map of the pages or `prove.py --pick`.
- Narrowing the map's `shared` list. It waits for a build that changes a page.
- Running the checks in a container on the owner's machine. Docker stays refused.
- Tightening the time limits in `CHECKS` or in the workflow.
- A rule that reads more than one build's records to decide red or green.
- Marking the pull request ready without the owner's yes, merging, or protecting `main`.
- Skipping a run on GitHub because an earlier one passed. One run is had by not asking twice, not by letting the job pass without running.
- Copying the changed files into the starter kit: a separate step after this build is merged.

## Further Notes

**Size.** Asking GitHub should be about 60 lines of `handover.py`. If the build passes about 200 lines of new code outside tests, `now_what` says so and why. No new dependency: `gh` is already how a pull request is opened.

**What a draft needs.** GitHub offers draft pull requests on a private repository only with a paid plan. This repo has one. The starter's notes will say so when this is copied there.

**Defaults used unless the owner says otherwise.** A wobble is red at once, not after two builds. The page asks GitHub itself; no record file is kept. A second red run on GitHub ends the trying and is said first. The builder opens the pull request as a draft before the owner has judged; accepting marks it ready. The workflow's limit stays 20 minutes.

**What `now_what` carries, in this order,** beyond what the page computes for itself:

1. What GitHub's machine found for this build's last commit, the run's number and how long it took; and if it was red at first, what failed and what fixed it.
2. The draft pull request's address; or that the push or the draft could not be made, and why.
3. What the wobbling test was reading too early, and how it was shown red.
4. Every run in this build that a wobble turned red, with the test's name.
5. Whether the skill file was edited or the edits were left in `skill-edits.md`.
6. Each default above that was used, and anything in this spec found to be wrong.
