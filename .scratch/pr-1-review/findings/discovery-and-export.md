# Branch review: discovery and export (PR #1, feature html-front-end)

Read: the area of the whole branch. Diff `git diff 9229115..feature/html-front-end -- webapp/` for `webapp/static/views/{find,registry_trial,add_by_id,saved_search,new_matches,summary}.js` and `webapp/{api_search,api_membership,api_saved_search,api_new_matches,api_summary}.py`, plus the domain code they call (`monitor.py` search, lookup, add and found functions; `briefing.py` summary, text and CSV; `ctgov.find_page`; `storage` found rows and memberships). Spec stories 52-90 and the Implementation Decisions; design pages 06 and 09.

Before this review I read the exploration reports for find trials, saved search and new matches, and summary and export (`.scratch/html-front-end/explore/*.md`), the logged observations, and the spec's Further Notes. I do not repeat what they list unless I am classing it or the branch has changed since. No per-ticket reviews exist for this area (`reviews/` holds only 01 and 02).

Reproductions are scripts outside the repo, in `/tmp/pr1rev/`, run with `.venv/bin/python -m pytest -p walks.conftest <file> -q -s --rootdir=<repo>` against the walk helper and stand-in registry. Their output is in `/tmp/pr1rev/run1.txt`, `run2.txt` and `run3.txt`. Screenshots are under `.scratch/html-front-end/walks/` (git-ignored).

Counts: blocking 0 · sweep 4 · design 2 · nit 4

---

## Sweep

### S1. Trial details always offer the first watchlist as the destination, not the one the analyst came from (stories 65, 70; design 11/2, 6/4)

- **What happens.** On the details page of a trial that is not monitored (`#/registry/<id>`), the "Add to" picker is preset to the first watchlist that does not hold the trial. It ignores the Find trials destination and the watchlist whose New matches tab opened the page. An analyst who searches from watchlist "Elsewhere", sees "Add to: Elsewhere" in the action bar, opens View details and presses Add to watchlist adds the trial to "Myeloma". The banner names the list, but nothing before the press does unless they read the picker.
- **New matches path.** From a New matches card ("title links to details", story 78) the same preset applies. A trial added from there to the wrong list stays on offer in the watchlist it came from, because `adopt_many` only clears the offer on the target list. On the same page, "‹ Back to results" goes to `lastFind` (Find trials), not back to New matches.
- **Who.** Every analyst who adds from a details page while holding more than one watchlist.
- **Where.** `webapp/static/views/registry_trial.js:21-22` (`first = watchlists.find(w => !trial.watchlists.some(...)) || watchlists[0]`), `:17` (Back link). `find.js` keeps `destination` but exports only `lastFind` and `chooseDestination`.
- **How I know.** Reproduced: `/tmp/pr1rev/test_discovery_repro.py::test_details_destination_from_find`, at both viewports. Seeded "Myeloma" (holds NCT10000002) and "Elsewhere"; opened `#/find/<Elsewhere>`; searched "many"; ticked a result (bar: "Elsewhere"); opened View details. The picker read "Myeloma" (`run1.txt`: `BAR Elsewhere DETAILS Myeloma`). The New matches path and its Back link are read from the code, not driven.
- **Why the walks miss it.** `test_find_select_walk.py` has the same two lists but never adds from the details page with a non-first destination.

### S2. A trial added while its watchlist is being deleted lands in the deleted watchlist, and the page reports "1 added"

- **What happens.** `add_trials` reads the target watchlist, then releases the lock to fetch from the registry, then reacquires it and writes the membership without checking that the watchlist still exists. SQLite foreign keys are not switched on (no `PRAGMA foreign_keys` in `storage.py`), so the insert succeeds. The result is a `list_members` row pointing at a watchlist that no longer exists. The answer is 200 `{"added": [...], "list": {"name": "Doomed"}}`, and the page shows "1 added" with an "Open Doomed" link that leads nowhere. The ghost row also makes `storage.list_trials(conn, None)` ("only what some list holds") count the trial as monitored, while `lists_holding` (which joins `lists`) says no list holds it.
- **Who.** An analyst with two windows open, or one who deletes a watchlist from its ⋯ menu while a long bulk add from Find trials is still fetching. Adding 30 or more selected trials holds the window open for many seconds.
- **Where.** `webapp/api_membership.py:37-62` (the target is read at :37, `_fetch_outside_lock` at :51, `adopt_many` at :59 with no re-check). `monitor.add` (`monitor.py:129-162`) calls `storage.add_member` without checking the list.
- **How I know.** Reproduced at the API level, `/tmp/pr1rev/test_ghost_repro.py`: stand-in `slow` (2 s); POST add to "Doomed" in one thread; POST delete after 0.5 s. Result (`run3.txt`): `DELETE 200 ADD 200 {'added': ['NCT00000003'], ... 'list': {'id': 2, 'name': 'Doomed'}}`, `lists` holds only id 1, `list_members` holds `(2, 'NCT00000003')`.
- **Fix.** Re-check the watchlist after the lock is retaken, answering 404 `watchlist_not_found`. Switching foreign keys on is the wider fix but touches every table. This is the only discovery handler that writes after releasing the lock.

### S3. Add by NCT ID: a failed add after a good lookup clears the typed ID and reads like a success (story 71)

- **What happens.** If the registry fails when Add to watchlist is pressed (the lookup succeeded, but `add` fetches again), the panel is redrawn. The NCT ID field is emptied. The failure ("ClinicalTrials.gov returned an error for NCT00000002 (500).") appears in the green success banner (`class="banner"`, `role="status"`) with an "Open My watchlist" link, as if something had been added. Story 71 asks for the input to be kept and focused on every failure; this is the one failure path where it is not.
- **Where.** `webapp/static/views/add_by_id.js:43-50` (`found = null; draw();` runs for both outcomes). The same pattern is in `registry_trial.js:36-38`, where a failed add shows its detail beside "Open the trial", a link to a trial that is not monitored (read, not driven).
- **How I know.** Reproduced, `/tmp/pr1rev/test_addbyid_repro.py`: look up NCT00000002, switch on stand-in `fail` for that ID, press Add. Result (`run2.txt`): `BANNER 'ClinicalTrials.gov returned an error for NCT00000002 (500).\nOpen My watchlist' CLASS banner INPUT ''`, at both viewports.
- **Not in the exploration list.** The exploration report lists "Registry failure while adding from New matches" as not checked. This is the Add by NCT ID path, also not driven there.

### S4. The exported CSV has no byte-order mark, so Excel shows mangled characters (story 89, design 10/3 "exact values")

- **What happens.** `as_csv` writes UTF-8, and `download()` wraps it in a `text/csv;charset=utf-8` Blob without a BOM. Excel on Windows and macOS opens a CSV without a BOM in the system code page. Every non-ASCII character is then garbled, including the em dash the export writes for every empty value (`display.EMPTY = "—"`, which shows as `â€”`), and accented or symbol characters in registry titles and sponsor names (é, ö, ®, ±, which are common in trial titles). The analyst's briefing spreadsheet then shows wrong values in exactly the columns the story calls "exact evidence".
- **Where.** `briefing.py:as_csv` (about lines 311-340) and `webapp/static/views/summary.js:17-24`.
- **How I know.** Read: no `﻿` anywhere in `briefing.py` or `webapp/`. Excel's handling of a CSV without a BOM is known behaviour, not reproduced here (no Excel on this machine). The acceptance walk reads the file back with Python's `utf-8` decoder, so it cannot see this.
- **Fix.** Prefix `﻿` (Python's `utf-8-sig`). The CSV test reads it with `csv.DictReader`, which needs `utf-8-sig` to strip it from the first header.

## Design

### D1. CSV cells that begin with `=`, `+`, `-` or `@` (exploration summary 6, logged observation 2026-11-09T02:40:46): **design**, with a recommendation to escape

- **Judgement.** Not blocking. The text is registry text that has passed ClinicalTrials.gov's QA review. The tool is local. A formula payload such as `HYPERLINK` needs a click, and DDE-style payloads trigger Excel's own warnings. It is also not merely a security matter. The argument for leaving cells as they are ("exact values", Further Notes) does not hold: Excel already does not show such a cell exactly. A value like `-80 °C storage` or `+/- 2 weeks` opens as a formula error (`#NAME?`), so the analyst never sees the exact value either way.
- **Where it applies.** The Title, Previous value, New value and Watchlist columns. `display.collapse` drops a lone `-` bullet, but not a `-` attached to a word.
- **Recommendation for the user's decision.** Prefix `'` to any cell starting with one of `= + - @`, a tab or a carriage return, and state it in the README. The page and the copied text keep the exact value.
- **Where.** `briefing.py:as_csv`.

### D2. A trial removed from the watchlist drops out of that period's summary and export, even for changes detected before the removal

- **What happens.** `briefing.summarise` keeps only changes of trials the watchlist holds now (`storage.list_trials(conn, list_id)`). A completion-date change detected on Monday disappears from the weekly briefing if the trial is removed on Wednesday. Story 86 keeps reviewed changes "so that reporting is independent of my reading". The same reasoning suggests reporting should not depend on later housekeeping either, but no story says so.
- **Where.** `briefing.py:summarise` (the `watched` set).
- **How I know.** Read, not driven. It needs a decision rather than a fix: the trial's membership could be judged at detection time (monitoring events record when monitoring stopped) or as now.

## Nit

### N1. The copied summary marks simulated changes "🧪 SYNTHETIC"; the page and the CSV say "Simulated" (story 103: "labelled simulated wherever they appear")

`briefing.as_text` uses `display.SYNTHETIC` (`'🧪 SYNTHETIC'`, confirmed by running it). `briefing.SYNTHETIC` was changed to `"Simulated"` for the CSV, and `summary.js:45` draws "Simulated". `tests/test_briefing.py:372` pins the old word into the text. Where: `briefing.py` `as_text`, the `mark =` line.

### N2. Different headings for the same trial across discovery

New matches cards and Find results use `_identity()["title"]`, which is the official title, or else the brief title (`api_new_matches.py:23`, `api_search.py:42`). The details page they open, the trial page and the summary use the acronym, else the brief title (Implementation Decisions: "The trial heading is the registry acronym, else its brief title"). A card titled with a 30-word official title opens a page headed with a short title, so the analyst checks the NCT ID to be sure it is the same trial. Design 06 and 09 show short headings. Read, not driven: the stand-in has one title.

### N3. Dismissing parses every offered record once per selected ID, under the server's one lock

`api_new_matches.dismiss` calls `storage.list_found` (which `json.loads` every full offered record) inside the per-ID loop (`api_new_matches.py:68-72`). With the 100-offer cap and 20 selected, that is 2,000 parses of full study records; live records average about 50 KB (measured: 5.0 MB for 100 multiple-myeloma studies). Every other request waits on the lock meanwhile. Inferred, not timed. One query per ID, or one `list_found` before the loop, removes it.

### N4. The Find action bar drops the reason a trial could not be added

The bar says "1 could not be added (NCT…)" and leaves out `failed[].detail`, which holds "was not found" or "could not reach ClinicalTrials.gov" (`find.js:249-251`; the same in `new_matches.js:125-127`). The analyst cannot tell whether pressing Add again will help. Related and also inferred: a bulk add fetches each selected trial one after another with no pause (`api_membership.py:_fetch_outside_lock`), unlike a check (`monitor.PAUSE`). A 50-to-100-trial add may meet the registry's rate limit, and that limit is then exactly the reason the bar does not show.

---

## Checked and not a finding

- **Live search shape.** `ctgov.find_page` reads `totalCount` and slices `pageSize = page × 10` from one request. Fetched live with `query.cond=multiple myeloma`: page 1 has 10 studies, the page-10 request (pageSize 100) has 100 studies with `totalCount` 4059, 5.0 MB in 1.1 s. The shape `find_page` reads matches. This is not a fidelity check of `filter.advanced` (phase, sponsor type, status, dates), which the stand-in ignores and nothing compares. That gap is already the stand-in row's own note.
- **Origin and Host guard.** A foreign-origin JSON POST is refused (non-simple content type, and the Origin check); a foreign `Host` is refused. Search and registry details are GET-only and store nothing.
- **Saved search round trip.** The page shape is converted to the domain shape and back (`_for_page` / `_read_query`), with types validated. A replace returns the previous query.
- **Undo token for dismissal.** It names only that action's IDs. A trial added since is not re-offered (`restore_found` needs `dismissed = 1`).

## Classing of logged items in my area

- **CSV formula cells:** D1 above (design, recommend escaping).
- **Dismiss of a match another window already added says "0 trials dismissed":** the logged follow-up stands. Nit; I agree with not fixing it here.
- **Empty orange strip in the Watch dialog:** nit; the logged follow-up stands.
- **Bad custom dates in the summary address replace the whole tab; two period buttons pressed at once; clipboard-refused advice:** logged follow-ups, nits. The clipboard one could become sweep if Safari refuses the clipboard by default (hand-over will show).

## Not read

- `webapp/static/views/{trial,check,watchlist_menu,dialog,tabs,all_trials,needs_review}.js`, `api_checks.py`, `api_trials.py`, `api_watchlists.py` beyond the helpers my area calls, `focus.js`, `style.css`.
- Design pages other than 06 and 09 (07, 08, 10, 11 not opened as images; judged from the spec's coverage table).
- The walk files for my area (`test_find_*`, `test_add_by_id_walk.py`, `test_saved_search_walk.py`, `test_new_matches_walk.py`, `test_summary_walk.py`) beyond their headers, and the red runs under `.scratch/html-front-end/red/`. I did not run the unit or walk suites; I ran only my four reproduction walks.
- `monitor.find_new` under the check thread (who holds the lock across `_matches`) belongs to the checks area.
- Safari and real Excel: the BOM finding (S4) and D1's Excel behaviour are inferred from known behaviour, not observed.
