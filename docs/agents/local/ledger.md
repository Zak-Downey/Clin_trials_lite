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
