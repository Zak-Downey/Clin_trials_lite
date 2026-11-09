# Ledger: what escaped, what each gate found, what it cost

The workflow's own measurements for this repo. Without them, nobody can say which gate earns its cost or which rule can be cut. Agents add rows as `evidence.md` and their role files say; the user reads this at a retro.

## Escapes

A defect found after its ticket merged. One row each, added by whoever fixes it, on the day.

| ID | Date | Feature | Defect | Found by | Should have been found by | Change made |
|---|---|---|---|---|---|---|
| E-001 | 2026-11-09 | html-front-end | Keyboard focus dropped to the page after a redraw in Find trials, Summary, New matches, Remove from this list, trial tabs, Check for updates (ticket 15 fixed Mark reviewed only); explore findings: watchlists-and-review 2, trial-page 3 and 4, find-trials 2, saved-search 1, summary 1, dialogs 2 and 4 | exploration | walk | ticket 16: webapp/static/focus.js restores focus after any redraw; Check button uses aria-disabled |
| E-002 | 2026-11-09 | html-front-end | A long unbroken word (watchlist name, query, condition, trial list name) widened the page or clipped a dialog title; explore: watchlists-and-review 1, find-trials 3, saved-search 4, dialogs 3, trial-page 5 | exploration | walk | ticket 16: overflow-wrap anywhere on the view, sidebar and dialogs (style.css) |
| E-003 | 2026-11-09 | html-front-end | A slow registry answer drew over a page or search the analyst had already left; explore: find-trials 1 | exploration | walk | ticket 16: render checks alive() after each await (find.js, registry_trial.js, app.js) |
| E-004 | 2026-11-09 | html-front-end | A filter and sort typed on All trials were cleared when a running check finished; explore: watchlists-and-review 3 | exploration | walk | ticket 16: all_trials.js keeps them per watchlist |
| E-005 | 2026-11-09 | html-front-end | After a check where every trial failed the empty queue read All caught up; explore: watchlists-and-review 4 | exploration | unit | ticket 16: needs_review.js says Nothing to review yet when a trial's latest check failed |
| E-006 | 2026-11-09 | html-front-end | An empty watchlist had no menu, so it could not be renamed or deleted; explore: dialogs 1 | exploration | walk | ticket 16: first-use screen carries a Rename and Delete menu |
| E-007 | 2026-11-09 | html-front-end | Full recheck started while a check ran closed its dialog and said nothing; explore: dialogs 5 | exploration | walk | ticket 16: check.js says why it did not start |
| E-008 | 2026-11-09 | html-front-end | Undo and Restore on New matches had no error handling: a refused undo left the button disabled with a page error; explore: saved-search 2 | exploration | walk | ticket 16: new_matches.js catches and says so |
| E-009 | 2026-11-09 | html-front-end | Escape did not close a ⋯ menu from its button and Tab left it open; explore: trial-page 1 and 2 | exploration | walk | ticket 16: views/menu_keys.js for both menus |
| E-010 | 2026-11-09 | html-front-end | Copy summary redrew the tab, closing opened trials and wiping typed custom dates; explore: summary-and-export 2 and 3 | exploration | walk | ticket 16: summary.js updates only the notice |
| E-011 | 2026-11-09 | html-front-end | A trial held by many watchlists made the review bar and the actions menu taller than the screen; explore: trial-page 5 | exploration | walk | ticket 16: also-list scrolls in a small box, menu has a max height (style.css, trial.js) |
| E-012 | 2026-11-09 | html-front-end | The walk runner's alone re-run of a failed walk runs the whole walk suite, so the defect/flake verdict the ready gate reads is wrong and two failures pass the walks timeout (walks/run_walks.py); pr-1-review findings: walks-and-retirement B1 | branch-review | foundation-review |  |
| E-013 | 2026-11-09 | html-front-end | The Summary's Latest line can name an older check's fields: _latest takes moves[0] after a high-signal-first sort (webapp/api_summary.py); its test's fixture had no high-signal field; findings: server-and-domain 1 | branch-review | unit |  |
| E-014 | 2026-11-09 | html-front-end | A finished check rebuilds the tab: Summary jumps to This week while the address says month, custom dates lost; New matches drops ticks, pending dismiss and View dismissed (app.js refresh, summary.js, new_matches.js); findings: client-shell 1, seams 1 | branch-review | walk |  |
| E-015 | 2026-11-09 | html-front-end | A slow answer for a trial, queue, All trials or Summary already left draws over the page the analyst moved to; ticket 16 fixed this for Find trials only (app.js route passes no alive); findings: client-shell 2 | branch-review | exploration |  |
| E-016 | 2026-11-09 | html-front-end | The sidebar loses aria-current and its highlight after Rename, New watchlist, Remove and Undo (app.js reviewchange redraws with null); findings: client-shell 5 | branch-review | walk |  |
| E-017 | 2026-11-09 | html-front-end | A failed read of a check's state shows an empty error box (app.js el takes no children) and one failed poll leaves Check for updates refused with a blank status (check.js poll has no catch); findings: client-shell 3 and 4 | branch-review | walk |  |
| E-018 | 2026-11-09 | html-front-end | Adding from New matches leaves the header at 0 trials monitored and Check for new matches (check.js captures the overview at mount); findings: seams 2 | branch-review | walk |  |
| E-019 | 2026-11-09 | html-front-end | Trial details preset Add to the first watchlist, not the one the analyst came from, so a trial is added to the wrong list; Back from a New matches card goes to Find trials (registry_trial.js); findings: discovery-and-export S1 | branch-review | walk |  |
| E-020 | 2026-11-09 | html-front-end | Add by NCT ID: a failed add after a good lookup clears the ID and shows the failure in the success banner with an Open link (add_by_id.js; same shape in registry_trial.js); findings: discovery-and-export S3 | branch-review | walk |  |
| E-021 | 2026-11-09 | html-front-end | A saved search with two lead sponsor types is narrowed to the first on Edit search, and Replace saved search would store it (find.js single select); findings: seams 3 | branch-review | walk |  |
| E-022 | 2026-11-09 | html-front-end | An inverted start-date window is shown as a registry failure with a Retry that cannot succeed (find.js ignores err.kind), and the server picks nothing_asked or bad_dates by matching message text (api_search, api_saved_search, monitor._refuse_unanswerable); findings: seams 4, server-and-domain 4 | branch-review | walk |  |
| E-023 | 2026-11-09 | html-front-end | A trial added while its watchlist is deleted gets an orphan list_members row and a 200 added reply (api_membership.add_trials writes after the unlocked fetch without re-reading the list); findings: discovery-and-export S2, server-and-domain 8 | branch-review | unit |  |
| E-024 | 2026-11-09 | html-front-end | A check still fetches, marks checked and records changes for a trial removed (or a watchlist deleted) while it runs (api_checks._work uses the steps fixed at start); findings: server-and-domain 7 | branch-review | unit |  |
| E-025 | 2026-11-09 | html-front-end | The exported CSV has no byte-order mark, so Excel shows the em dash for every empty value and accented title characters garbled (briefing.as_csv); findings: discovery-and-export S4 | branch-review | none |  |
| E-026 | 2026-11-09 | html-front-end | The Summary walk asserts (trials, changes) == (2, changes), a value compared with itself, and its seed leans on the wall clock at week and month boundaries (walks/test_summary_walk.py); findings: client-shell 10, walks-and-retirement N3 | branch-review | none |  |
| E-027 | 2026-11-09 | html-front-end | The acceptance walk measures horizontal scroll only at its nine screenshots and the end, though its box claims every step (Guards.measure via Walk.shot); findings: walks-and-retirement S1 | branch-review | none |  |
| E-028 | 2026-11-09 | html-front-end | The acceptance walk checks only the controls it aimed at, not the Tab stops it passed, though its box claims every control reached (Keys.focus); findings: walks-and-retirement S2 | branch-review | none |  |
| E-029 | 2026-11-09 | pr-1-review | A check that finishes after the analyst left New matches redraws New matches and resets where Find trials' View details came from (app.js refresh draws after await drawSidebar with no alive(); new_matches.js render calls setOrigin); todo walk: test_walk_a_check_finishing_after_leaving_new_matches_does_not_change_where_find_trials_details_came_from; explore: watchlists-and-review 1; UNRESOLVED | exploration | walk | ticket 13 (not yet built) |
| E-030 | 2026-11-09 | pr-1-review | Two quick review changes whose sidebar answers arrive out of order leave the sidebar badges stale (app.js reviewchange drawSidebar has no ordering guard; same in check.js onChange); todo walk: test_walk_a_late_older_sidebar_answer_does_not_overwrite_the_newer_badges; explore: watchlists-and-review 4; UNRESOLVED | exploration | walk | ticket 13 (not yet built) |
| E-031 | 2026-11-09 | pr-1-review | Check for updates gives up keyboard focus: Enter moves focus to Add trials because focus.js counts an aria-disabled button as unusable; todo walk: test_walk_check_for_updates_keeps_keyboard_focus_while_it_runs_and_after; explore: watchlists-and-review 2; UNRESOLVED | exploration | walk | ticket 14 (not yet built) |
| E-032 | 2026-11-09 | pr-1-review | View dismissed and Back to new matches leave focus on the Summary tab; todo walk: test_walk_view_dismissed_and_back_to_new_matches_do_not_leave_focus_on_a_tab; explore: watchlists-and-review 3; UNRESOLVED | exploration | walk | ticket 14 (not yet built) |
| E-033 | 2026-11-09 | pr-1-review | A double click on Mark reviewed sends two requests and leaves an Undo that fails with a script error (trial.js mark handler has no in-flight guard); todo walk: test_walk_undo_after_a_double_click_on_mark_reviewed_still_undoes_the_review; explore: watchlists-and-review 5; fixed | exploration | walk | ticket 15 |
| E-034 | 2026-11-09 | pr-1-review | A wholly failed add from the Find results bar reads as an outcome (0 added, an Open link to a list that gained nothing, no reason); F9 fixed Add by NCT ID and trial details only; todo walk: test_explore_a_wholly_failed_add_in_the_bar_is_an_error_with_a_reason_and_no_open_link; explore: find-and-add 1; UNRESOLVED | exploration | walk | ticket 16 (not yet built) |
| E-035 | 2026-11-09 | pr-1-review | In Add by NCT ID the failure sentence of a failed add stays beside the field after the ID is edited; todo walk: test_explore_the_add_error_is_cleared_when_the_id_is_edited; explore: find-and-add 4; UNRESOLVED | exploration | walk | ticket 16 (not yet built) |
| E-036 | 2026-11-09 | pr-1-review | A page number outside 1 to 10 in the Find address is read as registry_error: a Retry that cannot succeed and an empty form (bad_page kind left on the old path by F11); todo walk: test_explore_page_11_is_a_refusal_with_no_retry_and_keeps_the_query_in_the_form; explore: find-and-add 2; UNRESOLVED | exploration | walk | ticket 17 (not yet built) |
| E-037 | 2026-11-09 | pr-1-review | A page past the last of a search (page=2 of 3 matches) draws 11-10 of 3 matches, Page 2 of 1 and no results; todo walk: test_explore_page_two_of_a_one_page_search_does_not_draw_an_empty_list; explore: find-and-add 3; UNRESOLVED | exploration | walk | ticket 17 (not yet built) |

### escapes.jsonl

Each Escapes row has a line in `docs/agents/local/escapes.jsonl`, written by `gate.py ledger add`, which prints the row to paste here with its `E-NNN` id as the first cell. `gate.py ledger check` joins the two and refuses a row without a line.

## Builds

One row per build, written by `gate.py close`.

| Feature | Dates | Tickets | Per-ticket review: blocking / notes / mutants survived | Exploration: defects | Whole-branch review: blocking / sweep / design / nit | Found by the user | Subagents by role and model | Merger subagents | Guard refusals |
|---|---|---|---|---|---|---|---|---|---|

## Recurring findings

A class of review finding seen more than once. The review merger adds rows and proposes a rule; adopting it is the user's.

| Class | Seen in | Rule proposed | Adopted |
|---|---|---|---|
| A late answer draws over a view the analyst already left (an async view render with no `alive` guard) | E-003 (exploration, Find trials), E-015 (pr-1 review: trial, queue, All trials, Summary) | R-001: forbid `^export async function render\w*\((?!.*\balive\b)` in `webapp/static/views/*.js` | |
| A finished check rebuilds a tab and drops what the analyst set on it (tab state kept in render's locals or a captured query) | E-004 (exploration, All trials), E-014 (pr-1 review: Summary, New matches) | R-002: CODING_STANDARDS line, state the analyst sets on a tab lives in a per-watchlist module map and refresh redraws from it | |
| A write after the lock is released for a registry call does not re-read what it writes to | E-023, E-024 (pr-1 review, twice) | R-003: one `ctx.unlocked()` helper and forbid `\.lock\.release\(\)` in `webapp/api_*.py`; CODING_STANDARDS line, re-read the target before writing | |
| A failure path draws nothing, draws as a success, or ignores the error's kind | E-008 (exploration), E-017, E-020, E-022 (pr-1 review) | R-004: CODING_STANDARDS line, a view's catch states the failure in an error element, never in `.banner`, and branches on `err.kind` | |
| A check does not check what its box claims (a value compared with itself; "every" or "any" sampled) | E-012, E-026, E-027, E-028 (pr-1 review) | R-005: forbid a tuple compared with itself in `walks/` and `tests/`; R-006: CODING_STANDARDS line, a box that says every or any is checked at each instance | |
