# Orchestrator: how a build is run

Facts for the session orchestrating the `implement-spec` skill in this repo: the main session, which dispatches every other agent. Subagents do not read this file. Each has a role file under `.claude/agents/` that is its whole contract, so nothing here is pasted into a prompt.

**The gate prints each phase's checklist where the phase ends** (the empty frontier, the clean box audit, the ready stamp), so a compacted session cannot lose a rule: the tool says it when it applies. This file holds the rest.

**Work in the integration worktree**: the checkout that has the integration branch. Every `gate.py` command below is run there. The gate reads the tree it is run in, and the ready stamp belongs to that worktree.

## Where this departs from the skill

### Checked against 1.3.1

Checked on 2026-11-07 against the installed `mattpocock-skills` plugin at version 1.3.1 (`mattpocock/skills` at 4588b32). `implement-spec`, `to-tickets`, `pr` and, as of that checkout, `retro` are under `skills/engineering`; `skills/in-progress` holds none of them. Their steps can still change without warning: if the skill's steps have changed, re-check this list and the version above.

- **Its per-ticket merge step (its step 5, a `merger` subagent per ticket) is `gate.py merge`**, which runs every suite and marks the ticket done; a `merger` is dispatched only for a conflict. Confirmed.
- **A `Kind: foundational` or `Kind: walk-tooling` ticket is reviewed by a `ticket-reviewer` the orchestrator dispatches**, after its implementer reports; every other ticket's second read is the whole-branch review's. The skill has no per-ticket review: its implementers call `tdd` and merge the integration tip, and nothing reads the result before the merger. Confirmed.
- **The orchestrator creates the worktrees, and an implementer does not merge the integration tip before reporting** (its step 4 has it do both). The worktree is cut from the integration tip, and the merge of the integration tip into a branch happens when `gate.py merge` meets a conflict or an aborted merge sends an implementer back. Confirmed.
- **Its closing step (its step 7, `code-review` of the whole branch, then one implementer fixing everything) is replaced** by the whole-branch review below. `mattpocock-skills:code-review` still runs once there, inside a subagent. Confirmed.
- **The pull request is marked ready through the ready gate and the records stamp**, not when the last ticket merges (its step 8). Confirmed.
- **Worktree cleanup (its step 9) is `close` printing one `git worktree remove` per worktree.** Confirmed.

## Roles and models

| Role | Dispatch as | Model | Does |
|---|---|---|---|
| Implementer | `implementer` | Sonnet | One ticket, test-first, in its own worktree |
| Ticket reviewer | `ticket-reviewer` | Sonnet | Fresh read of a `Kind: foundational` or `walk-tooling` ticket's diff against the spec sections it cites; its evidence; a mutation sample. No other ticket gets one |
| Merger | `merger` | Sonnet | Resolves the conflict `gate.py merge` stopped on; dispatched only then |
| Exploratory walker | `exploratory-walker` | Sonnet | Tries to break one area of the running app; reports only |
| Standards reviewer | `standards-reviewer` | Sonnet | Runs `mattpocock-skills:code-review` over the whole branch, once |
| Branch reviewer | `branch-reviewer` | Opus | An area of the whole branch, the seams between areas, a foundational ticket, the walk tooling, a scoped re-check, or a spec against its brief |
| Review merger | `review-merger` | Opus | Ranks and classes the findings; writes the fix spec, the Open list and the ledger rows |

- **Dispatch by name and pass no `model`.** The model is in the role file, and a `model` on the call overrides it.
- **Sonnet implements because the tests and the reviewer catch a Sonnet-level mistake better than a bigger model prevents one.** Opus is spent where nothing downstream checks the work: the foundation, the walk tooling, and the whole branch.
- **There is no cap on Opus subagents at once.** A subagent that stalls on a session limit keeps its transcript and resumes with SendMessage after the reset.
- **Create each worktree yourself**, named after the ticket's file without `.md`: `git worktree add .claude/worktrees/<NN-slug> -b ticket/<NN-slug> <integration branch>`. Do not rely on a subagent's own worktree isolation: it branches from the default branch, not the integration tip. `.claude/worktrees/` is git-ignored, or every worktree would make the integration tree look dirty.

## Prompts are pointers

A dispatch prompt names where things are and nothing else, bar the one line named under the ticket reviewer. The role file holds the rules; the spec, the ticket and the commits hold the content.

- **Implementer**: the feature, the ticket file, the worktree path and its branch, the integration branch. For the exploration ticket, also the walkers' branches.
- **Ticket reviewer**: the feature, the ticket file, the worktree path, the integration branch, and the implementer's `Hand sample:` line from its report, verbatim (the reviewer's draw skips the lines it names; with none, say "no Hand sample line").
- **Merger**: the feature, the ticket number, the ticket branch, the integration worktree's path.
- **Exploratory walker**: the feature, its area (from `local/repo.md`), its worktree and branch.
- **Standards reviewer**: the feature, the base branch, where to write.
- **Branch reviewer**: which read it is; the feature; the spec's path (and the brief's, for a spec against its brief); the diff command; where to write.
- **Review merger**: the findings folder, the feature, the pull request number if there is one.

A report comes back as a branch tip or a file path and a few counts. Long reports are the main cost of this session's context: read the file a report names only when a decision needs it.

### Release

Before the first dispatch, `python3 .claude/factory/gate.py release <feature>` moves the spec and its tickets from `needs-triage` to `ready-for-agent`; do not edit the `Status:` lines by hand. It refuses a branch not cut from the protected branch's tip, a spec missing the tickets `tickets.md#kind` lists, and a `Brief:` with no `spec-against-brief` log entry. Commit what it changed. Release is a records change made before any ticket exists on the branch, so it sits outside the two-stamp close (`#close`).

## The loop

1. **Ask the gate for the frontier**: `python3 .claude/factory/gate.py frontier <feature>`. It reads every ticket's `Status:`, `Blocked by:` and `Touches:` lines and the worktrees, and prints what is ready, held, in flight and blocked. Do not keep the frontier in your head.
2. **Dispatch an `implementer` for each ready ticket**, in the background. Not for a held one: it touches a shared file a ticket in flight also touches, or one of the two is marked `*` to run alone. Keep the number of agents running browsers at or below the figure in `local/repo.md`.
3. **When an implementer reports green**, read the ticket's `Kind:`. For `foundational` or `walk-tooling`, dispatch a `ticket-reviewer` on its worktree, passing the report's `Hand sample:` line on in the prompt. When the reviewer reports findings, resume that implementer with SendMessage and the findings file's path: it fixes every blocking finding, and fixes or leaves each note, saying why in the file. One round. A second read of the same ticket is the whole-branch review's. A review with no blocking finding and every note already `left` skips the resume (No blocking findings, below). **Every other ticket goes straight to step 4**: its hand sample was the implementer's own, and the whole-branch review is its second read. The audit (`gate.py close`) asks for `reviews/<NN>.md` only for the two reviewed kinds; a review that exists is judged whatever the kind.
4. **Then run the merge yourself**, in the integration worktree: `python3 .claude/factory/gate.py merge <feature> <NN> <branch>`. It checks the tree, merges, runs every check, asks the ticket gate, marks the ticket done and commits `Merge ticket NN: <title>`, logging `merge-start` and `merge-end`. Merges run one at a time: they share one worktree and one index. The refusal names its rule. `merge-conflict` (it names the files and leaves the merge open): dispatch a `merger`, which resolves the conflict, and run the command again. `merge-checks` or `merge-ticket-gate`: resume the implementer (step 6). `merge-config`, `merge-git` or `merge-commit`: read the refusal and report it; the implementer cannot fix it.
5. **While a merge is running or open, write and commit nothing in the integration worktree.** The command holds a merge open while the suites run, and any commit made there in the meantime concludes that merge with the suites unrun and the ticket not marked. A status change or a findings file waits until it reports.
6. **A merge that aborts prints why.** If its rule is `merge-checks` (a suite went red on the merged tree) or `merge-ticket-gate` (the ticket gate refused), resume the implementer: merge the integration tip into its branch, resolve keeping the other ticket's behaviour and tests, re-run, report. Then merge again.
7. **Log each event in the grammar**, one line each: `python3 .claude/factory/gate.py log <feature> <verb> ...` (the log grammar, below). The log is kept in the git directory, not in the tree, so writing it never dirties a checkout or disturbs a merge. It is how a restarted session, the audit and the build row know what happened.
8. **Push a batch, not each merge** (`ci-spend.md`): when several merges are in, before a review reads the branch, and at ready.
9. Go to 1.

### The foundation read

- **The foundational ticket is reviewed as soon as it merges**, by a `branch-reviewer`, before the dispatch of the tickets whose `Blocked by` names it; the others go on meanwhile. `gate.py frontier` holds exactly those tickets (`held: NN (foundation 01 read pending)`, or `read not dispatched` before the read is logged), and releases them when `report <NN> branch-reviewer` is logged: the gate releases at the report, not at the follow-up's merge. A spec therefore keeps `Blocked by` to the tickets that build on the foundation's code. The spec names the foundation. So is the walk-tooling ticket: every later walk's validity rests on its guards. The reviewer writes `<tracker>/<feature>/reviews/<NN>-foundation.md`; commit it, then resume that ticket's implementer with it as review findings and hold the tickets it blocks by hand, not dispatching them until the fixes have merged, whatever the frontier shows (whether the gate should hold them is an open question for the kit).
- **The exploration ticket is worked in two steps** (`walkthrough.md` section 5). When it is ready, create one worktree per area, named `<exploration ticket's file name>--<area>` with branch `ticket/<the same>`, and dispatch an `exploratory-walker` into each, at once. The gate then shows the ticket in flight. When all have reported, dispatch an `implementer` for the exploration ticket in a worktree of its own, naming the walkers' branches in its prompt. Then review and merge it like any other ticket.
- **After the first ticket with something to see merges, show the user**: the paths of its walk's screenshots and one line on each. Keep building. A wrong direction is then found one ticket deep instead of at hand-over.

### Follow-ups

A fix found after a ticket merged (a review round that came late, a defect in the merged work) is a follow-up, not a second merge of the ticket. Log `python3 .claude/factory/gate.py log <feature> dispatch <NN> implementer --agent <id> --follow-up`, work it on its own branch (below), review it into `reviews/<NN>-followup.md` (or `-followup-<n>.md`) with every blocking finding closed, then run `python3 .claude/factory/gate.py merge <feature> <NN> <branch> --follow-up`. It runs every step a merge runs and writes `merge-start`/`merge-end`, commits `Merge ticket NN follow-up: <title>` and leaves the ticket's `Status: done`. Without `--follow-up` a done ticket is not merged again. The gate judges a done ticket from the first merge's base to its newest merge, so the first merge's `doc:` files are still new and a follow-up's `red:` runs are on the branch. A follow-up dispatch is an attempt, as the audit counts it (`#audit`): a ticket's dispatch and one follow-up pass, a third attempt needs `needs-triage` (below). `gate.py frontier` prints `unpushed: N merge(s) since <remote tip>` when the integration branch is ahead of its upstream, so a batch is pushed before a review reads the branch (step 8).

**The follow-up branch.** Cut it from the integration tip (as `every-agent.md` says for every worktree), in a new worktree; the ticket's first branch is not worked on again. `gate.py ticket` run there judges the ticket from the first merge's base to the branch's HEAD, so a new box and its new `red:` run pass on the branch, and `gate.py ticket` prints the follow-up review file to write.

**The third attempt.** `merge --follow-up` refuses a ticket that is not `done`, and the audit wants `needs-triage` in the status history of a ticket attempted three times. Before the third `merge --follow-up`, commit the ticket's `Status: needs-triage` on the integration branch, then `Status: done`: two commits.

### No blocking findings

When the findings file has no blocking finding and the reviewer has already marked every note `| left: <why>`, `gate.py ticket` passes it as it stands: do not resume the implementer, go straight to step 4. A note still `open` is the implementer's to fix or leave. What closes a blocking finding is read by the gate from the file: `fixed` only with a check and a committed `red:` run showing it fail at the review's tip, `unreachable` only with one committed `run:` per engine, and `left` never (`ticket-reviewer.md`, Closing grammar).

## The log grammar

Each line is `<ISO time> <verb> <args>`. The audit and the build row read these verbs; free prose is written with `note` and is invisible to them. An unknown verb or the wrong arguments is a usage error, and nothing is written.

| Verb | Written when |
|---|---|
| `dispatch <NN> <role> --agent <id>` | an agent is dispatched for a ticket (the id from the dispatch result) |
| `dispatch <NN> implementer --agent <id> --follow-up` | an implementer is dispatched for a fix after the ticket merged (`#follow-ups`); the flag is valid only with `--agent` |
| `report <NN> <role>` | that agent reports (the only verb a subagent writes: the guard refuses the rest, and `gate.py open`, from one) |
| `resume <NN> <role>` | it is resumed (a second attempt) |
| `foundation-read <NN> --agent <id>` | the foundation or walk-tooling read of a ticket is dispatched |
| `review-wave <n>` | a whole-branch review wave is dispatched |
| `spec-against-brief <path>` | the spec-against-brief read is committed |
| `merge-start <NN> <tip>`, `merge-end <NN> <result>` | written by `gate.py merge`, not by hand |
| `merge-abort <NN> <start time> "<reason>"` | late line: a merge was aborted and no `merge-end` was written (`#late-lines`) |
| `decided <n> <commit>` | late line: the user decided Open list item n in `<commit>` and no `open` line was written (`#late-lines`) |
| `observation "<text>"` | something the observer or the scorer should see: a surprise, a workaround |
| `note "<text>"` | anything else |

`gate.py log <feature>` prints the tail; `gate.py log <feature> --agents` prints agent ids by ticket and role, for resuming one. `gate.py open <feature> "<item>"` appends a numbered item to the spec's `## Open list` (creating the section) and logs it as `open`; an Open list addition is always made this way, so the audit can see when. `gate.py stats` prints each log's first and last time beside the guard counts.

### Late lines

Two verbs record a true event the log missed, after the fact; never write one instead of the line at the time. Each is checked by the audit against something it cannot fake.

- **`merge-abort <NN> <start time> "<reason>"`**: the merge of NN whose `merge-start` is at `<start time>` (as `gate.py log` prints it, `YYYY-MM-DDTHH:MM:SS`) was aborted and its `merge-end` was never written. The audit pairs it with that `merge-start`, which must exist, be for NN and have no `merge-end` before the next `merge-start`, counts no overlap for it and prints the reason. A `merge-abort` naming no such open start is a violation.
- **`decided <n> <commit>`**: the user decided Open list item n in `<commit>` and the item was not added with `gate.py open` (the review merger writes an Open list by hand). The audit accepts it for a `Kind: design` ticket NN when the commit is an ancestor of the ticket's merge, changes the feature's `spec.md`, and the spec there has item n naming `ticket NN`; any other `decided` line is a violation.

## Audit

`gate.py audit <feature> [<review-fix feature>] [--report <file>]` reads the build log (in the grammar above) and the git history and says whether the loop was run as this file describes. It prints one line per rule: `ok`, a `violation`, or `expected and did not find: <line>` where a rule needs a log line the log does not hold (silence is never compliance). The rules: every `Merge ticket NN:` commit has `reviews/NN.md` on its branch with every blocking finding closed (a `Merge ticket NN follow-up:` commit has `reviews/NN-followup.md` or `-followup-<n>.md`, closed the same way) and a `merge-start`/`merge-end` pair; merges did not overlap and no commit landed in the integration worktree while one was open; each ticket with a branch was dispatched once (a second attempt is `resume`; a third went back through `needs-triage`); the foundation read precedes the dispatch of what the foundation blocks; a user-facing spec's exploration and acceptance-walk tickets were dispatched and reported; `spec-against-brief` precedes the release; a merged `Kind: design` ticket has an `open` line before its merge (or a valid `decided` line); the built-tip stamp exists, and the records stamp's parent is the built tip.

- **A log older than the grammar.** The grammar began at the log's first ISO line (no `- ` prefix, as `gate.py log` writes), and only when dash-prefixed prose came before it. An expected line for an event before that is printed as `expected and did not find ... (before the log grammar began; not counted)` and does not fail the audit. A log that is ISO from its first line has no such excuse: every missing line counts, however late its first dispatch. An old log with no ISO line at all counts every one, so an old build audits as a baseline of what its log cannot prove.
- **An attempt is not a round.** A ticket's attempts are its `dispatch NN implementer` plus each `resume NN implementer` that follows that implementer's own `report NN implementer`, and each `dispatch NN implementer --agent <id> --follow-up` (an escape past the review). A resume after `report NN ticket-reviewer` (step 3, the review-fix round) or after `merge-end NN red|refused|conflict|failed` (step 6, a merge abort) is a round and is not counted. Three attempts need a `needs-triage` status in the ticket's history.
- **`gate.py close` runs the audit first** and refuses to write records on a violation. Fix it or record why, then close again.
- **`gate.py ready <feature> --records <Y>` audits the committed report** (`audit --report`), so the report is checked at the moment it is handed over: every 7-character hash it contains is a commit on the branch, the tip it calls built is the built-tip stamp's, and every count in a `| Measure | Value |` table (and the Facts block's `Tickets` and `Boxes` lines) that the gate can compute matches, with both values printed when it does not.

## When a ticket cannot be finished

- **If the spec or the ticket turns out wrong, the implementer stops and reports `needs-info`.** Set the ticket's `Status:` to `needs-info` on the integration branch, with a note saying what it asks and what stands in the way, and commit it.
- **A `needs-info` on the spec goes to its author at once**: the session that wrote it, by SendMessage, when `ListAgents` lists it; otherwise the user. The user approved the spec, and nothing else in the loop may change it; the author's answer is appended to the spec's `## Comments` and the clause amended to match. Tickets blocked by that one leave the frontier until the answer comes; the rest carry on.
- **An attempt fails** when the implementer reports with checks still red, or with a blocking review finding it says it cannot resolve inside the ticket. A failed ticket gets one more implementer, resumed with SendMessage or started fresh in the same worktree, given the first report.
- **After two failed attempts the ticket goes to the user**: its `Status:` becomes `needs-triage` with a note naming both attempts, the tickets it blocks leave the frontier, and you tell the user then, not at hand-over. Not `ready-for-human`: that status is for the tickets that were always the user's, and the ready gate lets those through.

## When the frontier is empty

`gate.py frontier <feature>` prints the steps itself when every ticket is done or the user's own: audit the boxes, review the whole branch, run the ready gate. Follow what it prints; `gate.py boxes <feature>`, when clean, prints the review's dispatch list with the findings folder, and `gate.py ready`, when it stamps, prints the close-out.

## The whole-branch review

- **One integration branch per feature**, reviewed into `main`. When the repo has a GitHub remote, this is one pull request per feature: push the branch and open it as a draft after the first ticket merges (`gh pr create --draft`, body from the `pr` skill, naming the spec and tickets). Without a remote, the review reads `git diff main...<integration branch>` in the integration worktree.
- **No review of the whole branch runs in the main session.** It fills the context window at the point it is most needed.
- **The waves** (wave one: an area per `branch-reviewer` and a `standards-reviewer`, at once; wave two: the seams; reviewers commit nothing) are in the dispatch list `gate.py boxes` prints. Log each as `review-wave <n>`.
- **One `review-merger` ranks and classes the findings**: blocking; sweep (mechanical, inside one file, no change in behaviour, not shared plumbing); design (a decision that is the user's); nit (dropped, recorded with why). It writes the fix spec and its tickets for the blocking ones, one sweep ticket, and the **Open list** of design findings, each with a recommendation. A non-blocking finding joins a blocking ticket only when its fix is in the function that ticket already changes. Ticketing every non-blocking finding rewrites shared code nobody asked to change. It returns only the ticket list; the main session reads that, not the findings files.
- **Then the branch is read again, at most twice.** A re-read is a round, and its findings go to `findings/round-<n>.md`. The review is over when a round finds nothing new that is blocking. If the second round still finds some, the open list goes to the user rather than to a third round.
- **A round after a fix is scoped to the fix.** When a round's blocking items are few and each fixed by one small ticket, the next read is one `branch-reviewer` given only `git diff <previous round's tip>..<new tip>` and that round's findings file, asked whether each fix landed and whether anything new blocks (`findings/round-<n>-check.md`). A scoped read does not count toward the two whole-branch rounds; after two scoped reads that still find a blocking item, the open list goes to the user.
- **The two rounds are the root feature's, and a fix feature's rounds count toward them.** There is one fix feature, `<feature>-review`; its own review is a round of the root's, not a review with rounds of its own. `gate.py release` refuses `<feature>-review-2` (or `-review-review`) by `release-rounds`: a blocking item still open after the cap is the user's, on the Open list, not a new feature's.

### The fix branch

- **The fix tickets are worked on the fix feature's own integration branch**, `feature/<fix feature>`, cut from the feature's branch tip and merged there by `gate.py merge <fix feature>`, through the loop above. The feature's branch is not fast-forwarded onto the fixes.
- **Each feature's tickets are judged from a checkout of its own branch.** The gate finds a ticket's merge by the ticket's own files in its feature, so a fix feature's `Merge ticket 01:` on the same line is never taken for the feature's own.
- **`ready`, `handover` and `close` name both features**: `gate.py ready <feature> <fix feature>`, and the same for the other two.

## Ready, and what reaches the user

- **The ready gate is one command**: `python3 .claude/factory/gate.py ready <feature> [<review-fix feature>]`. It needs a clean tree, every ticket done or the user's own, every box evidenced or needs-human, the forbidden-pattern lint clean and every suite green on the tip; then it stamps that tip, the **built tip** X, and prints the close-out steps. It is the last thing that happens to the branch's code.
- **`gh pr ready` is refused unless the tip is stamped.** One more commit and the stamp no longer matches: run the gate again (or, after the close, the records stamp).
- **The user gets three things**: the output of `python3 .claude/factory/gate.py handover <feature> [<review-fix feature>]` (what to judge, their own tickets, the stand-ins nothing checks); the Open list, where they need only say which recommendations they reject; and the pull request.
- **Merging into `main` is the user's act.**

## Resuming a build

A session that restarts mid-build rebuilds its picture from the repo:

- **What is done, ready and in flight**: `python3 .claude/factory/gate.py frontier <feature>`.
- **What happened and why**: `python3 .claude/factory/gate.py log <feature>`.
- **A ticket in flight has a worktree whose commits are the work so far.** Resume its agent with SendMessage if the agent is still listed; otherwise start a fresh implementer in that same worktree, told to read its own branch's commits first. Never dispatch a ticket that has a worktree into a new one.
- **If the integration worktree is mid-merge** (`git status` says so) and no merger is listed, `git merge --abort` and run `gate.py merge` again; do not dispatch the merger.

## Close

The close is two stamps in order, so that no tracked write follows the stamp the report names. The gate prints these steps after the first stamp; this is the rule behind them.

1. `gate.py ready <feature>...` stamps the built tip X.
2. `gate.py close <feature> [<review-fix feature>]` refuses unless X is stamped and the tree is clean; runs the audit; prints the dispatch lines for the scorer and the observer when their roles exist and waits for `--collect`; then writes every record in one pass (`builds.jsonl` with `tip: X`, the tokens record `tokens.jsonl` for each subagent and for the orchestrating session, the build row in the ledger's Builds table, the scorer's and observer's records), prints the `## Facts` block (with `- Tokens:` and, when `prices` are set, `- Cost:`), runs `gate.py github` for the current month when `origin` is a GitHub remote, writes the dashboard page and prints `dashboard: <path>`, and prints one `git worktree remove` per ticket worktree. A failure in `github` or `dashboard` prints one line and does not change the exit code; `github-storage.json` and `github.jsonl` are written before step 3, so they go in the same commit. What the page shows is in `dashboard.md`. Run the worktree lines one at a time.
3. Write `<tracker>/<feature>/report.md`, embedding the Facts block verbatim. **The report embeds the Facts and restates none of them**: a number written twice goes stale. Commit everything from step 2 and the report as one commit `Close <feature>` (Y).
4. `gate.py ready <feature>... --records Y` re-stamps Y when `git diff X..Y --name-only` touches only record paths (`docs/agents/local/*.jsonl`, `ledger.md`, `rules.md`, `<tracker>/**`), Y's parent is X, and the report names X. Anything else refuses the stamp by name: a code change after X is the next feature, not this close.
   Record paths, in full: `docs/agents/local/*.jsonl`, `docs/agents/local/github-storage.json` (written by `github` before the records commit), `ledger.md`, `rules.md` and `<tracker>/**`.
5. The hand-over names X as built and Y as stamped. `gh pr ready` is allowed on Y.

### Reporting at close

`gate.py close` writes the tokens record (`tokens.jsonl`, one line per agent run and model, the orchestrating session included) in the same pass as `builds.jsonl`, and the Facts carry `- Tokens:` and, with `prices` in `factory.json`, `- Cost:` with the count of unpriced models. When `origin` is a GitHub remote it then runs `gate.py github` for the current month (its files are written before step 3, so they go in the Close commit), writes the dashboard page and prints `dashboard: <path>`; the hand-over names the same path. A failure in `github` or `dashboard` prints one line and leaves the exit code alone. `dashboard.md` says what the page shows.

- **The spec's own `Status:` goes to `done`** in the commit that closes its last ticket (`gate.py merge` does it). A spec whose tickets are all closed but whose line was never moved reads as open indefinitely.
- **A defect the user finds after hand-over gets an escape row the day it is found.**
- **Retro is the user's.** `/retro` can only be run by the user, and whether to run one is theirs: a session neither writes a retro by hand nor asks the user to run one. When a retro's findings exist, they go where retro puts them: a mechanical mistake becomes a guard rule, a forbidden pattern or a test; a judgement call becomes a line of `CODING_STANDARDS.md`; a navigation gap becomes a pointer in `docs/agents/`.
