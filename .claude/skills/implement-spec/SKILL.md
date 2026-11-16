---
name: implement-spec
description: "Build a spec and its tickets in this repo: one ticket at a time on one feature branch, then walkers and a review try to break it, then one hand-over page for the owner."
disable-model-invocation: true
---

You have been provided a spec. This spec should have tickets associated with it, describing how to implement the spec. Both live under `.scratch/<feature>/` (`docs/agents/issue-tracker.md`).

The goal is the entire spec implemented on a single **feature branch**, every ticket `Status: done`, the checks green, and one **hand-over page** the owner can decide from without reading code.

The owner starts this and leaves. Do not ask him anything the spec, the tickets or the repo can answer. A question about the process is never worth a message; a question about what the product should do is, when the spec is silent and a wrong guess would be expensive.

The tickets are a **task graph** with blocking relationships. Build them **one at a time**, lowest number first among the tickets whose blockers are done. No worktrees, no parallel implementers, no merges: every commit lands on the feature branch.

Start every subagent with a fresh context window, of the `general-purpose` type. Communicate through **context pointers**: to the spec, the ticket, the brief file, earlier commits. Don't duplicate what a pointer already gives.

`python3 checks.py` is the only judge of whether the code works. Nothing is done while it is red. Never delete, skip or weaken a check to get it green; a check changes only when the spec changed the behaviour it checks, and the commit message says so.

## Steps

1. Read the spec, the tickets and `docs/agents/local/repo.md`.

2. Create the branch `feature/<feature>` from `main` and make one empty commit, `Start the build: <feature>`. The hand-over page times the build from that commit.

3. For each ticket in turn, use a fresh **implementer subagent**, in the foreground. Point it at the spec, its ticket and `docs/agents/local/repo.md`. It:
   - calls the Skill tool with `mattpocock-skills:tdd` to build the ticket. The seams are the ones the spec names; the owner agreed them when the spec was written, so it does not ask again;
   - ticks the ticket's boxes it has met, sets `Status: done`, and commits on the feature branch with the ticket number in the message.

4. When the implementer reports, run `python3 checks.py` yourself. If it is red, send the same implementer the path of the red check's output file and run the command again when it reports. If it is red a third time on one ticket, use a fresh subagent that calls the Skill tool with `mattpocock-skills:diagnosing-bugs`. Start the next ticket only on green.

5. **The early read.** After ticket 01 is green and before ticket 02 starts, use one fresh subagent with the brief `.claude/skills/implement-spec/reviewer.md`, finder `early-read`, on the diff so far. A wrong turn is cheapest to fix here. Have its findings fixed, by step 7's rules, before ticket 02 starts.

6. **Break it.** Once every ticket is done and the checks are green, in parallel:
   - one **walker subagent** per area the feature touched (the areas are listed in `docs/agents/local/repo.md`; at most three browsers at once), each with the brief `.claude/skills/implement-spec/walker.md`;
   - one **reviewer subagent** per area, each with the brief `.claude/skills/implement-spec/reviewer.md`, finder `review`;
   - call the Skill tool with `mattpocock-skills:code-review`, fixed point `main`, and write each thing it raises as a line in `.scratch/<feature>/findings/review-standards.jsonl` in the format below.

7. **Fix on the same branch.** Use one fresh implementer subagent for all the findings. For each finding, in this order: a check that is red because of it goes into the suite (the walker's script made into a walk, or a unit test); then the fix; then one line in `.scratch/<feature>/fates.jsonl`. A finding that is not a defect, or is left unfixed, still gets its line, with the reason in `why`. Every finding has exactly one fate line before you go on.

8. **Re-check once.** Run `python3 checks.py`. On green, send walkers again to the areas the fixes touched, with `pass` set to `recheck`. Fix what they find the same way. Do not start a third round: anything still open gets the fate `left` and a line in the page's "now what".

9. **Hand over.** Write `.scratch/<feature>/hand-over.json`, commit, then run `python3 handover.py <feature>`. Your last message to the owner is the `open` command it printed and nothing else of length. Do not push, merge or open a pull request: he decides from the page.

## The files the page is built from

The page is computed from these and from git. Keep to the fields exactly; nothing reads prose.

`.scratch/<feature>/findings/<finder>-<area>.jsonl` (add `-recheck` for the second pass), one finding per line:

```json
{"id": "walker-find-trials-01", "finder": "walker", "pass": "first", "area": "Find trials", "severity": "wrong", "what": "what a user would see, in one or two sentences", "where": "webapp/static/views/find.js:120", "check": ".scratch/<feature>/findings/scripts/walker-find-trials-01.py"}
```

- `finder`: `early-read`, `walker`, `review` or `you` (the owner).
- `pass`: `first` or `recheck`.
- `severity`: `blocks` (a user cannot finish a task, or loses data), `wrong` (the app shows or stores something untrue, or goes against the spec), `cosmetic` (looks off; nothing is untrue).
- `check`: the script or test that is red because of the defect; empty when the finder could not write one.

`.scratch/<feature>/fates.jsonl`, one line per finding id:

```json
{"id": "walker-find-trials-01", "fate": "fixed", "commit": "abc1234", "check": "walks/test_find_trials_walk.py::test_a_filter_survives_paging", "why": ""}
```

- `fate`: `fixed`, `left` or `not-a-defect`. `fixed` names the commit and the check now in the suite. `left` and `not-a-defect` say why.

`.scratch/<feature>/hand-over.json`, written by you, in plain words for someone who will not read the code:

```json
{"what": ["what was built, as the user meets it"], "so_what": ["what he can now do that he could not, and what he should try first"], "now_what": ["what is left, unknown or not checkable here; every finding left unfixed"]}
```

Two to five short sentences in each list. Facts and numbers stay out of it: the page computes those.
