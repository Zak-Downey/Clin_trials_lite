# 04: The map of the pages, and the test that keeps it current

**What to build:** `docs/agents/local/walk-map.json`, this product's map, and the function that reads it. The map holds `shared` (files every page depends on), `always` (walk files that run in every picked run: the walk-guard tests and the acceptance walk), `areas` (each with a name, the source files that belong to it and the walk files that cover it) and `none` (files that reach no walk: records, docs, the unit tests). Files are paths or glob patterns. Start from the lists "Areas" and "Shared client plumbing" in `repo.md` and from what each walk file opens; when in doubt about a file, put it in `shared`, where the cost is time. The function that reads a map and says what is wrong with it is a kit file and names nothing of this product: a walk file in neither `always` nor an area; a file git tracks that `shared`, an area or `none` does not place; a pattern that matches nothing; a listed walk file that does not exist; an area with no walk. A unit test runs it on this repo's map, so a new source file or walk that the map does not place turns the ordinary checks red. The two prose lists in `repo.md` give way to one line that points to the map and says how to add to it. Spec: `.scratch/kit-phase-3/spec.md`, "The map" and "The map is kept current by a cheap test".

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Red first: each fault named above, in a hand-made map over a small repo in a temporary folder, is reported in words that name the file and the fault
- [x] Red first: this repo's map is read by a unit test, which fails when a walk file is taken out of it and when a new file is added under `webapp/` without a place
- [x] Every walk file and every tracked file of this repo is placed, and the comments say which files went to `shared` out of doubt
- [x] `repo.md` points to the map in place of the two lists, and `python3 checks.py` ends green

## Comments

**Built.** `walk_map.py` (kit file, names nothing of this product): `read(root, path=MAP)`, `problems(the_map, root, walks=WALKS, files=None)` (one line a fault, naming the file or area), `matches(path, patterns)`, `repo_files(root)` (tracked files still present plus untracked files git does not ignore). Patterns are fnmatch from the repo root, so `*` crosses `/`. A walk file is `walks/test_*.py`; it is placed by `always` or an area's `walks`, every other file by `shared`, an area's `files` or `none`. Tests: `tests/test_walk_map.py` (seven on hand-made maps over small git repos, each seen red first; three on this repo's map, red before the map existed).

**The map.** `docs/agents/local/walk-map.json`: `always` is the walk-guard tests and the acceptance walk; eight areas (the seven of the old prose list, plus the walks' own tooling for `test_run_walks.py`, `test_fidelity_check.py` and `test_standin_registry.py`); a walk file that opens several areas is listed in each, and a source file used by two or three areas is listed in each (`registry_trial.js`, `saved_search.js`, `menu_keys.js`). `none` holds `.scratch/*`, `docs/*`, `tests/*`, `.claude/*`, `.github/*`, `*.md`, `ruff.toml`, `.gitignore`, and the kit and command-line scripts no walk runs (`run.py`, `explore.py`, `handover.py`, `prove.py`, `walk_map.py`). The map file itself is under `docs/*`, so in `none`.

**Went to `shared` out of doubt** (beyond the old "Shared client plumbing" list, which all went there with `walks/run_walks.py` and `walks/__init__.py`):
- `webapp/static/index.html`; `views/tabs.js` (the tab bar of every watchlist tab); `views/check.js` (the header, mounted on every watchlist page); `views/watchlist_menu.js` (imported by `check.js`); `views/trial_address.js` (links to a trial from four views and `app.js`); `views/dialog.js` and `views/new_watchlist.js` (imported by four or five views).
- The server's own modules: `webapp/__init__.py`, `server.py`, `routes.py`, `errors.py`, `times.py`, `instance.py`; and the endpoints several pages call: `api_watchlists.py` (the sidebar), `api_membership.py` (adding from Find trials, New matches and the trial page), `api_saved_search.py` (the banner on every watchlist page), `api_checks.py` (Check for updates, used by many walks).
- The Python the server or the walks' seeding imports: `storage.py`, `monitor.py`, `display.py`, `diff.py`, `ctgov.py`, `medical_affairs.py`, `briefing.py`, `simulate.py`; `tests/fixtures/NCT03412565.json` (the stand-in registry serves it).
- `checks.py` (it holds the walks check's command), `pytest.ini`, `requirements.txt`, `requirements-dev.txt`.
- Placed in one area rather than `shared`: `api_summary.py` (Summary), `api_search.py` (Find trials), `api_new_matches.py` (New matches), `api_trials.py` (the trial page).
