# Area review: the proof and the retirement (walks/, the acceptance walk, the retirement)

Feature: html-front-end. PR #1. Diff read: `git diff 9229115..feature/html-front-end -- walks/ requirements.txt requirements-dev.txt README.md docs/ .github/ .gitignore`, at tip e77cb9c.
Read first: `reviews/02.md`, `02-foundation.md`, `02-followup-2.md` (walk tooling), and the build log's observations. Findings already left there with a reason (serve.py row, fidelity covering only lookup, Chromium row with no fidelity check) are not repeated.

What I ran: the whole walk suite through `walks/run_walks.py` (278 passed, exit 0, 108 s at four workers), and small probe walks of my own in `/tmp` against the real fixtures (`-p walks.conftest`). Each finding says whether it was reproduced or inferred.

Counts: blocking 1, sweep 6, design 2, nit 7.

## Blocking

### B1. The runner's "alone" re-run runs the whole walk suite, so the flake/defect verdict the ready gate reads is wrong
- **What happens.** `pytest()` always passes `"walks"` as a positional argument (`walks/run_walks.py:32`), and the re-run calls `pytest([nodeid], alone)` (`walks/run_walks.py:61`). So the "alone" run collects the whole `walks/` folder plus the node id, runs it serially (no `-n`), and its exit code is the whole suite's. Three things follow:
  1. A walk that only flakes under load is called "red alone" (a defect) if *any other* walk fails in that serial run, and a real defect in one walk makes every flaky walk in the same run "red alone" too. The verdict means "the whole suite was red serially", not "this walk was red alone".
  2. Each failed walk costs a full serial run of the suite. At four workers the suite takes 108 s, so a serial run takes several minutes; two failing walks plus the first run are past the check's `timeout_s: 900` in `docs/agents/local/factory.json`, and the gate's walks check times out instead of reporting.
  3. `evidence.md` ("A red walk is re-run alone once ... The ready gate reads the verdict from the `## Result` section and nothing else") depends on this verdict.
- **To whom.** The orchestrating session and the ready gate. The user gets a wrong defect list at hand-over.
- **How I know.** Reproduced. `pytest walks --collect-only "walks/test_run_walks.py::test_runner_lists_..."` collects 278 tests. The retained re-run `.scratch/html-front-end/walks/alone-test-walk-a-trial-with-simulated-changes-carries-the-simulated-label-on-its-changes-tab-1024x768.txt` ends `2 failed, 113 passed in 114.84s`: a whole-suite run, with the *other* viewport's walk failing in it too.
- **Why the tests miss it.** `walks/test_run_walks.py` says at its top "Lacks: the re-run itself". The two runner tests cover parsing and the exit code only.
- **Class:** blocking. A walk-tooling guard (the flake/defect split) that was never seen giving the right answer for one walk on its own.

## Sweep

### S1. "No horizontal scroll at any step" (ticket 15 box 18) is only measured at screenshots and at the end
- **What happens.** `Guards.measure()` runs only from `Walk.shot()` (`walks/conftest.py:61`) and from `problems()` at the end (`walks/conftest.py:98`). Console and request guards are event-driven and do cover every step; sideways scrolling is sampled. The acceptance journey takes nine shots. States it passes through with no shot are never measured: the New watchlist dialog open, the Add by NCT ID tab and its found card, the Watch this search dialog and its "Search saved" state, the running-check panel, the Dismiss confirmation, the View dismissed list, the copy notice.
- **How I know.** Inferred from the code.
- **Fix direction.** Call `walk.guards.measure()` from `Keys.focus` (every keyboard move) in the acceptance walk, or on every step of the shared helper.
- **Class:** sweep. The box's cited evidence does not reach "any step".

### S2. "Every control reached in the journey" (ticket 15 box 19) checks only the controls the walk aimed at
- **What happens.** `Keys.focus` (`walks/test_acceptance_walk.py:87-98`) presses Tab until the target has focus, then notes only the target (`:97`). The stops Tab passes over on the way are reached but never checked for being a real control, having a name, or having a ring. The second walk's `crawl` covers every stop, but only in five views plus the results page (`:339-344`). The dialogs (New watchlist, Watch this search, the dismiss confirmation), the New matches tab and its bar, Add by NCT ID, the dismissed list and the check panel are never crawled.
- **How I know.** Inferred from the code.
- **Fix direction.** Note every stop inside the `focus` loop, or crawl the dialogs and the New matches tab too.
- **Class:** sweep.

### S3. The stand-in registry ignores every search parameter, the stand-ins row does not say so, and nothing shows a filtered search works against the real registry
- **What happens.** The stand-in reads only `query.cond` ("many", "nothing") and paging (`walks/standin_registry.py:130-145`). `query.intr`, `query.spons` and the whole `filter.advanced` expression (phase, sponsor type, status, start dates; `ctgov.py:202-226`) are thrown away. Its docstring says so. The repo.md row (`docs/agents/local/repo.md:34`) says only that search *answers* are not compared. The stand-in keeps `state.requests`, but no walk reads the search requests (only `test_check_walk.py:117-120` reads lookups). So the walks for ticket 07 (summary line, Edit search keeps every value, zero matches with "Clear optional filters") and the saved-search walks show that the form and summary carry the filters, not that they reach the registry. The fidelity check never runs a search. A `filter.advanced` expression the live registry rejects or misreads passes every check in the gate.
- **How I know.** Inferred from the code. I did not read the unit tests of `search_params` or `api_search`. They may pin the parameters, but they cannot show that the live registry accepts them.
- **Fix direction.** Add a line to the row: "ignores every search parameter but query.cond many/nothing". Add one walk that asserts the registry received the filter. See D1 for the live side.
- **Class:** sweep (row and walk). The live part is D1.

### S4. `docs/agents/local/repo.md` is stale in four places after this branch
- `:18` "Find trials (not built yet)". It is built (tickets 07, 08, 10).
- `:33` stub fetcher/finder row: "None yet: no endpoint calls the registry; first live check belongs to the ticket that adds one". Search, add by ID, check and saved search all call the registry now. The row should say what checks the unit stubs (nothing does), not that nothing needs to.
- `:34` the stand-in registry row lists "not-found, server-error, slow, revise and register switches". It leaves out `fail` (per-ID failure), which the check walks and the acceptance walk use.
- There is no row for the monkeypatched `time.sleep` in the unit suite (`tests/test_api_checks.py:237`, `tests/test_check_trials.py:288`; the pause ticket 14 moved to `time.sleep`). `evidence.md` says "A fake clock in a test of timing is a stand-in, and has a row". The walks run the real sleep, which would serve as its nothing-injected check if the row said so.
- **How I know.** Read against the code.
- **Class:** sweep.

### S5. The walk setup is written down only in repo.md: `requirements-dev.txt` names only Chromium, and the README says nothing about walks
- **What happens.** `requirements-dev.txt:2` says "once: python -m playwright install chromium". The walks check also runs the acceptance walk in WebKit, so someone who follows that file gets a launch error for `webkit-1440x900`. The README's only test line (`README.md`, "Run the tests with `python -m pytest`") leaves out the walk suite, `requirements-dev.txt` and the browser installs. Ticket 14's fresh-environment box ("189 walks passed") was ticked before ticket 15 added WebKit, so it no longer shows that a fresh environment passes `gate.py checks`.
- **How I know.** Read. I did not build a fresh venv.
- **Class:** sweep.

### S6. The Check for updates button is now `aria-disabled`, and no walk presses it while a check runs
- **What happens.** E-001's fix made the button `aria-disabled` (`webapp/static/views/check.js:60-65`). The button still takes clicks, and only `if (!busy)` (`check.js:183`) stops a second start. `test_walk_during_a_check_progress_shows_and_the_queue_and_a_trial_stay_usable` asserts `button.is_disabled()`. Playwright counts `aria-disabled` as disabled, so that assertion holds, but the walk never presses the button, so the guard on the click is unproven. Ticket 03 box 15's walk half ("the button is disabled with its reason") is now held by a different mechanism than the one it was written against. The server-side refusal is unit-tested.
- **How I know.** Inferred. I did not mutate `check.js`, to keep the tree unchanged.
- **Fix direction.** Press the button during the running check and assert that no second check starts and no error banner appears.
- **Class:** sweep.

## Design

### D1. The fidelity check covers the single-study lookup only, and the search path, which carries all the filter logic, has no live check even by hand
- Builds on S3 and on `02-foundation.md` finding 7, which asked only that the row *say* search is not compared (done). This is the next step. `walks/fidelity_check.py` could run one filtered search live (`ctgov.search_params` with a phase, a status and a start-date range) and check three things: the answer is 200, it has the `studies` / `nextPageToken` / `totalCount` shape the stand-in invents (`nextPageToken` an opaque string, not an offset), and it is narrower than the same search without filters. The stand-in's integer `pageToken` (`standin_registry.py:133`) works only because the app never reads the token. Nothing pins that.
- **Class:** design (by-hand check, outside the gate).

### D2. The guards cannot declare an expected network failure, so no walk can prove the stopped-server behaviour
- `Guards.expect(status, path)` covers HTTP statuses only. A `requestfailed` (server stopped) always trips the guard (`walks/helper.py:126`). The trial-page explorer named this ("Helper change needed: a way to declare an expected network failure", `.scratch/html-front-end/explore/trial-page.md`, Not checked). The spec's follow-up list has the wording defect ("Failed to fetch") but not the helper change, so the follow-up's fix cannot get a green walk without it.
- **Class:** design (add it to the follow-up list next to the wording item).

## Nit

### N1. The WebKit acceptance run accepts either copy notice
- `walks/test_acceptance_walk.py:276` waits for `#summary-notice`, which is drawn on success *and* on failure ("The summary could not be copied here...", `summary.js:146`). The clipboard is read only in Chromium. Reproduced: a probe in WebKit 1440 x 900 shows "Summary copied." today, so the box holds for the right reason now. The walk would not notice copying failing in WebKit. Assert the notice text.

### N2. The focus-ring check would pass a control that always has a shadow
- `RING` (`walks/test_acceptance_walk.py`, top) accepts any `boxShadow !== 'none'` or any outline, and never compares the focused state with the unfocused one. It was shown red only by removing the outline everywhere (`red/15-walks-4ac0d37-focus-ring-broken.txt`). No control has a resting shadow today (only `.menu`, which is not a control), so it does no harm yet.

### N3. The Summary walk's data depends on the clock and the week boundary
- `walks/test_summary_walk.py:35` seeds a change "30 minutes ago". Run in the first half hour of a Monday (server zone America/New_York), or of the 1st of a month for This month, it falls outside the period and the counts are off. `:68` `(trials, changes) == (2, changes)` compares `changes` with itself, which `evidence.md` names as an always-true form (it reduces to `trials == 2`).

### N4. The guard tests match a guard's message anywhere in the combined output
- `walks/test_walk_guards.py:61` `"horizontal scrolling" in out`: three broken walks print that phrase. So the message half of the plain sideways-scroll test is satisfied by the other two, and only `failing(...)` ties the result to `test_broken_sideways_scroll`. Match the message inside that test's own failure block.

### N5. "Enter in any field submits the search" is shown for two fields
- `walks/test_find_trials_walk.py:98-109` shows Enter in Sponsor and Intervention, and the acceptance walk shows Condition. The start-date fields under More filters are never shown. The box says "any field".

### N6. The exploration walks exist twice, and their docstrings point at the wrong copy
- Each `walks/test_explore_*` file is a copy of a script still kept in `.scratch/html-front-end/explore/<area>/`. Their `Run:` lines point to the `.scratch` copy (for example `walks/test_explore_find_trials_long_unbroken_query_widens_the_page.py:3`), so a reader runs the copy that is not in the suite. Some names are doubled (`test_explore_dialogs_and_administration_dialogs_and_administration.py`, `test_explore_saved_search_and_new_matches_saved_search_new_matches.py`).

### N7. The stale-response walks depend on timing, and an unidentified flake showed under load
- `walks/test_explore_find_trials_stale_response_overwrites_view.py:24-27` turns `slow` off as soon as "Searching" shows. The race is real only if the app's registry call arrived first. My probe found it did in 30 of 30 runs alone, so the walk does test what it says. Under heavy load it could pass without testing anything; leaving `slow` on until after the navigation removes the race.
- Separately: 1 failure in 32 runs of `test_trial_page_walk.py`, `test_needs_review_walk.py` and `test_check_walk.py` at `-n 4` (44 walks each run). I did not keep that run's output, so I cannot say which walk failed. The build log's 20:31 observation (simulated-label walk, `count()==0` after navigation) is the likely candidate. Its re-run file above shows it failing at both viewports at that time. Not proven.

## Retirement: checked and found clean
- Deleted: `app.py`, `browser.py`, `build_site.py`, `views/*.py`, `web/index.html`, `.github/workflows/deploy.yml` and their four tests. `git grep -i 'streamlit|stlite|build_site|pyodide|pyyaml'` outside `.scratch` and the ADRs finds only the README sentence on the retired site and the test that reads that sentence. `views/` is left on disk with only an untracked `__pycache__` in it.
- `requirements.txt` drops streamlit and pyyaml. Nothing left imports `yaml`.
- The README's claims (`python run.py`, `--no-browser`, `--port N`, `monitor.db` in the folder started from, `MONITOR_DB` with an existing folder, 127.0.0.1 only, a second start points at the first) match `run.py` as read.
- `.gitignore`: dropping `site/` is right. `.venv/` → `.venv` also ignores a `.venv` symlink, which is wanted for worktrees.
- Ledger: `gate.py ledger check` prints "joined". E-001 to E-011 each have a jsonl line.

## Not read
- The per-ticket walks were sampled, not read in full. I read: the acceptance walk, check, all trials (seed and sort), find trials (Enter, summary, paging, zero, error), summary (seed, copy, export), trial page (simulated-label), and the explore walks for find trials, the tab focus and the failed check. Not opened: add by ID, find/select, needs review, new matches, saved search, trial details, watchlist menu, standin_registry tests, and the explore walks for dialogs, summary, saved search, many watchlists and menu keyboard.
- I did not judge the boxes of tickets 03 to 13 one by one against their walks beyond the sample above. The per-ticket reviews own that.
- The unit tests (`tests/`), `.claude/factory/`, the ADRs, CONTEXT.md and `docs/agents/*` other than `local/`.
- A fresh-venv install, the live registry (`fidelity_check.py` was not run), Safari, real hardware.
