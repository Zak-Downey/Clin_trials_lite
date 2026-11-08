# This repo

What is particular to this repo. The other files under `docs/agents/` hold in any repo and are replaced when the kit is updated; the files in `local/` are yours and are never replaced. Every line below is a fact of this repo; a line left blank is a gap an agent will trip on.

## Commands

- **Unit suite.** `.venv/bin/python -m pytest -q`, run from the repo root (tests in `tests/`). Under `gate.py checks` its output goes to the file the gate names on the `output:` path it prints (`unit.txt` in a temporary `factory-gate-*` folder).
- **Walk suite.** None in this repo yet.
- **Outline a module.** `grep -n '^def \|^class ' <file>.py`
- **The gate's checks.** The suites above, by name, in `docs/agents/local/factory.json`. `python3 .claude/factory/gate.py checks` runs them all.

## Walks

- **Tooling.** None in this repo yet: no browser driver or walk runner is installed. The Streamlit pages are tested in the unit suite through `streamlit.testing.v1.AppTest` (`tests/test_app.py`), which needs no browser.
- **Helpers.** None in this repo yet.
- **Evidence.** None in this repo yet; when a walk suite exists, `.scratch/<feature>/walks/`.
- **Shared client plumbing.** Not in this repo.
- **Areas.** Not in this repo.
- **Viewports.** Not in this repo.
- **Agents running browsers at once.** 1.
- **Not checkable by a walk here.** Everything in a browser: with no walk suite, every user-facing behaviour is checked only by the unit suite's `AppTest` runs or by the user.

## Stand-ins

Every check in this repo runs against these. A row whose fidelity check starts with "None" is listed for the user at every hand-over (`evidence.md`).

| Stand-in | Stands in for | Fidelity check | Last checked |
|---|---|---|---|
| Stub fetcher and finder (`make_fetcher`, `make_finder` in `tests/conftest.py`) injected by the `api` fixture | The ClinicalTrials.gov client | None yet: no endpoint calls the registry; first live check belongs to the ticket that adds one | never |
| In-process `make_server` on a free port (the `api` fixture) | `python run.py` as a user starts it | `tests/test_run.py` starts the real `run.py` in a subprocess and fetches the page | 2026-11-08 |

## CI

- **Workflows.** `.github/workflows/deploy.yml` ("Publish the site"): on push to `main` or `master` and on `workflow_dispatch`, runs `python build_site.py site` and deploys the result to GitHub Pages. It runs no tests. There is no pull-request workflow, so nothing runs on a draft.
- **The local gate.** No pre-push hook or other local hook in this repo; `python3 .claude/factory/gate.py checks` is run by hand. No CI step runs the tests, so there is nothing to skip.
- **The dispatch.** `gh workflow run deploy.yml` (publishes the site; not a test run).
- **Gaps against the checklist.** No CI workflow runs the tests, so the test-workflow items of `ci-spend.md` do not apply yet. `deploy.yml` triggers on push to `main` on purpose, because it publishes `main`. Neither of its jobs sets `timeout-minutes`.
