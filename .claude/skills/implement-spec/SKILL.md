---
name: implement-spec
description: "Build a spec and its tickets in this repo: one ticket at a time on one feature branch, then walkers and reviewers try to break it, then one hand-over page for the owner."
argument-hint: "<feature>"
disable-model-invocation: true
---

You have been provided a spec. This spec should have tickets associated with it, describing how to implement the spec. Both live under `.scratch/<feature>/` (`docs/agents/issue-tracker.md`). The feature is the argument; with none, it is the one folder under `.scratch/` that has tickets not yet done.

The goal is the entire spec implemented on a single **feature branch**, every ticket `Status: done`, the checks green, and one **hand-over page** the owner can decide from without reading code.

The owner starts this and leaves. Do not ask them anything the spec, the tickets or the repo can answer, and never ask about the process. When the spec is silent on what the product should do and a wrong guess would be expensive, do not wait for an answer either: build every ticket the question does not gate, leave the gated ones not done, skip steps 6 to 8 (they wait until every ticket is built) and put the question first in `now_what`. The page is where the owner reads it.

The tickets are a **task graph** with blocking relationships. Build them **one at a time**, lowest number first among the tickets whose blockers are done. No worktrees, no parallel implementers, no merges: every commit lands on the feature branch.

Start every subagent with a fresh context window, of the `general-purpose` type. Communicate through **context pointers**: to the spec, the ticket, the brief file, earlier commits. Don't duplicate what a pointer already gives.

`python3 checks.py` is the only judge of whether the code works, and you run it yourself; a subagent's word is not a run. It takes about four minutes and ends within fourteen, longer than the ten minutes the command tool waits: run it in the background and wait for it to end.

**When it is red, at any step:** send the path of the red check's output file to the subagent whose work turned it red (a fresh implementer if there is none) and run the command again when it reports. After two such goes, use one fresh subagent that calls the Skill tool with `mattpocock-skills:diagnosing-bugs`; tell it the owner is away, so where that skill says to ask the user it reports what it tried instead. If the checks are still red after that:

- on a ticket (step 4): stop building. Set the ticket back to `Status: ready-for-agent`, commit, and go to step 9. Steps 5 to 8 are skipped.
- on a fix (steps 5, 7 and 8): revert that finding's commit and give it the fate `left`; its `why` says the fix made the checks fail and was reverted, then what the diagnosis found.
- anywhere else: hand over red, with the red check first in `now_what`.

## Steps

1. Read the spec, the tickets and `docs/agents/local/repo.md`.

2. **Start, or pick up.** Run `git fetch origin`.
   - If `feature/<feature>` already exists, check it out and carry on from the first ticket not `done`. An implementer picking up a half-built ticket reads the uncommitted changes first. A walker or reviewer whose findings file already exists is not run again: carry on from the findings that have no fate.
   - Otherwise, if `main` is behind `origin/main`, fast-forward it. Stop with one line only if it cannot fast-forward; if `main` has no `checks.py`; if files outside `.scratch/<feature>/` are uncommitted; or if `git branch --no-merged main --list 'feature/*'` names another branch: the last build is neither merged nor deleted, and building now would leave it out. Then create `feature/<feature>` from `main` and commit `Start the build: <feature>`: the spec and tickets if they are not committed yet, an empty commit if they are. The hand-over page times the build from the branch's first commit.

3. For each ticket in turn, use a fresh **implementer subagent**, in the foreground. Point it at the spec, its ticket and `docs/agents/local/repo.md`. It:
   - calls the Skill tool with `mattpocock-skills:tdd` to build the ticket. The seams are the two in `CLAUDE.md` (walks for pages, the `api` fixture for the rest), whatever the spec lists, so it does not ask;
   - takes a `walk.shot("<step>")` at each moment worth seeing in a walk it adds. The walks this build adds or changes are the owner's walk-through: `handover.py` records the ones `hand-over.json` lists under `walk_through`, as one recording in parts, and shows the owner nothing else of the app;
   - ticks the ticket's boxes it has met, sets `Status: done`, and commits on the feature branch with the ticket number in the message.

4. When the implementer reports, run `python3 checks.py --quick --pick`. Start the next ticket only on green.

5. **The early read.** After ticket 01 is green and before ticket 02 starts, use one fresh subagent with the brief `.claude/skills/implement-spec/reviewer.md`, finder `early-read`, area `whole`, on the diff so far. A wrong turn is cheapest to fix here. Have its findings fixed, by step 7's rules, before ticket 02 starts.

6. **Break it.** Once every ticket is done and a full run of `python3 checks.py` is green (with a ticket not done, go to step 9), in parallel:
   - one **walker subagent** per area the feature touched (the areas are listed in `docs/agents/local/repo.md`; at most three browsers at once), each with the brief `.claude/skills/implement-spec/walker.md`;
   - one **reviewer subagent** per area, each with the brief `.claude/skills/implement-spec/reviewer.md`, finder `review`. Before starting them, split the output of `git diff --name-only main...HEAD` among them so that every changed file is in exactly one reviewer's list: a page's reviewer takes the API and domain code behind that page and the tests and walks for it. Whatever is left (walk tooling, `checks.py`, modules behind no one page) goes to one more reviewer, area `server-and-checks`.

   A feature that touches no page gets no walker and the `server-and-checks` reviewer alone.

7. **Fix on the same branch.** Use one fresh implementer subagent per area, one after another, each given that area's findings files together and pointed at "The files the page is built from" below. Within an area: `blocks` first, then `wrong`, then `cosmetic`. For each finding, in one commit of its own, in this order: a check that is red because of it goes into the suite (the walker's script made into a walk, or a unit test); then the fix; then one line in `.scratch/<feature>/fates.jsonl`. A finding that is not a defect, or is left unfixed, still gets its line, with the reason in `why`. Run `python3 checks.py --quick --pick` after each implementer reports, and a full `python3 checks.py` after the last. Then compare the ids in `findings/` with the ids in `fates.jsonl`: any id without a fate line goes to a fresh implementer, named by id.

8. **Re-check once.** Skip this step when step 7 changed no code. Otherwise, in parallel:
   - walkers again to the areas the fixes touched, with `pass` set to `recheck`;
   - one reviewer with the brief `.claude/skills/implement-spec/reviewer.md`, finder `review`, area `whole`, `pass` set to `recheck`, on step 7's commits alone (`git diff <the commit before step 7's first>..HEAD`). Nobody has read that code: step 6 read the branch before it was fixed.

   Fix what they find by step 7's rules. Do not start a third round: anything still open gets the fate `left`.

9. **Hand over.** This step runs however the build ended.
   - Write `.scratch/<feature>/hand-over.json`.
   - Commit until `git status --porcelain` prints nothing: delete temporary files you or your subagents made, commit the rest.
   - Run the full `python3 checks.py` on that commit. If it is red and the build did not stop at step 4, apply the rule for red, add what changed to `now_what`, and do this step again, once. If the build stopped at step 4, red is the true state and `now_what` already says so.
   - Push the feature branch (`git push -u origin feature/<feature>`) and open a draft pull request for it (`gh pr create --draft`), whose text says in one line that the owner has not yet accepted it. Wait for the `checks` run on that pull request to end, in the background (a run has taken 6 to 17 minutes). Green: go on. Red: read which check failed from the run, fix it by the rule for red, run `python3 checks.py` and push, which starts the run again; wait once more, and if it is red again, go on and say so first in `now_what`. If the push or the draft cannot be made (no network, not signed in, a plan without drafts), go on and say so first in `now_what`.
   - Run `python3 handover.py <feature>`. It builds the page, opens it in the owner's browser, prints the page's headline, and ends on one line: that the page is open, or the command that opens it. If it refuses (two findings sharing an id, a line that is not JSON, a summary line too long, a build that changed walks and lists none under `walk_through`, a part's title or legend that is too long or holds a name from the code), correct the file it names, and `fates.jsonl` where an id changed, commit, and run it again. It records the walks `walk_through` lists, or the acceptance walk when the build added or changed no walk. If it says the walk-through or the acceptance walk failed, did not run or did not finish, hand over as it is: the page says so.

   Your last message to the owner is one sentence saying how the build ended, then the headline `handover.py` printed (the page's own count of what to look at, so your message and the page agree), then the last line it printed. When that line is a command, the page did not open: say so, and give the command. The page carries the rest. Never mark the draft ready, push to `main` or merge: the owner decides from the page (`CLAUDE.md`, "When the owner accepts a build").

## The files the page is built from

The page is computed from these and from git. Keep to the fields exactly: the script reads no prose. The owner does: a finding's `what`, a fate's `why`, the three lists of `hand-over.json` and each `title` and `legend` of its `walk_through` are printed on the owner's page as written, as plain text (a backtick or an asterisk shows as typed), so they follow `.claude/rules/human-facing-writing.md`. Use the page's words in them (issue, outcome, test, review, walk-through, automated checks: `handover.py`'s docstring has the list).

`.scratch/<feature>/findings/<finder>-<area>.jsonl` (add `-recheck` for the second pass), one finding per line:

```json
{"id": "walker-find-trials-01", "finder": "walker", "pass": "first", "area": "Find trials", "severity": "wrong", "what": "what a user would see or lose, in whole sentences; then the cause, in a sentence of its own", "where": "webapp/static/views/find.js:120", "check": ".scratch/<feature>/findings/scripts/walker-find-trials-01.py"}
```

- `id`: `<finder>-<area>-<NN>` on the first pass and `<finder>-<area>-recheck-<NN>` on the re-check, so no two findings ever share an id. Fates are matched to findings by id alone.
- `finder`: `early-read`, `walker` or `review`.
- `pass`: `first` or `recheck`.
- `area`: one of the areas in `docs/agents/local/repo.md`, `server-and-checks`, or `whole` (the early read, and the re-check's reviewer).
- `severity`: `blocks` (a user cannot finish a task, or loses data), `wrong` (the app shows or stores something untrue, or goes against the spec), `cosmetic` (looks off; nothing is untrue).
- `check`: the script or test that is red because of the defect; empty when the finder could not write one.

`.scratch/<feature>/fates.jsonl`, one line per finding id:

```json
{"id": "walker-find-trials-01", "fate": "fixed", "commit": "abc1234", "check": "walks/test_find_trials_walk.py::test_a_filter_survives_paging", "why": ""}
```

- `fate`: `fixed`, `left` or `not-a-defect`. `fixed` names the commit and the check now in the suite. `left` and `not-a-defect` give the reason in `why`: the reason itself first, in a sentence the owner can accept or reject without opening anything, then where it was decided. The reason is what happened in this build: the fix made the automated checks fail and was reverted; the re-check found the issue and the build stops after one re-check; the spec rules it out. Findings that share one reason carry the same `why`, word for word: the page then prints it once.

`.scratch/<feature>/hand-over.json`, written by you:

```json
{"what": ["what was built, as the user meets it"], "so_what": ["what the owner can now do that they could not, and what to try first"], "now_what": ["what is left, unknown or not checkable here"], "walk_through": [{"test": "test_walk_a_filter_survives_paging", "title": "A filter is kept from page to page", "legend": "The list is filtered to recruiting trials, then turned to page two. Page two should still show recruiting trials only."}]}
```

`walk_through` is the owner's recording of what the build changed: one entry per part, in the order to show them. The page plays the parts as one recording and prints each part's `title` and `legend` under it, the way a figure carries its legend, so the owner knows what they are watching without the code open.

- `test`: a walk this build added or changed, by its function name (`file::name` where two files share a name). The script refuses any other.
- `title`: the change as the user meets it, in at most 80 characters.
- `legend`: what is done in the recording and what should be seen, in at most 300 characters. Write it from the walk's steps and its last assertion.
- Neither holds a name from the code (a test, a function, a file): the script refuses one.
- List each walk that shows a change the spec asked for. A walk the build edited only in passing may be left out: the page counts it as left out and names it under a fold. A build that added or changed no walk has no `walk_through`.

One thing per line. `what` and `so_what` take at most five lines each, and no line of the three is longer than 200 characters: the script refuses more. `now_what` is as long as its list needs, weightiest first, because the page shows its first five lines and folds the rest. Leave out what the page counts for itself (issues and their outcomes, commits, files, check runs, how long the build took): a typed number can disagree with the page's. The page prints `what` at its top, labelled as your words and unchecked: write there what a user now meets, and keep how the build went for `now_what`. `now_what` carries, in this order and only where they exist: a question the spec could not answer; a ticket not built and the red check that stopped it; every finding left unfixed; what a walker reported it could not try.
