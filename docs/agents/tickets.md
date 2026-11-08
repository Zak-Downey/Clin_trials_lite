# Tickets: what the tracker holds and what the gate reads

Facts for whoever writes a spec's tickets (`to-tickets`, or the review merger writing a fix spec) and whoever changes a ticket file. `issue-tracker.md` says where the files live. This file says what goes in them, because `.claude/factory/gate.py` reads them: the frontier, whether a ticket is done, and whether a branch is ready all come from these lines.

## The tracker folder

`<tracker>` is `factory.json`'s `tracker` (default `.scratch`); every path below that begins `<tracker>/` is under it.

## A feature's folder

```
<tracker>/<feature>/
  spec.md             the spec; its Status line; decisions left under ## Comments
  issues/NN-<slug>.md one ticket per file, numbered from 01
  reviews/NN.md       the per-ticket review's findings (foundational and walk-tooling tickets), each marked fixed or left
  explore/<area>.md   an exploratory walker's findings; explore/<area>/ holds its scripts
  walks/              walk results and, git-ignored, screenshots (factory-allow: the tracker's own folder)
```

The build log is not here: it is kept in the git directory and read with `gate.py log <feature>`.

## A ticket's header lines

Above the `## Comments` heading, bold or plain. `to-tickets` writes the first two; add the third. Acceptance boxes are read down to `## Comments` too; a box below it is conversation, not a criterion.

- **`Blocked by:`** the numbers of the tickets that gate this one, or `None`. Lists (`01, 04`) and ranges (`01 to 10, 12`) are read; text in brackets is ignored. A number that is not a ticket of the feature is an error.
- **`Status:`** one of the triage roles in `triage-labels.md`, or `done`. Status is written on the integration branch only: `done` by `gate.py merge` in the merge commit, `needs-info` and `ready-for-human` by the orchestrating session. A ticket branch never changes it, so the frontier is read from one place.
- **`Touches:`** the shared files or folders the ticket will change, comma-separated: shared CSS, a registry, routing, a manifest, the test or walk helpers. Not every file, only the ones another ticket might also change. Two tickets that touch the same one are not worked at once, and the gate holds the second. Write `*` for a ticket that changes dependencies or the test harness: it runs alone. Write `none` for a ticket that changes no shared file, so the gate knows the line was not forgotten. This is the one place a ticket names paths. Blocking edges are logical: two tickets with no edge between them can still both rewrite the same stylesheet, and that only shows at merge.

### Kind

A fourth header line, `**Kind:**`, says what part a ticket plays in the spec: `foundational`, `walk-tooling`, `acceptance-walk`, `exploration`, `ready-for-human`, `design`, or absent. It is not a status and the frontier never reads it for ordering; `Status:` alone decides what is ready (a `Kind: ready-for-human` ticket also has `Status: ready-for-human`, which the ready gate lets through). `gate.py release` reads it:

- **Every spec has a `foundational` ticket.**
- **A spec whose tickets' `Touches:` lines, or whose own text, name a path under `user_facing` in `docs/agents/local/factory.json` (`user_facing`, with `user_facing_except` carved out) has a ticket of `Kind: acceptance-walk` and one of `Kind: exploration`.** A spec that touches no such path needs neither.
- **`design` marks a review-fix ticket that changes what a user sees.** `gate.py ticket` refuses a review-fix ticket (feature slug ending `-review`) whose diff on the integration branch touches a `user_facing` path unless it is `Kind: design` and the fix spec's Open list has an item naming it (`ticket NN`).

### factory.json

`python3 .claude/factory/gate.py config --keys` lists every key with its type, default and meaning; `config` validates the file. (The gate reads no `kit_prefix`; it is not a key.)

### Release

`python3 .claude/factory/gate.py release <feature>` moves the spec and every `needs-triage` ticket to `ready-for-agent` in one pass, and refuses to run twice. It refuses when the integration branch `feature/<feature>` is not cut from the protected branch's tip (it names both commits), when a rule under Kind fails, or when the spec has a `Brief:` line and the build log has no `spec-against-brief` entry. It replaces the hand edit and commit.

A ticket also cites, by heading, the spec sections it implements. The per-ticket review reads those sections, not the ticket's paraphrase of them.

## Acceptance boxes

- **Every box is something that can be checked**, and says how where that is not obvious.
- **A box ends with its evidence once it has some**: ` — test: <title>`, ` — walk: <title>` and the other kinds in `evidence.md`. The implementer adds it when ticking the box.
- **A box no agent can check is written as needs-human from the start**: `- [ ] <box> — needs-human: <what to judge, and on what>`. Real hardware, paper, an unfamiliar user, legibility. It stays unticked and goes to the user at hand-over with everything else already green.
- **A ticket is done when every box is ticked with evidence or marked needs-human.** `gate.py ticket <feature> <NN>` decides, and `gate.py merge` runs it. A build once closed its tickets with the browser boxes unticked and deferred, and one with nine boxes never ticked at all; the first thing the user clicked failed (2026-11-06).

## The tickets every spec has

- **Before tickets are written, the spec is read against its brief** by one fresh `branch-reviewer` given both: what the brief asks that the spec lacks, contradicts or narrows. Every later gate checks the code against the spec; this is the only one that checks the spec.
- **The spec names its foundational ticket**: the core logic the others read. It is reviewed as soon as it merges, before anything builds on it (`orchestrator.md`).
- **A spec with anything a user sees in a browser has walk tooling before its first user-facing ticket.** If the repo has none, the first ticket builds it: the driver, the shared helper with its guards, and one walk through the thinnest working slice, each guard shown to fail. It is reviewed like a foundational ticket: every later walk rests on it.
- **A ticket with browser boxes names the walk that checks them** (`walkthrough.md`).
- **A spec that changes what a user sees has an acceptance walk**, blocked by every ticket that builds something: one end-to-end journey across the whole spec, keyboard only, run at the fixed viewport and at the smallest one the brief allows.
- **After the acceptance walk, for the same specs, comes the exploration ticket**, blocked by the acceptance walk, with `Touches: *`. It is the last ticket an agent works. It builds nothing new: one exploratory walker per area tries to break the app, and one implementer fixes what they find, starting from each walker's red check (`walkthrough.md` section 5). Its boxes:

  ```
  - [ ] One findings file per area — doc: <tracker>/<feature>/explore/<area>.md
  - [ ] Every defect found is fixed, and the check that found it is in the walk suite and green — check: <the walk suite's name>
  - [ ] Each defect has a row in the escape ledger — doc: docs/agents/local/ledger.md
  ```
- **What only the user can do is one last ticket, `ready-for-human`**, blocked by all the others: the release checks, with a box for each. That status is for this ticket only. A ticket an agent could not finish becomes `needs-triage` (`orchestrator.md`), because the ready gate lets `ready-for-human` through.
- **The gate refuses a blocking cycle**, so no two tickets are each "blocked by every other".

## Review-fix tickets

A whole-branch review's blocking findings become a spec and tickets of their own under the tracker folder `pr-<N>-review/` (or `<feature>-review/` without a pull request), in the same form, each finding restated so the spec stands alone and citing the findings file it came from.
