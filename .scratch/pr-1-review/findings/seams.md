# Seams read: html-front-end, PR #1 (wave two)

Tip read: `e77cb9c` (feature/html-front-end). Diff: `git diff 9229115..feature/html-front-end -- . ':!.scratch'`. I read the five wave-one files in `.scratch/pr-1-review/findings/` first and do not repeat what they found. Where a seam finding extends a wave-one finding, I say which one. I also read the per-ticket reviews named there (`reviews/01*`, `02*`) through the wave-one summaries, plus the spec's Further Notes list of logged follow-ups.

Probes: one scratch walk file outside the repo, `/tmp/seams/test_probe_seams.py`, run with `.venv/bin/python -m pytest -p walks.conftest <file> -q -s --rootdir=.` from the repo root, with the guards on, at both viewports. Output: `/tmp/seams/run1.txt`, `run2.txt` and `run3.txt`. "Reproduced" below means the probe failed at both 1440 x 900 and 1024 x 768 for the reason given.

Counts: blocking 0 · sweep 4 · design 1 · nit 2

---

## Sweep

### 1. When a check finishes, the New matches tab drops the analyst's selection, the pending Dismiss confirmation and the View dismissed sub-view
- **What happens.** The analyst opens New matches, presses Check for updates, and ticks matches while the check runs. When the check finishes, the tab redraws from scratch. The ticks are cleared and the action bar disappears. A Dismiss that was waiting for "Yes, dismiss N" is gone too, and an open View dismissed list falls back to new matches.
- **Why it is a seam.** `check.js` hands off to `ctx.refresh` (`app.js:177-181`), which calls the tab's `render` again. `new_matches.js:15-20` keeps `selected`, `showing` and `pending` as locals of `render`, so every refresh starts them empty. Ticket 16 fixed this class for All trials (exploration defect 3: filter and sort kept per watchlist) and wave one found it on Summary (client finding 1). The client reviewer did not read `new_matches.js`, and the discovery reviewer did not read `app.js`'s refresh, so this third case fell between them. Story 8 ("never switch tabs by itself when a check … changes the counts, so that what I'm reading doesn't move") and story 78 (decide on several at once) both apply. A check is exactly when new matches arrive.
- **Who.** An analyst triaging matches while a check runs, which is the moment new matches arrive.
- **Where.** `webapp/static/views/new_matches.js:15-20`, `webapp/static/app.js:177-181`.
- **How I know.** Reproduced (`test_probe_new_matches_selection_survives_check`, stand-in `slow` at 1 s). The bar read `'1 selected\nDismiss 1\nAdd 1 to watchlist'` before completion and was hidden afterwards, and the box was unchecked (`run3.txt`).
- **Fix direction.** The All trials fix: keep the tab's state per watchlist at module level, or have `refresh` redraw only the counts. One fix for Summary, New matches and any later tab is to make `refresh` re-read the state the view keeps, not rebuild the view.

### 2. Adding trials from New matches leaves the watchlist header at "0 trials monitored · Check for new matches"
- **What happens.** Take a watchlist with a saved search and no trials yet (story 82). The analyst adds a match from New matches. The tab strip updates to "All trials 1", because `new_matches.js` re-reads `/api/watchlists` for its own tabs. The header that `check.js` owns does not update: it still reads "0 trials monitored", and the button still says "Check for new matches". Pressing that button runs a full check of the new trial as well (`api_checks.start` reads membership fresh), so the label is wrong as well as stale. This holds until the analyst leaves the watchlist.
- **Why it is a seam.** The header's `current` is captured by `mount` (`check.js:30`) and only renewed when a check finishes (`check.js:151,168`). `new_matches.js:22-27` refreshes its own copy and the sidebar, through `reviewchange`, and nothing tells `check.js`. Each module refreshes what it draws, and the header belongs to neither.
- **Who.** Every analyst who fills a new watchlist from its saved search, which is the path stories 24 and 82 exist for.
- **Where.** `webapp/static/views/check.js:30,34-58`, `webapp/static/views/new_matches.js:22-27,123-130`.
- **How I know.** Reproduced (`test_probe_header_after_adding_from_new_matches`): `'0 trials monitored · Not checked yet' -> '0 trials monitored · Not checked yet' | button 'Check for new matches' -> 'Check for new matches' | tabs 'Needs review 0\nAll trials 1\nNew matches 1\nSummary'` (`run1.txt`).
- **Fix direction.** Have the header listen for the same `reviewchange` event the sidebar uses (re-read the overview and redraw), or route after an add that changes the trial count.

### 3. A saved search with more than one lead sponsor type loses all but the first when it is edited
- **What happens.** The domain, the API and the address all carry `sponsor_types` as a list. `as_query`, `_for_page`, `_read_query`, `toParams` and `readQuery` keep every value, and the results summary shows "Industry or NIH". The form's Lead sponsor type is a single `<select>`. It shows `q.sponsor_type[0]` (`find.js:86`) and reads back at most one value (`find.js:120`). Manage saved search, then Edit search, then Edit search on the results, then Search trials, silently narrows the query to Industry. Watch this search, then Replace saved search, would store the narrower query. Story 54 asks for More filters "showing my selections in full when open". Story 76 says Edit search "replaces the query only when I save it", and here what gets saved is not what was opened.
- **Why it is a seam.** The retired Streamlit page offered sponsor type as a multiselect (`git show 9229115:views/search.py:137`, `st.multiselect`). The spec keeps existing `monitor.db` files "with their data intact" (Implementation Decisions, "An existing database file is upgraded in place"). So a saved search made in the old app reaches the new page in a shape the new form cannot hold. The server accepts lists, the page assumes one value, and neither side says so. Statuses and phases are multi-valued in both the old and the new form, so only this axis is affected.
- **Who.** An analyst upgrading from the Streamlit app whose saved search names two sponsor classes, or anyone following a shared address with two `sponsor_type` values.
- **Where.** `webapp/static/views/find.js:84-86` (render), `:120` (read); compare `webapp/api_saved_search.py:15-24` and `monitor.as_query`.
- **How I know.** Reproduced (`test_probe_edit_saved_search_keeps_both_sponsor_types`, seeded through `monitor.remember_search` with `["INDUSTRY", "NIH"]`): `'Industry or NIH' -> 'Industry'`, address after `#/find/1?cond=myeloma&sponsor_type=INDUSTRY&page=1` (`run2.txt`). The upgrade path was not driven from a real old database file. It is inferred from the old view's code.
- **Fix direction.** Make the sponsor type a group of checkboxes like Trial status, or show the extra values and refuse to drop them silently.

### 4. An inverted start-date window is shown as a registry failure with a Retry that can never succeed
- **What happens.** The analyst opens More filters, enters Study started from 2025-01-01 and to 2020-01-01, and presses Search trials. The server refuses with 400 `bad_dates` ("The start-date window ends before it begins … Swap the two dates."). The page shows that message in the registry-error box with a Retry button (story 61's treatment), not beside the date fields. Retry re-sends the same query and fails the same way.
- **Why it is a seam.** The server distinguishes `nothing_asked`, `bad_dates`, `bad_page` and `registry_error` (`api_search.py:20,30,36`). The page's search path never reads `err.kind` (`find.js:296-302`): every failure becomes "network blip, Retry". Server finding 4 says the kind is chosen by matching message text. Read together, the "distinct error kinds … the API maps to messages" contract is produced carelessly on one side and not consumed on the other. Only the client-side `named()` check keeps the four-field rule (story 57) working.
- **Who.** An analyst who types the dates the wrong way round.
- **Where.** `webapp/static/views/find.js:296-302`; `webapp/api_search.py:27-30`.
- **How I know.** Reproduced through the address (`test_probe_inverted_dates_show_as_registry_error`, with the 400 declared by `walk.expect`): the box read the swap-dates message followed by Retry, with one Retry button (`run1.txt`). I did not drive it through the date inputs, but the form submits by setting that same address (`find.js:288-289`).
- **Fix direction.** On `bad_dates`, re-open the form with the message beside the dates and no Retry. Keep Retry for `registry_error` only.

## Design

### 5. The app starts on a new port each time, so remembered tabs and saved links do not outlive a restart
- **What happens.** `run.py` defaults to `--port 0` (a free port). The page's origin is therefore new on every start. Remembered tabs (`app.js:83-88`, `localStorage` `tab:<id>`) are per origin and start empty after each restart. Any bookmark or link the analyst kept ("links can be opened in a new tab", Implementation Decisions; story 6) points at a port nobody listens on. Within one run, reload and Back work as specified.
- **Why it is a seam.** Story 1 ("don't have to remember a URL or a port") chose the free port. Story 7 ("stay on any tab I chose explicitly when I come back to it") and the address-as-state decision assume an address that lasts. Each decision is reasonable alone, but together the tab memory only lasts until the next start.
- **Where.** `run.py:28`, `webapp/static/app.js:83-88`.
- **How I know.** Inferred from the code. Not driven, because the walks start through `serve.py`, not `run.py`.
- **Decision needed.** Either a fixed default port (with the second-start redirect `instance.claim` already provides), or accept it and say in the README that links last for one run.

## Nit

### 6. "View details" on a trial the app already monitors opens the registry page, which has no Changes tab and does not flag unreviewed changes
- Find results and New matches always link to `#/registry/<id>` (`find.js:178`, `new_matches.js:187-189`). For a trial that another watchlist holds, that page fetches the live record and draws the sections with no unreviewed flags (`api_membership.registry_trial` passes no `changed` set). It offers no way to the trial's own page until the analyst presses Add. It says "In: Myeloma" (`registry_trial.js:47`), so it is not hidden. But the live values can differ from what the monitor has recorded, and story 47's "never hidden inside a collapsed section" holds only on the other page. The search rows carry no membership, so the page cannot choose the link. Read, not driven.

### 7. A watchlist address that no longer exists shows only the server's sentence
- After Delete watchlist, browser Back (or a stale link) returns to `#/watchlists/<deleted>/needs-review`. The view is replaced by "There is no watchlist 5." with no sidebar highlight and no way forward except the sidebar (`app.js:187-192`). The server's `watchlist_not_found` kind is not read. The route could send the analyst to the first watchlist, as `deleted` already does (`app.js:176`). Read, not driven.

---

## Seams checked and found sound
- **Error envelope.** `ApiError.body()` gives `{"error": {"kind", "message"}}` and `api.js` reads exactly that. Every handler error passes through the dispatcher's three `except` arms.
- **Change counting.** The queue (`monitor.needs_review`), the trial page (`monitor.history`), the Summary and the CSV (`briefing._detection`) all fold with `diff.fold_moves` one check at a time, so "6 unreviewed field changes" and "Review covers all N changes" count the same unit. Review by ID is scoped to the trial in SQL (`storage.review_changes`).
- **Times.** Every stamp the page shows goes through `webapp/times.local` (the server's zone, named), and `api.js when()` formats the wall clock without shifting it into the browser's zone. Summary bounds use the same machine zone (`briefing.summarise(zone=None)`, `date.today()`). The zone-name caveat is standards (c).
- **Concurrent checks of a trial held by two watchlists.** `monitor.check` reads the latest snapshot after the fetch returns and the lock is retaken, so two runs fetching the same trial do not record its changes twice.
- **Saved-search round trip.** Page axis names to domain axis names and back (`_for_page` / `_read_query`), apart from finding 3's sponsor type.
- **Watchlist ids** are `AUTOINCREMENT` (and were before this branch), so a deleted id is never reused. The in-memory check runs, `localStorage` tab keys and orphan rows (discovery S2) cannot attach to a new watchlist.
- **Registry functions in production.** `make_server(db)` leaves `fetch`, `find` and `find_page` as `None`, and every caller falls back to the `ctgov` function, which reads `ctgov.BASE` at call time, so `serve.py`'s replacement reaches all three.

## Not read
- `webapp/static/style.css`, `index.html`, `menu_keys.js`, `watchlist_menu.js` beyond the menu call sites, `all_trials.js` and `needs_review.js` beyond their heading and filter lines, and `saved_search.js` beyond the Manage and Edit search lines.
- `briefing.as_text` and `as_csv` bodies, `display.detail_sections`, `medical_affairs`, `diff` beyond `fold_moves`, `simulate.py` beyond its stamps, and the storage migrations.
- The unit tests and the walk files, beyond the New matches walk's seed (which my probes reuse). I ran no full suite, only the four probes above.
- `.claude/factory/`, `docs/agents/local/factory.json`, the ADRs, `CONTEXT.md`, the design PDF and pages.
- An upgrade from a real Streamlit-era `monitor.db` (finding 3 seeds the shape directly), `run.py` across a restart (finding 5), WebKit, Safari and the live registry.
