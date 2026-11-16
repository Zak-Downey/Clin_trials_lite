# Clin_trials_lite

## Agent skills

### Issue tracker

Issues live as markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default canonical labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Building

- **Checks.** `python3 checks.py` runs every check (the unit suite, the pattern rules, the browser walks), prints one line per check and exits non-zero when any is red. `python3 checks.py unit` runs one by name. Nothing is called working until this is green.
- **A build** is `/implement-spec` (`.claude/skills/implement-spec/SKILL.md`): one ticket at a time, on the feature branch.
- **Hand-over.** `python3 handover.py <feature>` builds the one page the owner judges a build from.
- **A correction becomes a check.** When the owner or a reviewer finds a defect the checks missed: first add a check that is red because of it (a unit test, a walk, or a pattern in `checks.py`, whichever is cheapest and can see it), then fix it, then append one line to `docs/agents/local/escapes.jsonl` naming that check.
- **This repo's commands, walk tooling and stand-ins:** `docs/agents/local/repo.md`.
