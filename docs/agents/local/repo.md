# This repo

What is particular to this repo. The other files under `docs/agents/` hold in any repo and are replaced when the kit is updated; the files in `local/` are yours and are never replaced. Every line below is a fact of this repo; a line left blank is a gap an agent will trip on.

## Commands

- **Unit suite.** `.venv/bin/python -m pytest -q`, run from the repo root (tests in `tests/`). Under `gate.py checks` its output goes to the file the gate names on the `output:` path it prints (`unit.txt` in a temporary `factory-gate-*` folder).
- **Walk suite.** `.venv/bin/python walks/run_walks.py` (four workers, then each failure alone; output under `.scratch/<feature>/walks/walks-run.txt`). One walk alone: `.venv/bin/python -m pytest walks/test_needs_review_walk.py -q`. Gate check name: `walks`.
- **Outline a module.** `grep -n '^def \|^class ' <file>.py`
- **The gate's checks.** The suites above, by name, in `docs/agents/local/factory.json`. `python3 .claude/factory/gate.py checks` runs them all.

## Walks

- **Tooling.** Playwright for Python with Chromium (`requirements-dev.txt`; once: `.venv/bin/python -m playwright install chromium`), run by pytest in `walks/`, outside the unit folder (`pytest.ini` points the unit suite at `tests/`). The Streamlit pages are tested in the unit suite through `streamlit.testing.v1.AppTest`, which needs no browser.
- **Helpers.** `walks/helper.py` (the app in a subprocess on a free port over a fresh temporary database, the stand-in registry, the guards: console error, page error, failed or foreign request, sideways scroll; seeded data `seed_queue`) and `walks/conftest.py` (fixtures `make_app`, `make_walk`, `registry`, `viewport`; a walk whose guards tripped is reported FAILED). `walks/standin_registry.py` is the stand-in registry; `walks/serve.py` starts the app against it. A walk is `walk = make_walk(make_app(seed=...))`, then acts through `walk.page` by role and name.
- **Evidence.** `.scratch/<feature>/walks/` (git-ignored): `<walk>-NN-<step>.png`, a `-final` shot of every failed walk, and `walks-run.txt`.
- **Shared client plumbing.** `webapp/static/app.js`, `webapp/static/api.js`, `webapp/static/style.css`, `walks/helper.py`, `walks/conftest.py`, `walks/standin_registry.py`, `walks/serve.py`. A change to one runs the whole walk suite.
- **Areas.** The shell and sidebar; each watchlist tab (`webapp/static/views/`); Find trials (not built yet).
- **Viewports.** 1440 x 900 and 1024 x 768 (every walk runs at both); the acceptance walk adds Playwright's WebKit when that ticket exists. The browser runs in Asia/Tokyo and the server in America/New_York, so a time shifted into the browser's zone shows.
- **Agents running browsers at once.** 1 (a suite run uses four workers).
- **Not checkable by a walk here.** Wording and legibility, Safari, real hardware, the live registry (`walks/fidelity_check.py` is by hand).

## Running a walk

Write `walk = make_walk(make_app(seed=helper.seed_queue))`, `walk.page.goto(app.url)`, act by role and name, assert on what is drawn, `walk.shot("step")`. The stand-in registry's switches are `registry.set("revise")` and so on (its control endpoint, never the app). A new guard or helper change runs `walks/test_walk_guards.py`, which runs deliberately broken pages in `walks/broken/`. A walk that proves an error response declares it first with `walk.expect(status, path)`; the guards then treat that response as expected, and fail the walk if it never comes.

## Stand-ins

Every check in this repo runs against these. A row whose fidelity check starts with "None" is listed for the user at every hand-over (`evidence.md`).

| Stand-in | Stands in for | Fidelity check | Last checked |
|---|---|---|---|
| Stub fetcher and finder (`make_fetcher`, `make_finder` in `tests/conftest.py`) injected by the `api` fixture | The ClinicalTrials.gov client | None yet: no endpoint calls the registry; first live check belongs to the ticket that adds one | never |
| Stand-in registry (`walks/standin_registry.py`) serving the captured NCT03412565 record and two copies, with not-found, server-error, slow, revise and register switches | ClinicalTrials.gov, in the walks | `python walks/fidelity_check.py` fetches NCT03412565 live and compares key paths and types with the fixture (by hand, outside the gate). Covers the single-study lookup only: the search answers (`studies`, `nextPageToken`, `totalCount`) are the stand-in's own and are not compared | 2026-11-08 |
| Chromium, headless, at 1440 x 900 and 1024 x 768 (Playwright) | The analyst's browser | None: Safari and real hardware are the user's at hand-over | never |
| `walks/serve.py` (the walks' start path: `make_server` on a free port over `ctgov.BASE` replaced after import; no `instance.claim`, `--port`, start-up messages) | `python run.py` as a user starts it, in the walks | `tests/test_run.py` runs the real `run.py` and fetches the page; nothing ties `serve.py` to it beyond that | never |
| In-process `make_server` on a free port (the `api` fixture) | `python run.py` as a user starts it | `tests/test_run.py` starts the real `run.py` in a subprocess and fetches the page | 2026-11-08 |

## CI

- **Workflows.** `.github/workflows/deploy.yml` ("Publish the site"): on push to `main` or `master` and on `workflow_dispatch`, runs `python build_site.py site` and deploys the result to GitHub Pages. It runs no tests. There is no pull-request workflow, so nothing runs on a draft.
- **The local gate.** No pre-push hook or other local hook in this repo; `python3 .claude/factory/gate.py checks` is run by hand. No CI step runs the tests, so there is nothing to skip.
- **The dispatch.** `gh workflow run deploy.yml` (publishes the site; not a test run).
- **Gaps against the checklist.** No CI workflow runs the tests, so the test-workflow items of `ci-spend.md` do not apply yet. `deploy.yml` triggers on push to `main` on purpose, because it publishes `main`. Neither of its jobs sets `timeout-minutes`.
