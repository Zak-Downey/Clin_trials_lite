# Area read: client shell and the watchlist and trial views

Tip read: `e77cb9c` (feature/html-front-end). Diff: `git diff 9229115..feature/html-front-end -- webapp/static/`, limited to `index.html`, `app.js`, `api.js`, `focus.js`, `style.css` and `views/` needs_review, all_trials, check, tabs, trial, summary, watchlist_menu, dialog, menu_keys, new_watchlist.

Read first: `reviews/01*.md`, `reviews/02*.md` (no per-ticket review exists for tickets 03 to 16 in my area), `explore/watchlists-and-review.md`, `explore/trial-page.md`, and the build log's `observation` lines. Findings already decided there are not repeated unless the branch shows the reason no longer holds.

Probes: two scratch walk files outside the repo, `/tmp/rv-client/test_probe_client.py` and `/tmp/rv-client/test_probe_client2.py`, run with `.venv/bin/python -m pytest -p walks.conftest <file> -q -s --rootdir=.` from the repo root, with the guards on, at both viewports. Output: `/tmp/rv-client/run1.txt` and `/tmp/rv-client/run2.txt`. "Reproduced" below means one of these probes failed at both 1440 x 900 and 1024 x 768 for the reason given. "Inferred" means I read it in the code and did not run it.

Counts: blocking 1, sweep 5, design 1, nit 4.

## Findings

1. **When a check finishes, the Summary jumps back to This week while the address still says This month.** | blocking
   - What happens: the analyst opens Summary, picks This month (or applies Custom dates), then presses Check for updates. When the check finishes, the tab redraws with This week pressed and the week's numbers. The address still reads `?period=month`, so a reload shows the month again. Any Custom dates the analyst was typing are lost too. This is the same class as exploration defect 3 (All trials filter and sort cleared when a check finishes). Ticket 16 fixed that one under story 8 and row 2/F, and the same rule applies here.
   - Where: `webapp/static/app.js:163`. The `draw` closure captures `hashQuery` at route time. `summary.js:78` (`remember`) moves the period with `history.replaceState`, which fires no `hashchange`, so `refresh` (`app.js:177-181`) redraws the Summary from the old query.
   - Who: an analyst preparing a briefing from a month or custom range who checks for updates first.
   - How I know: reproduced (`test_probe_summary_period_survives_check`). Before the check the heading read "1–30 Nov 2026 · 2 trials · 6 field changes". After it read "2–8 Nov 2026 · 2 trials · 9 field changes", with pressed `['This week']` and hash `#/watchlists/1/summary?period=month`.
   - Proposed fix direction: in the refresh closure, read the period from `location.hash` and not from the captured value, or keep it per watchlist as `all_trials.js` now does.

2. **A slow answer for a view the analyst has already left still draws over the newer view.** | sweep
   - What happens: the analyst opens a trial, then goes elsewhere (the sidebar, Back, Next trial twice) before the trial's data arrives. The trial page then replaces the view they moved to. The address names one place and the page shows another. Mark reviewed on that page acts on the trial shown, so the data stays correct, but the analyst is not where the address says. Ticket 16 fixed this for Find trials ("stale answers dropped"). The watchlist and trial views did not get the same treatment. `route()` passes no `alive()` to `renderTrial`, `renderQueue`, `renderAll` or `renderSummary`, and each of them calls `root.replaceChildren` after its `await`. The `generation` check in `route()` guards only the error path (`app.js:188`).
   - Where: `webapp/static/app.js:141`, `app.js:172`; `views/trial.js:14,42`; `views/needs_review.js:14-16`; `views/all_trials.js:23,64`; `views/summary.js:71,76`. `drawSidebar` (`app.js:36`) has the same gap, but there it only costs the highlight.
   - Who: anyone on a slow machine, or during a long check, who clicks faster than the server answers.
   - How I know: reproduced (`test_probe_slow_trial_overwrites_newer_view`). The probe delayed `/api/trials/NCT03412565` by 1.5 s with Playwright routing, a stand-in for a slow server, then clicked Quiet. The result was hash `#/watchlists/2/needs-review` with the h1 showing the daratumumab trial's title. The other three renders are inferred from the same pattern.

3. **When a check's state cannot be read, the error box is empty.** | sweep
   - What happens: if `GET /api/watchlists/<id>/check` fails when a watchlist opens, the status area shows an empty red box with no words.
   - Where: `webapp/static/app.js:183`. Here `el("div", { class: "error" }, err.message)` passes a third argument, but `app.js`'s own `el` (`app.js:20`) takes only `(tag, attrs)`, so the message is dropped. The views' `el` helpers take children. The shell's does not.
   - How I know: reproduced (`test_probe_check_mount_error_is_worded`, with a 500 from Playwright routing and declared with `walk.expect`). The `.error` text was `''`.

4. **One failed poll during a running check leaves Check for updates refused until the analyst leaves the page.** | sweep
   - What happens: if one progress poll fails while a check runs (a 500, or a dropped connection), polling stops. The button stays `aria-disabled="true"` with "A check is already running." beside it, and the status area is blank. This combines with finding 3. The check itself finishes on the server, but nothing on the page says so.
   - Where: `webapp/static/views/check.js:142-157`. `poll()` has no catch. When it is reached from `show()` (`check.js:135`), the rejection goes to `app.js:183`, which never calls `setBusy(false)`. When it is reached from `begin()`, the catch at `check.js:178` does clear busy.
   - How I know: reproduced (`test_probe_poll_error_leaves_button_usable`). The probe left during a check, came back, and made the second GET fail. After 8 s the result was `aria-disabled` `true` and status `''`.

5. **The sidebar loses its "you are here" mark after Rename, New watchlist and other in-place changes.** | sweep
   - What happens: the `reviewchange` listener redraws the sidebar with `drawSidebar(null)`, so the current watchlist loses its highlight and `aria-current="page"`. Rename (from the header menu or first use), + New watchlist, Remove from this list and its Undo all fire it, as do the views that dispatch `reviewchange`. On the watchlist page the analyst is left with no visible marker of which list is open, and a screen reader loses the current-page state.
   - Where: `webapp/static/app.js:81`.
   - How I know: reproduced for Rename (`test_probe_sidebar_active_after_rename`) and New watchlist (`test_probe_sidebar_active_after_new_watchlist`). Both gave `aria-current=page` count 0. Other dispatchers are inferred.

6. **The trial address does not carry the watchlist the analyst came from, so reload, a new tab or a shared link loses "Back to" and Next trial.** | design
   - What happens: the origin (list, tab, scroll) lives only in a module variable and in the queue entry's history state (`app.js:67-79`). After a reload of `#/trials/NCT…`, or when the link is opened in a new tab, the page falls back to the trial's first watchlist (`trial.js:16`). "Back to" then names the wrong list, and Next trial walks the wrong queue. Story 6 says reload keeps "the same watchlist, tab or trial", and story 36 says Back returns "to the list … I came from". The implementation decision says links "can be opened in a new tab". This is design-class because the trial address shape is now cited by every view that links to a trial (queue, All trials, Summary, Next trial, Find's results), and adding the list to it later touches all of them.
   - Where: `webapp/static/app.js:67-79`, `views/trial.js:16-21,180-186`.
   - How I know: reproduced (`test_probe_back_to_after_reload`). NCT00000003 is held by both lists. Opened from Quiet's All trials, it read "‹ Back to Quiet". After a reload it read "‹ Back to Non-small cell lung cancer: …".

7. **Escape (or Cancel) after Create watchlist has been pressed still creates the watchlist.** | nit
   - What happens: the analyst presses Create watchlist, then Escape before the reply arrives. The dialog closes as a cancel (`onCancel` runs), the POST completes, and `onCreated` runs as well. The new watchlist appears in the sidebar, and a Find picker switches to it. Story 97 says "close on Escape without changes".
   - Where: `webapp/static/views/new_watchlist.js:26-37`. The `close` handler fires `onCancel` while the request is in flight, and nothing stops `onCreated` afterwards. The same shape exists in `watchlist_menu.js:27-41` (rename) and `:68-78` (delete): Escape during the POST closes the dialog, and the change still lands, silently in rename's case because `close()` is a no-op on a closed dialog and `onRenamed` still runs.
   - How I know: reproduced for New watchlist (`test_probe_escape_during_create`, with the POST delayed 1.5 s): sidebar names `[…, 'Quiet', 'Cancelled one']`. Rename and delete are inferred.
   - Simplest fix: block Escape (the `cancel` event) while the request is pending.

8. **The tab strips and the trial menu use ARIA roles whose keyboard model they do not provide, and the menu hides its membership list from screen readers.** | sweep (inferred; no screen reader run)
   - What happens: `tabs.js` and the trial page give links `role="tab"` inside `role="tablist"`, with no arrow-key movement, no roving `tabindex` and no `aria-controls`. A screen reader announces tabs and tells the user to use arrow keys, which do nothing. The trial page's `role="menu"` (`trial.js:28,59-62`) holds the "In watchlists" names as `<p role="presentation">`. Content in a menu that is not a menuitem is commonly not announced, so story 50's "which watchlists hold the trial" may be invisible to a screen-reader user. Neither menu supports arrow keys. Story 100 asks for "real controls". Plain links in a `nav`, and a disclosure (`aria-expanded` region) in place of `role="menu"`, would match how they behave.
   - Where: `webapp/static/views/tabs.js:6,15`; `views/trial.js:28,37-40,59-62`; `views/watchlist_menu.js:85,88`.
   - How I know: read. Not checked with VoiceOver.

9. **An empty This week offers "Show the whole month", which can be narrower than the week.** | nit (inferred)
   - What happens: a week that starts in the previous month (Mon 27 Oct to Sun 2 Nov, viewed on 1 Nov) is not inside This month (1 to 30 Nov). The offer of "a wider range" (story 90, row 10/F) then shows a period that drops five of the week's days.
   - Where: `webapp/static/views/summary.js:169`.

10. **The Summary walk's first assertion compares a value with itself, and its fixture leans on the wall clock.** | nit
    - What happens: `(trials, changes) == (2, changes)` (`walks/test_summary_walk.py:69`) is half always-true. It reads as checking the field-change count but checks only `trials == 2` (evidence.md, "no value compared with itself"). The seed places changes at "now" and "now minus 30 minutes" in the server's zone, while the test computes `today` in the test process's zone. In the first 30 minutes of a Monday or of the 1st of a month (New York time), one seeded change falls into the previous period. I did not work out whether `changes >= 3` would then fail.
    - Where: `walks/test_summary_walk.py:30-38,63-69`.
    - How I know: read.

11. **Judgement on logged gaps that touch this area.** | nit
    - "Failed to fetch" with the server stopped (Further Notes; exploration): agreed as follow-up. The same follow-up should cover `api.js:9`. Any non-JSON reply, such as a proxy page or a truncated body, throws `SyntaxError: Unexpected token …` from `response.json()`, and that text is shown verbatim as the message. Findings 3 and 4 make the stopped-server case worse than logged: the check status can go blank and stay refused.
    - Header "Last checked <now>" after a check where every trial failed (exploration defect 4): ticket 16 fixed the queue card ("Nothing to review yet … could not be checked"). The header still moves (`check.js:38`), but the spec defines a watchlist's last checked as "the time its most recent check for updates finished", so the header is per spec. The decision holds.
    - Tabs lacking counts (observation 23:42): holds. `tabs.js` now carries counts for every tab but Summary.
    - The flaky simulated-label walk (observation 20:31): holds. `test_trial_page_walk.py:221` now waits for the fifth change card before counting.
    - Design 11's second panel (observation 00:27): still absent from `app.js:91-118`. Logged as a decision, and nothing in the branch changes the reason.

## Not read

- `views/find.js`, `add_by_id.js`, `registry_trial.js`, `saved_search.js`, `new_matches.js` (other areas). `saved_search.js`'s `manageDialog` and `banner` were read only at their call sites.
- The server and domain modules, except `webapp/times.py`, `display.status_label` and the all-trials and needs-review handlers' field names.
- `style.css` beyond a grep for focus, sticky, state and overflow rules. I did not compare any screen with the design PNGs. Header stacking with a long name (observation 01:22) was not re-checked.
- The full walk suite and the unit suite were not run. Only my probes ran.
- WebKit, Safari, screen readers, real hardware, and the live registry.
- `focus.js` was read and reasoned about, not mutated. I did not try to make it steal focus.
