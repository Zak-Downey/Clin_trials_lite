# Spec: Fix what the whole-branch review of PR #1 found blocking

Status: needs-triage

Root feature: html-front-end (`.scratch/html-front-end/spec.md`). This spec fixes the blocking findings of the whole-branch review of pull request #1 at tip `e77cb9c`. The full ranked list, with every finding's class and reason, is `ranked.md` in this folder; the reviewers' own files are under `findings/`. Each finding below is restated so this spec stands alone, and each says where its fix goes: where the defect was made, not where it shows.

The root spec's stories, Implementation Decisions and Design coverage still hold. Story numbers below are the root spec's. Hand-over stays the root spec's ticket 17, which runs after this spec's tickets (`gate.py handover html-front-end pr-1-review`).

## Problem Statement

The branch passes its suites (454 unit, 278 walks), yet the review found seventeen defects that a user would meet, that write wrong data, or that sit inside a check that does not check what its box claims. Several are one class seen again after ticket 16 fixed it in one place only: a finished check rebuilding a tab (exploration defect E-004, fixed for All trials alone), and a late answer drawing over a page already left (E-003, fixed for Find trials alone).

## Findings

### F1. The walk runner's "alone" re-run runs the whole walk suite

`walks/run_walks.py` always passes `"walks"` as a positional argument to pytest (`pytest()`, line 32), and the re-run of a failed walk calls `pytest([nodeid], alone)` (line 61). The "alone" run therefore collects the whole folder plus the node id, runs it serially, and returns the whole suite's exit code. A walk that flakes under load is reported "red alone" (a defect) whenever any other walk fails in that serial run, and every failed walk costs a full serial run, so two failures push the `walks` check past its 900 s timeout. The ready gate reads the defect/flake verdict from the `## Result` section this produces (`evidence.md`, The runner contract), so the user's defect list at hand-over can be wrong. Seen: the retained re-run of the simulated-label walk ends `2 failed, 113 passed`. `walks/test_run_walks.py` says at its top "Lacks: the re-run itself".

Fix where it was made: `walks/run_walks.py`, the argument list `pytest()` builds; the re-run passes only the node id. Source: `findings/walks-and-retirement.md` B1.

### F2. The Summary's "Latest:" line can name an older check's fields

`briefing.summarise` sorts a trial's moves high-signal fields first, across all checks (`briefing.py:202`). `webapp/api_summary.py` `_latest` then takes `moves[0]["detected"]` as the newest check. A trial whose newest check (5 Nov) moved only the brief title and whose older check (3 Nov) moved the completion date reads "Latest: completion date updated." That is the line the analyst briefs from (story 87, design 10/4). The existing test `test_api_summary.py:112` means to pin this rule but its fixture moves no high-signal field, so it cannot fail.

Fix where it was made: `webapp/api_summary.py` `_latest`, taking the newest stamp as the maximum `detected` over the trial's moves; a fixture with a high-signal field in the older check. Source: `findings/server-and-domain.md` 1.

### F3. A finished check rebuilds the tab and drops what the analyst set on it

When a check finishes, `check.js` calls `ctx.refresh` (`webapp/static/app.js:177-181`), which calls the tab's `render` again from scratch.

- **Summary.** The `draw` closure captured `hashQuery` when the route was drawn (`app.js:163`); `summary.js` `remember` (line 78) moves the period with `history.replaceState`, which fires no `hashchange`. So after a check the Summary redraws as This week while the address still says `?period=month`, and Custom dates being typed are lost. Reproduced: "1–30 Nov 2026 · 2 trials · 6 field changes" became "2–8 Nov 2026 · 2 trials · 9 field changes" with `#/watchlists/1/summary?period=month`.
- **New matches.** `new_matches.js:15-20` keeps `selected`, `showing` and `pending` as locals of `render`. After a check the ticks are cleared, the action bar goes, a pending "Yes, dismiss N" is gone and View dismissed falls back to new matches. A check is exactly when new matches arrive.

Story 8 ("never switch tabs by itself when a check … changes the counts, so that what I'm reading doesn't move"), design 2/F, story 78. Ticket 16 fixed the same class for All trials by keeping its state per watchlist.

Fix where it was made: the refresh path in `app.js` reads the period from the current address, not the captured value; Summary's period and custom dates and New matches' selection, sub-view and pending confirmation are kept per watchlist at module level, as `all_trials.js` now does. Sources: `findings/client-shell-and-watchlists.md` 1; `findings/seams.md` 1.

### F4. A slow answer for a page already left draws over the page the analyst moved to

`route()` passes no `alive()` to `renderTrial`, `renderQueue`, `renderAll` or `renderSummary`; each calls `root.replaceChildren` after its `await`. The `generation` check in `route()` guards only the error path (`app.js:188`). Reproduced with the trial's answer delayed 1.5 s and Quiet clicked meanwhile: the address read `#/watchlists/2/needs-review` and the page showed the trial. Ticket 16 fixed this for Find trials and Registry details only (they take `alive`). `drawSidebar` (`app.js:36`) has the same gap.

Fix where it was made: `app.js` `route()` hands each render the `alive` it already gives Find trials, and `views/trial.js`, `needs_review.js`, `all_trials.js` and `summary.js` return before drawing when it is false. Source: `findings/client-shell-and-watchlists.md` 2.

### F5. The sidebar loses its "you are here" mark after Rename, New watchlist and other in-place changes

The `reviewchange` listener redraws the sidebar with `drawSidebar(null)` (`app.js:81`), so the open watchlist loses its highlight and `aria-current="page"`. Rename, + New watchlist, Remove from this list and its Undo all fire it. Reproduced for Rename and New watchlist: `aria-current=page` count 0.

Fix where it was made: `app.js:81`, redrawing with the watchlist the current address names. Source: `findings/client-shell-and-watchlists.md` 5.

### F6. When a check's state cannot be read, the status is blank and Check for updates stays refused

- `app.js:183` builds the error with `el("div", { class: "error" }, err.message)`, but `app.js`'s own `el` (line 20) takes only `(tag, attrs)`, so the message is dropped: an empty red box. Reproduced with a 500 on `GET /api/watchlists/<id>/check`.
- `check.js` `poll()` (142-157) has no catch. Reached from `show()` (line 135) its rejection goes to `app.js:183`, which never calls `setBusy(false)`. One failed poll during a running check leaves the button `aria-disabled="true"` with "A check is already running." beside it and a blank status, until the analyst leaves the page. Reproduced: after 8 s, `aria-disabled` true and status `''`.

The root spec: every failure is stated, and nothing that failed is presented as current.

Fix where it was made: `check.js` `poll()` catches, states the failure in the status area and clears busy; `app.js:183` puts the message in the box. Sources: `findings/client-shell-and-watchlists.md` 3 and 4.

### F7. Adding trials from New matches leaves the header at "0 trials monitored · Check for new matches"

The header's `current` is captured by `check.js` `mount` (line 30) and renewed only when a check finishes (151, 168). `new_matches.js` refreshes its own tab strip and the sidebar, not the header. On a watchlist with a saved search and no trials (stories 24, 82), adding a match leaves "0 trials monitored", and the button still says "Check for new matches" though pressing it now checks the new trial. Reproduced.

Fix where it was made: `check.js` re-reads the overview and redraws the header on the `reviewchange` event the sidebar already listens to. Source: `findings/seams.md` 2.

### F8. Trial details always offer the first watchlist as the destination, not the one the analyst came from

On `#/registry/<id>` the "Add to" picker is preset to the first watchlist not holding the trial (`registry_trial.js:21-22`), ignoring the Find trials destination and the watchlist whose New matches tab opened the page. Searching from "Elsewhere", the bar reads "Add to: Elsewhere"; View details then Add to watchlist adds to "Myeloma". From New matches the wrong list gets the trial while the offer stays in the list it came from, and "‹ Back to results" goes to Find trials, not New matches (line 17). Design 11/2 ("Find trials and Add by NCT ID carry the originating watchlist"), stories 65, 70, 78. Reproduced at both viewports.

Fix where it was made: `find.js` exports its current destination; `registry_trial.js` presets the picker to the originating watchlist (Find's destination, or the New matches watchlist that linked it) and its Back link returns where the analyst came from. Source: `findings/discovery-and-export.md` S1.

### F9. Add by NCT ID: a failed add after a good lookup clears the ID and reads as a success

If the registry fails when Add to watchlist is pressed after a good lookup, `add_by_id.js:43-50` runs `found = null; draw();` for both outcomes: the ID field is emptied and the failure sentence appears in the green success banner (`class="banner"`, `role="status"`) with an "Open My watchlist" link. Story 71 keeps and focuses the input on every failure. `registry_trial.js:36-38` has the same shape, showing a failed add beside "Open the trial" for a trial that is not monitored. Reproduced for Add by NCT ID.

Fix where it was made: the add handlers in `add_by_id.js` and `registry_trial.js` branch on the outcome; a failure is an error beside the control, with the input kept and focused. Source: `findings/discovery-and-export.md` S3.

### F10. A saved search with two lead sponsor types loses all but the first when edited

The domain, the API and the address carry `sponsor_types` as a list; the form's Lead sponsor type is a single `<select>` that shows `q.sponsor_type[0]` (`find.js:86`) and reads back one value (`find.js:120`). Manage saved search → Edit search → Search trials narrows "Industry or NIH" to "Industry", and Replace saved search would store the narrower query. The retired Streamlit page offered a multiselect, and existing databases are upgraded in place, so old saved searches arrive in this shape. Stories 54, 76. Reproduced: `'Industry or NIH' -> 'Industry'`.

Fix where it was made: the Lead sponsor type control in `find.js` holds several values (a group of checkboxes, as Trial status is). Source: `findings/seams.md` 3.

### F11. A refused search is shown as a registry failure with a Retry that cannot succeed, and the server chooses the refusal's kind by its wording

- An inverted start-date window gets 400 `bad_dates` ("… Swap the two dates."). `find.js:296-302` never reads `err.kind`, so the message appears in the registry-error box with Retry (story 61's treatment), not beside the dates (story 57, design 7/1); Retry re-sends the same refusal. Reproduced.
- `api_search.py:30` and `api_saved_search.py:57` map a `MonitorError` to `nothing_asked` when `"at least one" in str(err)`, else `bad_dates`; `monitor._refuse_unanswerable` raises both with the default kind. Rewording the message would send every empty-form refusal to the dates. The root spec asks for error kinds the API maps to messages, not message text.

Fix where it was made: `monitor._refuse_unanswerable` raises each refusal with its own kind and the two handlers pass the kind through; `find.js` shows `bad_dates` and `nothing_asked` beside their fields with the form open and no Retry, keeping Retry for `registry_error`. Sources: `findings/seams.md` 4; `findings/server-and-domain.md` 4.

### F12. A trial added while its watchlist is being deleted lands in the deleted watchlist

`api_membership.add_trials` reads the target, releases the lock to fetch (line 51), retakes it and writes the membership (59) without checking that the watchlist still exists. Foreign keys are off, so the insert succeeds: an orphan `list_members` row that `list_trials(conn, None)` counts as monitored while `lists_holding` says no list holds it. The reply is 200 "added" to a list that no longer exists. Reproduced at the API with the stand-in `slow`.

Fix where it was made: `add_trials`, re-reading the watchlist after the lock is retaken and answering 404 `watchlist_not_found`. Sources: `findings/discovery-and-export.md` S2; `findings/server-and-domain.md` 8.

### F13. A check still checks a trial removed, or a watchlist deleted, while it runs

`api_checks._start` fixes the run's steps from `list_trials` when the run begins; `_work` releases the lock on every fetch. A trial removed mid-run that no other list holds is still fetched, marked checked and given new changes, though the root spec says it "is skipped by every check". Deleting the watchlist mid-run checks every trial it held. Inferred from the code.

Fix where it was made: `api_checks._work`, re-reading membership under the lock before each step (`storage.is_member`) and ending the run if the watchlist is gone. The same function's `finally` should also set `run.running = False` in an inner `finally`, so a failing `finish_run` cannot leave the watchlist refusing checks until restart (`findings/server-and-domain.md` 9, a nit carried here because its fix is in this function). Source: `findings/server-and-domain.md` 7.

### F14. The exported CSV has no byte-order mark, so Excel garbles every non-ASCII character

`briefing.as_csv` writes UTF-8 with no BOM; `summary.js` `download()` wraps it as `text/csv;charset=utf-8`. Excel opens a BOM-less CSV in the system code page, so the em dash written for every empty value shows as `â€”`, and accents and symbols in titles and sponsors (é, ®, ±) are mangled: the columns story 89 calls exact evidence. The acceptance walk decodes the file as UTF-8 and cannot see this. Inferred from known Excel behaviour; no Excel here.

Fix where it was made: `briefing.as_csv` starts its output with U+FEFF; the CSV tests read with `utf-8-sig`. Source: `findings/discovery-and-export.md` S4.

### F15. The Summary walk's first assertion compares a value with itself, and its data leans on the clock

`walks/test_summary_walk.py:69` asserts `(trials, changes) == (2, changes)`, which reduces to `trials == 2`: the field-change count it reads as checking is never checked (`evidence.md`, No always-true check). The seed places changes at now and 30 minutes ago (lines 30-38) while the test computes `today` in its own process, so in the first half hour of a Monday or of the 1st (server zone) a seeded change falls into the previous period. Sources: `findings/client-shell-and-watchlists.md` 10; `findings/walks-and-retirement.md` N3.

Fix where it was made: `walks/test_summary_walk.py`, asserting the expected count, and seeding at a fixed time inside the period (or a clock the server and the test share).

### F16. "No horizontal scroll at any step" is measured only at screenshots and at the end

`Guards.measure()` runs only from `Walk.shot()` (`walks/conftest.py:61`) and from `problems()` at the end (line 98). The acceptance journey takes nine shots, and never measures the states between them: the New watchlist dialog, Add by NCT ID and its found card, the Watch this search dialog and its saved state, the running-check panel, the Dismiss confirmation, View dismissed, the copy notice. Ticket 15 box 18 claims every step. Exploration then found pages widened in exactly such states (E-002). Source: `findings/walks-and-retirement.md` S1.

Fix where it was made: the acceptance walk's `Keys.focus` (`walks/test_acceptance_walk.py`) measures on every keyboard move.

### F17. "Every control reached in the journey" checks only the controls the walk aimed at

`Keys.focus` (`walks/test_acceptance_walk.py:87-98`) presses Tab until the target has focus and notes only the target. The stops passed on the way are never checked for being a real control with a name and a ring. The second walk's `crawl` covers five views and the results page, not the dialogs, New matches and its bar, Add by NCT ID, View dismissed or the check panel. Ticket 15 box 19 claims every control reached. Source: `findings/walks-and-retirement.md` S2.

Fix where it was made: `Keys.focus` notes every stop it passes.

## Tickets

`issues/01` to `issues/12`. 01 is the foundation: every later walk verdict in this spec rests on it. 02 to 06 change what a user sees and are `Kind: design`, each with its Open list item. 07 and 08 are server only. 09 and 10 are walk fixes; 10 is this spec's acceptance walk. 11 is the exploration round, 12 the sweep.

## Further Notes

- Every non-blocking finding, with why it has its class, is in `ranked.md`. The sweep findings are ticket 12. The design findings are the Open list below. The nits are dropped there with a reason.
- A ticket here whose diff touches `webapp/static/**` must be `Kind: design` (`gate.py ticket` refuses it otherwise). The exploration ticket is not, so a defect it finds that needs a page change is written up as a new `Kind: design` ticket with its own Open list item (`gate.py open pr-1-review "...ticket NN..."`), not fixed inside ticket 11.

## Open list

Say which recommendations you reject; silence accepts them all. Items 1 to 5 are the design marks of tickets 02 to 06 (fixes that change what a user sees).

1. **ticket 02 (design mark): a finished check keeps the tab as the analyst left it.** Choice: keep Summary's period and custom dates and New matches' ticks, sub-view and pending confirmation per watchlist, as All trials now keeps its filter (F3), or leave refresh rebuilding the tab. Doing it costs a module-level map in two views and a change to app.js's refresh. Leaving it breaks story 8 on the two tabs where a check matters most. Recommended: do

2. **ticket 03 (design mark): a late answer never draws over the page the analyst moved to, and the sidebar keeps its mark.** Choice: pass `alive()` to the trial, queue, All trials and Summary renders and redraw the sidebar with the current watchlist (F4, F5), or leave them. Doing it changes four render signatures and one listener. Leaving it lets the page and the address disagree on a slow answer, and drops `aria-current` on every rename. Recommended: do

3. **ticket 04 (design mark): Check for updates states a failed read and keeps its header current.** Choice: catch a failed poll, put the message in the error box, and re-read the header on `reviewchange` (F6, F7), or leave them. Doing it adds a catch and a listener in `check.js`. Leaving it shows an empty red box, a button refused until the page is left, and "0 trials monitored" after adding from New matches. Recommended: do

4. **ticket 05 (design mark): adding from trial details or by NCT ID goes where the analyst came from, and a failed add is not a success.** Choice: preset trial details to Find's destination or the New matches watchlist, and show a failed add as an error with the ID kept (F8, F9), or leave the first-watchlist preset and the shared banner. Doing it exports Find's destination and splits two handlers. Leaving it adds trials to the wrong watchlist. Recommended: do

5. **ticket 06 (design mark): Find trials keeps every sponsor type on edit and shows a refused search by its kind.** Choice: make Lead sponsor type a group of checkboxes like Trial status, or keep the select and show the extra values with a refusal to drop them; and show `bad_dates` and `nothing_asked` beside their fields without Retry (F10, F11). Checkboxes cost a taller More filters; the select keeps the form short but needs its own warning. Leaving it narrows saved searches silently. Recommended: do, with checkboxes

6. **CSV cells beginning `=`, `+`, `-`, `@`, a tab or a carriage return** (discovery-and-export D1, server-and-domain 6, root Further Notes summary 6). Choice: prefix `'` to such cells in the CSV and say so in the README, or write them as they are. Prefixing costs the literal exactness of those cells in the file (the page and the copied text stay exact). Leaving them lets Excel read a registry title as a formula and show values like `-80 °C storage` as `#NAME?`, so the file is not exact either way. Recommended: do (ticket 08 carries it as its last box; rejecting this item removes that box)

7. **The saved-search cap: 100 per run of the search's first results, or 100 new matches per run** (server-and-domain 2). Today a run looks only at the first 100 results, so once those are added or dismissed, later runs offer nothing and say "Nothing new matched" while unseen matches exist. Reading further costs more registry pages per run and a cap on pages; keeping it costs the untrue sentence, which could at least name the cap instead. Recommended: defer (follow-up spec; decide the reading there and fix the sentence with it)

8. **Story 103: the simulator runnable from the command line** (server-and-domain 3). No ticket built it; `simulate.py` has no entry point and the README does not mention it. A small CLI costs a ticket; moving the story to Further Notes costs nothing now but leaves the simulator usable only from Python. Recommended: defer (move story 103 to the follow-up spec)

9. **The trial address does not carry the watchlist the analyst came from** (client-shell 6). After a reload, a new tab or a shared link, "Back to" names the trial's first watchlist and Next trial walks its queue. Adding the list to the address touches every view that links to a trial; leaving it keeps reload true only for trials in one list. Recommended: defer (follow-up spec; the address shape is one decision for all links)

10. **Tab strips and the trial menu use ARIA roles whose keyboard model they lack** (client-shell 8; not checked with a screen reader). Choice: give them arrow keys and a roving tabindex, or drop `role=tab` and `role=menu` for plain links in a `nav` and a disclosure, which is how they behave. The first costs a keyboard model in three views; the second changes what the walks query by role. Leaving it tells a screen-reader user to press arrow keys that do nothing, and may hide the "In watchlists" names. Recommended: defer (follow-up spec, judged with VoiceOver at hand-over)

11. **The app starts on a new port each run, so remembered tabs and kept links last one run** (seams 5). A fixed default port keeps them across restarts and costs a clash when the port is taken (`instance.claim` already redirects a second start); the free port costs the tab memory at every restart. Recommended: defer (follow-up spec; until then the README can say links last one run)

12. **A trial removed from a watchlist drops out of that period's summary and CSV, even for changes detected before** (discovery-and-export D2). Judging membership at detection time keeps the briefing independent of later housekeeping and costs a query over monitoring events; judging it as now matches what the watchlist holds. No story asks for either. Recommended: leave

13. **A live fidelity check for search** (walks-and-retirement D1). `walks/fidelity_check.py` checks the single-study lookup only; one filtered live search would show the filter expression is accepted, the answer has the shape the stand-in invents, and the page token is opaque. It costs a by-hand live call outside the gate; without it nothing shows a filtered search works against the real registry. Recommended: defer (follow-up spec, beside the stand-in row ticket 12 corrects)

14. **Walk guards cannot declare an expected network failure** (walks-and-retirement D2). Without it the logged "Failed to fetch" follow-up cannot get a green walk. Adding it costs a change to the helper every walk rests on. Recommended: defer (follow-up spec, beside the "Failed to fetch" item)

15. **Shared helpers** (standards: the `el` DOM helper copied into 13 view files, with `app.js`'s variant taking no children, which caused F6's empty box; the watchlist-404 guard written five times; the lock release written three times; `monitor`'s private functions called from the API). Extracting them costs a change across most views and handlers that no defect asks for; leaving them keeps shotgun edits. R-003 needs the lock helper if adopted. Recommended: defer (follow-up spec; ticket 07 does not refactor them)

## Proposed rules

Each is a row of the rule queue (`docs/agents/local/rules.md`) and of Recurring findings in `docs/agents/local/ledger.md`. Adopting one is yours; silence leaves it proposed, and `gate.py handover` lists it.

- **R-001** (forbid, for `docs/agents/local/factory.json`): every async view render takes `alive`. Pattern `^export async function render\w*\((?!.*\balive\b)`, paths `webapp/static/views/*.js`. Today it would flag `trial.js`, `needs_review.js`, `all_trials.js`, `summary.js` and `new_matches.js`. Escapes E-003, E-015.
- **R-002** (line for `CODING_STANDARDS.md`): state the analyst sets on a tab (selection, filter, sort, period, typed dates, pending confirmation, sub-view) lives in a per-watchlist module map, never in render's locals or a captured query; refresh redraws from it. Escapes E-004, E-014.
- **R-003** (forbid, after a `ctx.unlocked()` helper exists): pattern `\.lock\.release\(\)`, paths `webapp/api_*.py`; and a `CODING_STANDARDS.md` line: a write after a registry call made outside the lock re-reads the rows it writes to. Escapes E-023, E-024.
- **R-004** (line for `CODING_STANDARDS.md`): a view's catch states the failure in an error element, never in `.banner`, and branches on `err.kind` where the server gives one. Escapes E-008, E-017, E-020, E-022.
- **R-005** (forbid): no value compared with itself. Pattern `\(\s*\w+\s*,\s*(\w+)\s*\)\s*==\s*\([^()]*,\s*\1\s*\)`, paths `walks/**/*.py`, `tests/**/*.py`. Escape E-026.
- **R-006** (line for `CODING_STANDARDS.md`, or for `docs/agents/walkthrough.md`): a box that says every, any or each is checked at each instance, not at a sample, and a check's `Lacks:` line names any instance it skips. Escapes E-012, E-027, E-028.
