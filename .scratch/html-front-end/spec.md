# Spec: Replace the Streamlit front end with an HTML page

Status: needs-triage
Brief: .scratch/html-front-end/brief.md

## Problem Statement

The Trial Change Monitor works, but its Streamlit front end gets in the analyst's way. Screenshots of every current screen (8 November 2026) showed the same problems again and again:

- The columns that matter, What changed, Registry updated and Detected, sit off-screen to the right of a canvas table, with nothing saying they are there.
- Selecting a trial opens its profile far below the table. Marking it reviewed then closes it, jumps the page and confirms nothing.
- The saved search is buried in a folded "Manage lists" panel. Its new matches appear only after a check, in a table that looks like the watchlist's own.
- On the Search page the destination watchlist has to be picked twice, below a tall grid with truncated titles and no select-all.
- The change summary is a monospace code block that runs off the right edge.
- On a narrow window, everything that matters scrolls sideways.

Streamlit can't fix most of this: its layout, tables and rerun model are the cause. The app also carries a WebAssembly runtime and a GitHub Pages pipeline, which the analyst no longer needs now that running locally is fine.

## Solution

A plain HTML page, designed in `design.pdf` (this folder, 14 pages), served by a small Python server on the analyst's own machine and opened in their browser. The monitoring logic that already works (checking, change detection, saved searches, the change summary) stays and is extended where the design asks. Streamlit, the WebAssembly runtime and the GitHub Pages pipeline are deleted (ADR 0003).

The analyst lands on a watchlist's **Needs review** queue and sees what changed before opening anything. They open a trial to compare previous and new values side by side, then mark it reviewed without losing their place, with Undo available. All trials, New matches and Summary are tabs of the same watchlist. Find trials gets the screen to itself: a short form, then paged results with real checkboxes and one action bar naming the destination. Administration moves into small dialogs. Every failure (a trial that could not be checked, a saved search that failed, a registry that is unreachable) is stated, and nothing that failed is presented as current.

The words used on screen are the ones in `CONTEXT.md`.

## User Stories

### Finding your way

1. As an analyst, I want to start the app with one command and have it open in my browser, so that I don't have to remember a URL or a port.
2. As an analyst, I want two top-level destinations, Watchlists and Find trials, always visible, so that I never hunt through a menu.
3. As an analyst, I want a sidebar listing my watchlists with each one's trial count and the number of trials needing review, so that I can see where the work is without opening each one.
4. As an analyst, I want long watchlist names to wrap in the sidebar rather than truncate, so that I can tell similar names apart.
5. As an analyst, I want a "+ New watchlist" action in the sidebar, so that creating a watchlist is one obvious step.
6. As an analyst, I want the browser's Back and Forward buttons, and a reload, to keep me on the same watchlist, tab or trial, so that the page behaves like a website.
7. As an analyst, I want a watchlist to open on its Needs review tab, but to stay on any tab I chose explicitly when I come back to it, so that my choice is respected.
8. As an analyst, I want the app never to switch tabs by itself when a check or a review changes the counts, so that what I'm reading doesn't move.

### Needs review

9. As an analyst, I want the Needs review tab to list only the trials with unreviewed changes, newest detection first, so that I work through what is new.
10. As an analyst, I want each queue entry to show the trial's heading, NCT ID, phase, sponsor and registry status, the names of the fields that changed, when the change was detected, and a count of its changes, so that I can triage without opening it.
11. As an analyst, I want the queue's heading to state both units, "2 trials need review" and "6 unreviewed field changes", so that I'm never unsure what a number counts.
12. As an analyst, I want the trial heading and a "Review changes" button to open the same page, so that there is one way in.
13. As an analyst, I want trials with simulated changes labelled "Simulated changes", so that I never brief anyone on a fabricated change.
14. As an analyst, I want an empty queue to say "All caught up", with the last check time and a "View all trials" button, so that an empty queue isn't mistaken for missing data.

### Watchlist header and checking

15. As an analyst, I want the watchlist header to show its name, how many trials it monitors and when it was last checked, so that I know how current it is.
16. As an analyst, I want a "Check for updates" button, and no hint of scheduled or live monitoring, so that I know checking happens only when I ask.
17. As an analyst, I want an "Add trials" button in the header that opens Find trials with this watchlist as the destination, so that adding starts from where I am.
18. As an analyst, I want a check to show its progress ("4 of 6 trials checked · Searching for new matches next") while I keep reading the watchlist or a trial, so that checking doesn't block me.
19. As an analyst, I want a second Check for updates refused while one is running, so that I can't start duplicate checks.
20. As an analyst, I want a completed check to say "Check complete · No new changes detected", with the number checked, the time, and how many trials still need review from earlier checks, so that "no changes" and "nothing to review" stay distinct.
21. As an analyst, I want a check that found no changes to leave earlier unreviewed changes in the queue, so that checking never counts as reviewing.
22. As an analyst, I want a check where some trials failed to say "Check incomplete", say how many failed, keep each failed trial's previous data and last successful check time, and offer "Retry failed" and "Show details", so that a partial failure never looks like an all-clear.
23. As an analyst, I want a saved-search failure reported separately from trial-check results, so that I know whether discovery or monitoring failed.
24. As an analyst, I want a check to run the saved search even when the watchlist has no trials yet, so that a new watchlist can be filled from its saved search.

### All trials

25. As an analyst, I want an All trials tab listing every trial in the watchlist, with title, phase, sponsor, registry status, review state and last successful check, so that I can scan the whole inventory.
26. As an analyst, I want the review state shown as "N changes", "Reviewed" or "No changes", separate from the registry status, so that I never confuse the trial's status with my reading of it.
27. As an analyst, I want a trial whose last check failed to show a labelled warning beside its last successful check time, so that I know its data may be stale.
28. As an analyst, I want to filter the table by title, NCT ID or sponsor, and have it clear that this filter only searches this watchlist, so that I find a known trial quickly.
29. As an analyst, I want to sort All trials by title, latest change or trial status, so that I can scan the inventory in the order I need.
30. As an analyst, I want trial titles to be real links and long titles to wrap, with headers that stay visible, so that nothing is truncated or hidden sideways.

### Trial page: changes

31. As an analyst, I want a trial page with Changes, Trial details and History tabs, opening on Changes when I come from the queue, so that the change is the first thing I read.
32. As an analyst, I want each unreviewed change shown as the field name with labelled Previously and Now values, stacked when the values are long, so that I compare them directly.
33. As an analyst, I want each change to show both its registry-updated date and its detected time, so that I know when the sponsor edited it and when I noticed.
34. As an analyst, I want changes grouped by the check that found them, keeping intermediate transitions, so that a field that moved twice shows both moves.
35. As an analyst, I want a link to the trial's ClinicalTrials.gov page, so that I can check the source.
36. As an analyst, I want a "Back to <watchlist>" link that returns me to the list and position I came from, so that I don't lose my place.
37. As an analyst, I want an action bar that stays visible without covering content, saying "Review covers all N changes shown above", so that I know exactly what reviewing will do.
38. As an analyst, I want the action bar to say before I act that reviewing also clears these changes in every other watchlist holding the trial, naming them, so that the scope is never a surprise.
39. As an analyst, I want "Mark reviewed" to mark exactly the changes shown, so that a change found by a check that finished while I was reading stays unreviewed.
40. As an analyst, I want to stay on the trial after reviewing, with a confirmation ("3 changes marked reviewed. This trial stays open.") and the page not jumping, so that I keep my place.
41. As an analyst, I want an Undo on that confirmation that restores exactly those changes to unreviewed, until I leave the trial or act again, so that a slip costs nothing.
42. As an analyst, I want a "Next trial" button that opens the next trial in Needs review without marking anything reviewed, so that I can move through the queue deliberately.

### Trial page: details and history

43. As an analyst, I want the trial heading to use the registry acronym if there is one, else its brief title, with the full official title and every identifier under Identity, so that the heading is readable and nothing is silently cut.
44. As an analyst, I want an "At a glance" panel with registry status, phase, lead sponsor, enrolment, the ClinicalTrials.gov link and when monitoring began, so that the key facts stay in view.
45. As an analyst, I want the details as five sections (Identity & study design, Conditions & eligibility, Interventions & arms, Endpoints, Dates & results), the long ones expandable on demand, so that the dossier reads as a document rather than uneven cards.
46. As an analyst, I want a missing registry value shown as "Not reported", never guessed, so that I can trust what I read.
47. As an analyst, I want fields with unreviewed changes never hidden inside a collapsed section, so that the details never conceal what is new.
48. As an analyst, I want a History tab with one newest-first timeline of change detections, reviews (with time and count) and the start of monitoring, so that the trial's whole record is in one place.
49. As an analyst, I want to expand any check in the history to see every previous-to-new transition, even after review, so that reviewing never erases evidence.
50. As an analyst, I want the trial page's menu to show which watchlists hold the trial and offer "Remove from this list", so that membership is managed where I'm looking.
51. As an analyst, I want removing a trial from a watchlist to offer Undo, and to keep the trial's history even when no other watchlist holds it, so that a slip loses nothing.

### Find trials: searching

52. As an analyst, I want the search form open the first time, with Condition, Intervention, Sponsor and Phase visible, and the rule "Start with at least one of these four fields" stated above them, so that I don't learn the rule by failing.
53. As an analyst, I want Phase as a set of labelled toggle buttons, several selectable, shown as selected by more than colour, with a clear-all action, so that picking phases is quick and accessible.
54. As an analyst, I want More filters (lead sponsor type, trial status, study started from and to) folded until I open them, showing my selections in full when open, so that the first search stays simple.
55. As an analyst, I want the help that matters ("Sponsor type uses the lead sponsor, not collaborators"; "Date filters exclude trials without a reported start date") written under the fields, not hidden in hover tooltips, so that I see it.
56. As an analyst, I want Enter to submit the search, so that the keyboard is enough.
57. As an analyst, I want a submitted search with none of the four fields to show the error beside that group and keep every value I typed, so that I fix it in place.
58. As an analyst, I want the form to collapse after results arrive into a plain-language summary ("Multiple myeloma · Janssen · Phase 3" and its filters) with "Edit search", so that the results get the screen.
59. As an analyst, I want "N matches" with the registry's true total, results paged ten at a time, and "Showing the first 100 of 5,214. Narrow your search to see the rest" when the cap applies, so that I know what I'm not seeing.
60. As an analyst, I want zero matches to keep my query and offer "Edit search" and "Clear optional filters", so that I recover in one step.
61. As an analyst, I want a registry error to keep the form and offer Retry, not an empty results area, so that a network blip costs nothing.

### Find trials: selecting and adding

62. As an analyst, I want each result as a row with a real checkbox and a title link that opens its details, long titles wrapping, so that selecting and opening stay separate.
63. As an analyst, I want "Select 10 on this page" and selections that persist across pages and while I look at a trial's details, with the total stated, so that I can gather trials from several pages.
64. As an analyst, I want an action bar, shown once something is selected, stating "N trials selected", with Clear, an "Add to" watchlist picker and "Add N trials", so that the count and destination are always in reach.
65. As an analyst, I want the destination preset to the watchlist I came from, so that I rarely pick it at all.
66. As an analyst, I want a "New watchlist" option inside every destination picker that creates the watchlist and returns me to my task with it selected, so that I never abandon a task to create a destination.
67. As an analyst, I want adding to confirm exactly what happened ("2 added; 1 already in this list"), link to the watchlist, and clear the completed selection, so that the loop is closed.
68. As an analyst, I want a trial added for the first time to take its baseline without reporting any changes, so that I don't expect history from before I started.

### Find trials: add by NCT ID

69. As an analyst, I want an "Add by NCT ID" tab where I type an ID, press "Look up trial", and see its ID, title, sponsor and status before an "Add to watchlist" button, so that I never add a trial I haven't seen.
70. As an analyst, I want the destination watchlist named on that tab, preset from where I came, so that I know where it goes.
71. As an analyst, I want distinct, in-place messages for an invalid ID ("NCT followed by 8 digits"), an ID not found, a trial already in this watchlist and the registry being unavailable, with my input kept and focused, so that I know what to fix.

### Saved search and new matches

72. As an analyst, I want "Watch this search" on the results to open a dialog saving the submitted query to a chosen watchlist, with or without any results selected, and without adding any results, so that saving a search means one thing.
73. As an analyst, I want that dialog, when the watchlist already has a saved search, to show the current query and label its button "Replace saved search", with Cancel changing nothing, so that I replace it knowingly.
74. As an analyst, I want a confirmation ("Search saved. <watchlist> will check for new matches when you run Check for updates.") with an "Open watchlist" link, so that I know it worked.
75. As an analyst, I want a "Saved search is on" banner on a watchlist that has one, with a Manage link, saying it runs when I check for updates and that new matches need my approval, so that discovery is visible but secondary.
76. As an analyst, I want Manage saved search to show the query, with "Edit search" (which opens Find trials pre-filled and replaces the query only when I save it) and "Turn off" (which keeps the watchlist's trials), so that I control discovery.
77. As an analyst, I want New matches as their own tab with a count, never pushing the review queue down, so that discovery never competes with review.
78. As an analyst, I want new matches listed with checkboxes, title links to details, and an action bar with "Add N to watchlist" and "Dismiss N", so that I decide on several at once.
79. As an analyst, I want trials added from new matches to take their baseline and the confirmation to say "N added" with a link to All trials, so that I see the result.
80. As an analyst, I want the dismiss action to state before I commit that "These trials will not be suggested again for this list", and to offer Undo afterwards, so that dismissing is deliberate and reversible.
81. As an analyst, I want "View dismissed" to list a watchlist's dismissed matches, each with Restore, so that a dismissal is never permanent.
82. As an analyst, I want a watchlist with a saved search and no trials to offer "Check for new matches", so that it has a useful next step.

### Change summary and export

83. As an analyst, I want a Summary tab with This week (Monday to Sunday), This month and Custom dates, filtering by detection time, so that I can brief on any period.
84. As an analyst, I want Custom dates to open labelled From and To fields with Apply and Cancel, the old summary staying until both dates are valid, so that a half-picked range never blanks the page.
85. As an analyst, I want the summary headed with the period, the number of trials and field changes, how many await review and how many are reviewed, and the time zone dates use, so that the numbers are unambiguous.
86. As an analyst, I want reviewed changes kept in the summary, so that reporting is independent of my reading.
87. As an analyst, I want the summary grouped by trial and then by check, each trial showing its change count, how many checks found changes and a latest-change line, expandable to every field transition, with simulated changes labelled, so that repeated changes aren't flattened.
88. As an analyst, I want "Copy summary" to copy plain text with each trial's ClinicalTrials.gov link, so that I can paste it into a briefing.
89. As an analyst, I want "Export CSV" to download a file with one row per field change: watchlist, NCT ID, title, field, previous value, new value, registry-updated date, detected date and time, review status and simulated flag, so that the file carries the exact evidence.
90. As an analyst, I want an empty period to say "No changes detected in this period", keep the controls, disable export with an explanation and offer a wider range, so that an empty result is clear.

### First use and administration

91. As a new analyst, I want an empty watchlist to show only "Monitor your first trial", explaining that adding a trial saves a starting point and future checks show what changed, with "Find trials" and "Add by NCT ID" buttons that carry this watchlist as the destination, so that I have one clear next step.
92. As a new analyst, I want no empty summary, activity feed or check controls before my first trial, so that the page teaches only what I need.
93. As an analyst, I want a ⋯ menu on the watchlist with Rename watchlist, Manage saved search, Full recheck and Delete watchlist, each opening its own dialog, so that administration stays out of the daily path.
94. As an analyst, I want watchlist names checked for being empty or duplicate inline, in both New watchlist and Rename, so that I fix the name in place.
95. As an analyst, I want Full recheck explained as a one-off that ignores the registry's update date, with its own completion message, so that I use it only when I mean to.
96. As an analyst, I want Delete watchlist to name the watchlist, say that it removes the watchlist, its saved search and its memberships, that trials in other watchlists are unchanged, and that history is kept while trials no longer in any watchlist stop being checked, so that I know exactly what I'm deleting.
97. As an analyst, I want every dialog to trap focus, close on Escape without changes, and return focus to what opened it, so that the keyboard works throughout.
98. As an analyst, I want to add a trial back after it left every watchlist and have its history resume, so that the next check tells me what moved while it was unwatched.

### Reach and trust

99. As an analyst, I want every screen usable at any window width down to 390 px with no horizontal scrolling of titles, changes or summaries, so that a narrow window still works.
100. As an analyst, I want every action reachable by keyboard, with visible focus, text labels and no meaning carried by colour alone, so that the app is accessible.
101. As an analyst, I want the app reachable only from my own machine, so that my watchlists are never exposed on a network.
102. As an analyst, I want the README to say how to start the app, where the database file lives and how to back it up, so that I can trust it with my work.
103. As a developer, I want the simulator runnable from the command line against a trial, its changes labelled simulated wherever they appear, so that I can demonstrate alerting without a real change.

## Implementation Decisions

### Shape

- **A local web app.** A small Python HTTP server, using the standard library only (no web framework, no new runtime dependency), binds to `localhost` on a free or configured port. It serves one static HTML page with plain CSS and JavaScript (no build step, no framework, no CDN at runtime), and a JSON API. One launch command starts the server and opens the browser. The database location stays as it is today: `MONITOR_DB` if set, else `monitor.db` in the folder the app is started from (git-ignored). The README names it and says to copy that file to back it up.
- **Routing in the page** uses the URL (hash or path), so Back, Forward and reload restore the watchlist, tab, trial and search state, and links can be opened in a new tab.
- **The server is a thin layer over the existing domain modules** (`monitor`, `storage`, `briefing`, `display`, `medical_affairs`, `diff`, `ctgov`). The API composes their functions and holds no business rules of its own; the rules the design adds go into the domain modules. A check runs on a background thread in the server process; the page polls its progress. One check at a time per watchlist is enforced by the server, and all database writes go through one connection guarded by a lock.
- **Retired in this spec:** the Streamlit entry point and its view modules, the stlite page, the site build script, the in-browser transport, the Pages publish workflow, Streamlit in the requirements, and the tests that exist only for those. ADR 0003 records the switch and supersedes ADR 0002.

### Domain changes (from the gap map against the design)

- **Changes carry their IDs to callers.** The functions that list a trial's changes and history return each change's ID, its check (the shared detection timestamp of one check of one trial is the check's identity), previous and new values, registry-updated date, detected time, review state and simulated flag.
- **Review by change ID.** Reviewing takes the list of change IDs shown and marks exactly those; changes not in the list are untouched. It returns what it marked. Review applies to the trial everywhere, as today.
- **Review events persist.** Each review records its time and the change IDs it marked, so History can show "Reviewed · Marked 3 changes from the 16:45 check as reviewed". Undo takes a review event and returns exactly its changes to unreviewed, recording the undo.
- **Check failures persist per trial.** A failed check records its time and error kind against the trial without moving its last successful check. A later success clears the failure flag. A watchlist's "last checked" is the time its most recent check for updates finished.
- **Retry failed** re-checks only the trials whose most recent check failed in the watchlist's last check run.
- **Retention.** Removing a trial from its last watchlist, or deleting that watchlist, no longer deletes the trial, its snapshots or its changes; the trial becomes unmonitored and is skipped by every check. Adding it back to any watchlist makes it monitored again without a new baseline; the next check compares against its last snapshot. Undo of a removal restores the membership.
- **Restore a dismissed match**, and list a watchlist's dismissed matches.
- **Look up a trial without adding it**: returns its NCT ID, heading, official title, sponsor and status.
- **Distinct error kinds** for invalid format, not found, already in this watchlist and registry unavailable, as error types or codes the API maps to messages, not message text.
- **Search returns a page and a total.** A search takes a page number, returns up to 10 rows for that page, the registry's total count for the same query (all axes, not only condition and term), and whether the 100-result cap applies. Bulk add returns added, already present and failed, by NCT ID.
- **New matches are capped at 100 per saved-search run**, and the result says when the cap applied.
- **The trial heading** is the registry acronym, else its brief title; the official title is always available.
- **The change summary** groups by trial and then by check, includes every transition and reviewed changes, and is bounded by detection time in the machine's local time zone. Its plain text includes trial links. Its CSV gains review status and the full detected date and time.
- **Trial details** regroup the eight existing information groups into the design's five sections plus the At a glance facts. The regrouping is a display mapping; the monitored fields don't change.
- **The registry's base URL is configurable**, so the walks can point the app at the stand-in registry. Nothing else in the app knows about the stand-in.
- **Dropped from the domain surface:** the cross-watchlist "Everything monitored" summary, and the activity feed as a screen.

### API (the contract the page uses)

The resources, in outline. Every response is JSON, every error carries a stable `kind` and a human message, and every write returns the updated state the page needs to redraw without a second request.

- Watchlists: list (with trial count, needs-review count, last checked, whether a saved search is on); create; rename; delete.
- A watchlist's views: needs-review queue; all trials (with review state, registry status, last successful check, failure flag); new matches; dismissed matches; summary for a period (and its text and CSV forms).
- Membership: add trials by NCT ID (bulk); remove a trial (returns an undo token); undo removal.
- Checks: start a check for updates or a full recheck for a watchlist; read its progress and result (trial outcomes and the saved-search outcome kept separate); retry failed.
- A trial: its header facts, details sections, unreviewed changes with IDs, history timeline, and the watchlists holding it.
- Review: mark change IDs reviewed (returns the review event); undo a review event.
- Search: run a query for a page; look up one NCT ID.
- Saved search: read; save or replace on a watchlist; turn off.
- New matches: add selected to the watchlist; dismiss selected (returns an undo token); restore.

### Look

- The design's teal accent, neutral greys, card and tab styles, typography hierarchy and spacing, implemented in one stylesheet with colours as custom properties. Not pixel-matched.
- One responsive layout: the sidebar collapses above the content below a breakpoint, tables reflow into rows, and nothing scrolls horizontally down to 390 px.

## Testing Decisions

- **A good test checks behaviour a user or the page can observe, through the highest seam that shows it**, never internal calls or SQL. A test names the behaviour in plain words, as the existing suite does.
- **Seam 1, the server's HTTP API, in-process.** The server is built by a factory that takes the database path and the registry fetch and search functions, so tests run it against a temporary database with the stub fetchers and finders the suite already uses (`make_fetcher`, `make_finder` and the captured NCT03412565 record in the test fixtures). All new domain behaviour is proven here: review by ID and its scope, review events and undo, failure recording and Retry failed, retention and resume, restore, lookup and the four error kinds, paging, the cap and totals, bulk-add outcomes, summary grouping, the CSV columns, the one-check-at-a-time rule.
- **The existing domain tests stay** (`test_check_trials`, `test_diff`, `test_briefing`, `test_found_trials`, `test_lists`, `test_search`, `test_watchlist`, `test_simulate` and the rest) and are updated where this spec changes a rule: retention instead of deletion, review by ID. Tests that exist only for retired code (the Streamlit app, the site, the in-browser transport, the deploy workflow) are deleted with it.
- **Seam 2, the browser.** Playwright (Python, a development dependency only) drives the real server in Chromium. A shared walk helper starts the server on a free port with a fresh temporary database and the stand-in registry, gives each worker its own browser, fails a walk on any console error or failed request, and takes screenshots into the feature's walks folder. Walks run at 1440 × 900 and 390 × 844. Every acceptance box about something a user sees names the walk that checks it.
- **The stand-in registry** is a small local HTTP server answering the two ClinicalTrials.gov API calls the app makes (one study by NCT ID; a study search with paging and a total count), serving captured records from the test fixtures, with switches to return not-found, server error and a slow response. Its fidelity check, run on demand and dated in `docs/agents/local/repo.md`: fetch one captured study live and compare its structure with the fixture.
- **The walk suite** is a separate pytest suite outside the fast unit folder, so the unit suite needs no browser. It becomes a gate check in `docs/agents/local/factory.json`, and the front-end paths become `user_facing` there, in the walk-tooling ticket.
- **Prior art:** `tests/conftest.py` (stub fetchers and finders, temporary database), `tests/test_check_trials.py` and `tests/test_found_trials.py` (domain behaviour through the module seam), and `tests/test_app.py` for the scenarios the current UI covers, which the new walks replace.

## Out of Scope

- Stopping a check midway; "Check this trial" on the trial page.
- The phone-specific designs on page 14: sticky footers, the view picker replacing tabs, the watchlist title as a picker. The layout is fluid instead.
- A check-activity page, and the cross-watchlist "Everything monitored" summary.
- The "Design sample · Simulated" header badge.
- Hosting, GitHub Pages, any server other than the analyst's own machine, logins, sharing and sync (ADR 0003).
- Migrating watchlists from the retired GitHub Pages site.
- Import and export of whole watchlists (ADR 0002's suggested next step stays a possible follow-up).
- Scheduled or automatic checking.
- Any change to which fields are monitored or how changes are detected.
- Browsers other than current Chrome and Safari.

## End State

The build is finished when all of the following hold, and not before. When they hold, it stops.

1. **Every numbered design note is covered.** Each of the 14 pages' numbered notes and its footer note, less the items ruled out above, maps to at least one acceptance box in a ticket, and each box is ticked with evidence (a walk, a test, or `needs-human` where only the user can judge). The coverage table, design page and note number → ticket and box, lives in the foundational ticket and is complete at hand-over.
2. **The old front end is gone.** No Streamlit, stlite, site build, in-browser transport or Pages workflow remains in the repository or its requirements, and nothing refers to them except the ADRs and closed tickets.
3. **Every check is green.** `python3 .claude/factory/gate.py checks` passes: unit, gate tests and the walk suite.
4. **The acceptance walk passes**, keyboard only, at 1440 × 900 and 390 × 844: start the app on an empty database; create a watchlist; search; select across two pages; add trials; save the search; check for updates; open a trial with a simulated change; review it; undo; review again; add a new match; dismiss one and restore it; view the summary; copy it; export the CSV.
5. **The exploration ticket is done**: its walkers' defects are fixed, each with the check that found it green.
6. **The user's hand-over ticket is done**: the user has started the app with the README's command and clicked through the acceptance journey themselves.

**Anything new the user asks for at or after hand-over is a follow-up spec, not a reopening of this one.** A defect against a box in this spec is fixed here; a wish beyond it is written down under Further Notes and carried to the next spec. This is what ends the build.

## Further Notes

- **Tickets, for `to-tickets`:** the foundational ticket is the server, its API seam with the factory and stub wiring, the domain changes the API needs first (change IDs, review by ID and review events), the design-note coverage table, and one thin end-to-end slice (open a watchlist's Needs review). Walk tooling comes before the first user-facing ticket: Playwright, the shared helper with its guards each shown to fail, the stand-in registry with its fidelity check, the `factory.json` checks and `user_facing` entries, and one walk through the thin slice. Then roughly one ticket per design page or pair of pages; the retirement of the old front end as its own ticket once the new one reaches the acceptance journey; the acceptance walk; the exploration ticket; and the user's hand-over ticket.
- **Areas for the exploratory walkers:** watchlists and review; trial page; find trials; saved search and new matches; summary and export; dialogs and administration.
- **ADR 0001 stands:** lead sponsor type matches the lead sponsor only, and the form's help text says so.
- **The screenshots of the current app** are in the UX overview PDF made on 8 November 2026 (`~/Downloads/Trial-Change-Monitor-UX-overview.pdf`); the design's "Current screens" footers refer to its numbering.
