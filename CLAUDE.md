# Clin_trials_lite

## Agent skills

### Issue tracker

Issues live as markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default canonical labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Building

- **Checks.** `python3 checks.py` runs every check (the read of the code for common mistakes, the pattern rules, the defect log, the unit suite, the browser walks), prints one line per check and exits non-zero when any is red. `python3 checks.py unit` runs one by name. Nothing is called working until this is green. Never delete, skip or weaken a check to get it green; a check changes only when the spec changed the behaviour it checks, and the commit message says so.
- **Seams are settled; a spec does not ask the owner.** Pages are tested through the walks (`walks/`), the API and domain through the `api` fixture (`tests/`). A ticket that changes what a page shows adds or changes a walk for it, red first.
- **No comments in the code.** Say it in a name, or in a test that fails without it: a comment is checked by nothing. The `patterns` check is red on any comment it does not let through; `python3 checks.py --comments` lists them, and `docs/agents/local/repo.md` says what is let through.
- **Standards.** `CODING_STANDARDS.md`: each line came from a defect that got past the checks.
- **A build** is `/implement-spec` (`.claude/skills/implement-spec/SKILL.md`): one ticket at a time, on the feature branch.
- **Hand-over.** `python3 handover.py <feature>` builds the one page the owner judges a build from.
- **When the owner accepts a build:** the build already pushed its branch and opened a draft pull request (the builder never marks it ready, pushes to `main` or merges). Mark the draft ready (`gh pr ready`) and give them the link; the owner merges it on GitHub. Marking it ready starts no run, so there is nothing to wait for; if the page said GitHub had not passed, say so again with the link. If the build could not open the draft, push the branch and open the pull request now, and say that the `checks` run has started and to wait for it before merging. When the owner turns one down, close the draft and say so; delete no branch until they say to.
- **A correction becomes a check.** When a defect turns up after a build was handed over (the owner using the product, or a later read of the code): first add a check that is red because of it (a unit test, a walk, or a pattern in `checks.py`, whichever is cheapest and can see it), then fix it, then append one line to `docs/agents/local/escapes.jsonl` (`id`, `date` as YYYY-MM-DD, `feature`, `defect`, and `check`: the file, or `file::test`, that now catches it). The `escapes` check is red when a new line names no check that exists.
- **This repo's commands, walk tooling and stand-ins:** `docs/agents/local/repo.md`.
