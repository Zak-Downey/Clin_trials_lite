# This repo

What is particular to this repo. The other files under `docs/agents/` hold in any repo and are replaced when the kit is updated; the files in `local/` are yours and are never replaced. Fill in each line below. A line that still says "Fill in" is a gap an agent will trip on.

## Commands

- **Unit suite.** Fill in: the command, and where its output goes.
- **Walk suite.** Fill in: the command that runs every walk across workers, and how to run some by name.
- **Outline a module.** Fill in: for example `grep -n '^export '` for JavaScript, `grep -n '^def \|^class '` for Python.
- **The gate's checks.** The suites above, by name, in `docs/agents/local/factory.json`. `python3 .claude/factory/gate.py checks` runs them all.

## Walks

- **Tooling.** Fill in: the browser driver (a dev dependency only), the runner, and where walks live (outside the fast test folder, so the fast suite needs no browser).
- **Helpers.** Fill in: the shared walk helper; how it starts the app on its own free port with a fresh temporary copy of the fixture data; which stand-in replaces each external service and how the app is pointed at it; one browser per worker; the guards; the screenshot helper.
- **Evidence.** Fill in: where results files (tracked) and screenshots (git-ignored) go, normally `.scratch/<feature>/walks/`.
- **Shared client plumbing.** Fill in: the files whose change runs the whole walk suite.
- **Areas.** Fill in: the four to six areas the exploratory walkers split into, one walker each.
- **Viewports.** Fill in: the fixed viewport, and the smallest one the brief allows.
- **Agents running browsers at once.** Fill in: a number at or below this machine's cores.
- **Not checkable by a walk here.** Fill in: what only the user can check in this product.

## Stand-ins

Every check in this repo runs against these. A row whose fidelity check starts with "None" is listed for the user at every hand-over (`evidence.md`).

| Stand-in | Stands in for | Fidelity check | Last checked |
|---|---|---|---|
| Fill in | | | |

## CI

- **Workflows.** Fill in: each workflow file, what it runs, and whether it runs on a draft. Or: none yet.
- **The local gate.** Fill in: the hook and commands that run before a push, and how a step CI has already passed on this commit is skipped.
- **The dispatch.** Fill in: the command that runs the expensive workflow on a draft.
- **Gaps against the checklist.** Fill in: any item of `ci-spend.md`'s checklist a workflow does not follow yet, and why.
