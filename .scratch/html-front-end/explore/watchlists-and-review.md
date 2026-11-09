# Exploration: watchlists and review

Run any script: `.venv/bin/python -m pytest -p walks.conftest .scratch/html-front-end/explore/watchlists-and-review/<file> -q` (the `-p` loads the shared walk fixtures, so the guards are on). Screenshots are in `.scratch/html-front-end/walks/` (git-ignored), named `<test-name>-<viewport>-NN-<step>.png`.

## Tried
- Sidebar Enter on a link, tab Enter, Check for updates Enter: where focus lands afterwards.
- Mark reviewed double-clicked: one review only, one history entry (fine).
- Two pages on one trial: A reviews, B (stale) reviews, B undoes; A reloads.
- Malformed addresses (`#/watchlists/abc`, `/0`, `/1.5`, `/99999/summary`, `#/trials/zzz`, `/1/bogus`): all show a clear not-found, no crash.
- 38 watchlists, names with `<script>`, `&amp;`, `<b>`, emoji, Hebrew/Arabic, padded spaces, 200 unbroken characters, a duplicate name (refused with a message): rendered as text, no injection.
- A list of 99 trials: All trials filter by NCT prefix; 59 queue entries all needing review; scroll position restored on Back to; Next trial disabled on the last one.
- Check for updates double-clicked (one run); leaving mid-check and returning (status and button recovered); slow registry; registry answering 500 for every trial.
- Server stopped before Mark reviewed, and during a check.
- Typed filter and sort on All trials while a check finishes.
- Keyboard: trial menu, watchlist menu, Escape, Rename dialog open and Escape, Remove from this list, its Undo.
- Unbroken 200-character name across Needs review, All trials, New matches, Summary, trial page, Find trials, first-use.
- Both viewports ran for every script; findings below hold at 1440 x 900 (the red scripts were run there; the 1024 run was not read separately).

## Defects
1. A watchlist name with no break points (a long code or URL) makes the page scroll sideways: by 1014 px on an empty watchlist's page (first-use heading), by 376 px on a trial page (the "Back to <name>" link), by 448 px after "Remove from this list" (the "Removed from <name>" banner). | Rename or create a watchlist with 200 "x"; open it empty; or open a trial in it. | red script: `explore/watchlists-and-review/test_long_name_overflow.py`, both tests | `.scratch/html-front-end/walks/test-walk-an-unbroken-name-does-not-widen-the-first-use-page-1440x900-01-first-use.png` (the trial-page shot is `...widen-the-trial-page-1440x900-*-final.png` if the walk wrote one) | wrong but workable (breaks the sideways-scroll guard, spec story 4 spirit)
2. Keyboard focus falls to the page after "Remove from this list" and again after its Undo, and after a Check for updates finishes. A keyboard user has to tab in from the top. | Trial menu, Enter on Remove from this list; Enter on Undo. Or focus Check for updates, Enter, wait for "Check complete". | red script: `test_focus_and_state_kept.py`, `test_walk_focus_is_not_lost_after_remove_from_this_list_and_its_undo`, `test_walk_focus_is_not_lost_when_a_check_finishes` | `.scratch/html-front-end/walks/test-walk-focus-is-not-lost-when-a-check-finishes-1440x900-01-after-check.png` | wrong but workable
3. A filter typed on All trials, and a changed Sort, are cleared when a running check finishes (the tab redraws). Spec story 8: what I am reading does not move. | All trials, type a filter, choose Sort "Trial status", press Check for updates, wait for "Check complete". | red script: `test_focus_and_state_kept.py`, `test_walk_a_typed_filter_and_sort_survive_a_check_finishing` | `.scratch/html-front-end/walks/test-walk-a-typed-filter-and-sort-survive-a-check-finishing-1440x900-01-after-check.png` | wrong but workable
4. After a check in which every trial failed, the header changes from "Not checked yet" to "Last checked <now>" and, with an empty queue, the card reads "All caught up. No changes awaiting review. Last checked <now>." The status panel above says "Check incomplete", but the card and header read as an all-clear (spec stories 20 and 22: a failure is never an all-clear). The per-trial table is right (keeps the old success time and shows the warning). | Open "Quiet" (never checked), make the registry fail, press Check for updates. | red script: `test_failed_check_is_not_an_all_clear.py` | `.scratch/html-front-end/walks/test-walk-a-check-where-every-trial-failed-does-not-claim-a-last-checked-time-1440x900-01-failed-check.png` | wrong but workable (the "last checked" meaning may be a design call: last attempt versus last success; the implementer may decide)

## Odd, not wrong
- After a navigation by keyboard (Enter on a sidebar link or a watchlist tab) focus is on the page, not on the new content. Browsers treat a route change like a page load, so this is probably acceptable; the acceptance walk does not require otherwise.
- The trial page menu button keeps focus when the menu opens; the watchlist menu moves focus to its first item. Inconsistent, both work.
- A stale second page (A already reviewed) that presses Mark reviewed is told "3 changes marked reviewed. This trial stays open." with an Undo, though nothing was marked; the history records nothing and the counts are right. Harmless.
- With the server stopped, the user sees the browser's raw "Failed to fetch" (in the banner, the status area and the view), with no hint that the app has stopped.
- `#/watchlists/abc` is rewritten to `#/watchlists/NaN/needs-review`.
- Creating a watchlist from "+ New watchlist" leaves the analyst on the current watchlist and gives no confirmation beyond the new sidebar row.
- With 38 watchlists the sidebar is as tall as the page (it scrolls with it; the New watchlist button is far down). Works.
- The stand-in registry's lookup regex for the 134 "many" studies only reaches NCT10000099 (a stand-in quirk, not the app).

## Not checked
- Safari, real hardware, screen readers, real registry.
- 1024 x 768 was run but I did not read the screenshots one by one; only layout guards and assertions apply there.
- Summary, New matches, Find trials, dialogs beyond Rename (other walkers' areas).
- A restart of the server with a page left open (the walk helper cannot restart the app on the same port).
- Times on a day boundary between the Tokyo browser and the New York server.
