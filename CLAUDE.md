# Clin_trials_lite

## Agent skills

### Issue tracker

Issues live as markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default canonical labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

<!-- software-factory:start (managed by the kit; edit the kit, not this block) -->
## Software factory

How builds are run in this repo. Read the file for your role, not all of them.

- **Orchestrating a build** (the main session running `implement-spec`): `docs/agents/orchestrator.md`.
- **Dispatched as a subagent**: your role file under `.claude/agents/` is your instructions, and names what else to read.
- **Every agent**: tool, git, worktree and shell facts in `docs/agents/every-agent.md`; this repo's commands, walk tooling and stand-ins in `docs/agents/local/repo.md`.
- **Writing or changing tickets**: `docs/agents/tickets.md`.
- **Reference**: what counts as evidence, `docs/agents/evidence.md`; browser walks, `docs/agents/walkthrough.md`; CI minutes, `docs/agents/ci-spend.md`; what escaped and what each gate found, `docs/agents/local/ledger.md`.
- **Mechanical rules are enforced, not described.** `.claude/factory/guard_bash.py` refuses the commands listed at its top. `python3 .claude/factory/gate.py` gives the frontier, says whether a ticket may be marked done, and is the ready gate.

### Gate commands

`python3 .claude/factory/gate.py` with no word lists them all. The ones an orchestrating session uses: `config` (validates `docs/agents/local/factory.json`), `checks` (runs every configured suite), `frontier <feature>` (what is ready), `ticket <feature> <NN>` (may this ticket be marked done), `red <feature> <NN> <check>` (writes the run in which a new check failed), `merge <feature> <NN> <branch>` (merges a ticket and runs every suite on the merged tree), `release <feature>` (moves the spec and its `needs-triage` tickets to `ready-for-agent`) and `ready` / `handover` (the ready gate and the user's list).
<!-- software-factory:end -->
