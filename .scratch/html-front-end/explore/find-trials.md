# Exploration: find trials

Run any red script: `.venv/bin/python -m pytest -p walks.conftest .scratch/html-front-end/explore/find-trials/<file> -q` (both viewports). Screenshots are in `.scratch/html-front-end/walks/` (git-ignored), named `<test title>-1440x900-NN-<step>.png`.

## Tried
- Slow search (stand-in `slow`), then leave to Watchlists; slow search then a newer search; slow trial details then leave
- Page beyond the last (page=99, page=11 under the cap), page 10 of 10 (Next disabled), Back/Forward across search, Edit search, resubmit
- Hostile condition text: `C++ & <b>x</b> 100% #1 ?a=b`, accents and CJK and quotes, `a/b/c`, `%2F`, 600 characters unbroken
- Selection: Select 10 on this page, persistence across Next/Previous, Clear, double-click Add, add of three already present, Add with the server stopped (message "Failed to fetch", Add stays enabled)
- Inverted date window (clear error, kept form); bogus phase/status in the address; filter-only address; Phase toggle by Space
- 40 watchlists with 150-character names and an HTML-looking name in the destination picker (no overflow; bar wraps taller)
- Details of a trial not monitored: lowercase ID, unknown ID, garbage, registry 500, double Add, Back to results
- Add by NCT ID: lowercase, padded, spaced, short, empty, injection-like, 400 characters, unknown ID
- Keyboard focus after: search with no field, Search, Next, Edit search, Clear, Add, Dismiss, Clear all, details load, Watch dialog open and Esc
- Both viewports (1440x900, 1024x768)

## Defects
1. A slow registry answer draws over a page the analyst has already left, or over a newer search: after "Searching..." the analyst opens Watchlists; when the answer arrives the Find trials results replace the watchlist while the address still says `#/watchlists/1/needs-review`. A newer search is likewise replaced by the older one's results (address says "nothing", page shows "many"); same for a slow trial detail. Cause: no check that the view is still current before drawing (find.js `render`, registry_trial.js `render`). | steps: search (registry slow), click Watchlists, wait; or search A slow, Back, search B | red script: `find-trials/test_stale_response_overwrites_view.py` (three tests) | `...a-slow-search-does-not-draw-over-the-watchlist-the-analyst-went-to-1440x900-01-after-slow-answer.png`, `...an-older-slow-search-does-not-replace-the-newer-one-1440x900-01-after-old-answer.png`, `...a-slow-trial-detail-does-not-draw-over-the-page-left-1440x900-01-after-slow-detail.png` | blocks a user (the analyst sees the wrong page, can add from it, and the address lies; a reload is the only fix)
2. Keyboard focus falls to the top of the page after each redraw in Find trials: after a search with none of the four fields (error shown), after Next/Previous, after Clear in the action bar, after Add (also Dismiss, Edit search, and submitting a search). The user must Tab from the top of the page again each time. The spec's keyboard rule is focus kept across redraws. | steps: focus the control, press Enter, ask where focus is | red script: `find-trials/test_focus_lost_after_redraw.py` (four tests) | `...focus-stays-in-the-page-after-next-and-previous-1440x900-01-after-next.png`, `...after-clear-in-the-action-bar-...-after-clear.png`, `...after-add-to-a-watchlist-...-after-add.png`, `...after-a-search-with-none-of-the-four-fields-...-after-error.png` | wrong but workable
3. A long query with no spaces (600 characters, e.g. a pasted code) makes the whole page scroll sideways by about 3,800 px (1440) and 4,200 px (1024); the results summary does not wrap. | steps: type 600 `x` in Condition, Enter | red script: `find-trials/test_long_unbroken_query_widens_the_page.py` | `test-explore-a-600-character-condition-does-not-scroll-the-page-sideways-1440x900-01-long-summary.png` | wrong but workable (also trips the walk guard)

## Odd, not wrong
- A page number outside 1..10 in the address (`page=99`, or `page=11` under the cap) answers a 400 and shows "Page must be a number from 1 to 10." with a Retry that can never succeed, and an empty form (the query is not shown). Reached only by editing the address.
- The inverted date window shows its own clear message, but with a Retry button that cannot help.
- After a failed lookup in Add by NCT ID the hint "Next: confirm the trial title, then Add to watchlist." stays beside the error.
- Clear all leaves a displayed "Add a condition..." error in place.
- 150-character watchlist names make the action bar about 154 px tall (wraps; usable).
- Selections are lost on reload (kept only while the page stays open); the spec says "when I leave Find trials and come back", which works.

## Not checked
- Page left open across a server restart (the helper gives each app a fresh port; the stand-in cannot be restarted on the same one)
- The registry answering nonsense (the stand-in has no switch for it)
- Deleting the destination watchlist while results are selected; creating a watchlist from the bar mid-selection
- Watch this search dialog beyond open/Esc (another area); Safari; screen readers; real registry paging tokens and filtering
