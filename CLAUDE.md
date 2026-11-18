# Clin_trials_lite

## Agent skills

### Issue tracker

Issues live as markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default canonical labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Building

- **Checks.** `python3 checks.py` runs every check (the pattern rules, the defect log, the unit suite, the browser walks), prints one line per check and exits non-zero when any is red. `python3 checks.py unit` runs one by name. Nothing is called working until this is green. Never delete, skip or weaken a check to get it green; a check changes only when the spec changed the behaviour it checks, and the commit message says so.
- **Seams are settled; a spec does not ask the owner.** Pages are tested through the walks (`walks/`), the API and domain through the `api` fixture (`tests/`). A ticket that changes what a page shows adds or changes a walk for it, red first.
- **Standards.** `CODING_STANDARDS.md`: each line came from a defect that got past the checks.
- **A build** is `/implement-spec` (`.claude/skills/implement-spec/SKILL.md`): one ticket at a time, on the feature branch.
- **Hand-over.** `python3 handover.py <feature>` builds the one page the owner judges a build from.
- **When the owner accepts a build:** push the feature branch, open a pull request and give them the link; the owner merges it on GitHub. With the link, say that the `checks` run has started on GitHub and to wait for it before merging; do not call the build safe to merge. When the owner turns one down, the branch stays until they say to delete it.
- **A correction becomes a check.** When a defect turns up after a build was handed over (the owner using the product, or a later read of the code): first add a check that is red because of it (a unit test, a walk, or a pattern in `checks.py`, whichever is cheapest and can see it), then fix it, then append one line to `docs/agents/local/escapes.jsonl` (`id`, `date` as YYYY-MM-DD, `feature`, `defect`, and `check`: the file, or `file::test`, that now catches it). The `escapes` check is red when a new line names no check that exists.
- **This repo's commands, walk tooling and stand-ins:** `docs/agents/local/repo.md`.
