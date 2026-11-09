# Brief: replace the Streamlit front end with an HTML page

What the user asked for, and what they decided when the design was grilled (8 November 2026). The spec is read against this file before any ticket is written.

## The ask

> We are going to upgrade the front end from Streamlit to an HTML webpage. You can find the updated UI design here: `design.pdf` (this folder, 14 pages). I would like to turn this into a spec. If easier, we do not need to deploy to GitHub Pages. It can run locally. This spec needs to include a clearly defined end state so we do not get stuck in a build loop.

The user owns the UI and scope; the technical side was delegated.

## The design

`design.pdf`: 14 annotated pages. Its layouts, wording, numbered design notes and the note under each page are the requirements. Colours, spacing and type follow the mockups closely but are not pixel-matched.

## Decisions

1. **Local only.** The app runs on the user's machine and is opened in their browser. The GitHub Pages site, its in-browser (stlite/WebAssembly) runtime, its build script and its publish workflow are retired. A new ADR supersedes ADR 0002.
2. **No data migration.** Start fresh from a local database file.
3. **Scope of the design's proposed and optional items.** In: review events in the trial history; Undo review; review clears only the changes shown; View dismissed and Restore; check failure states with Retry failed and a per-trial last successful check; deleting a watchlist keeps monitoring history; Undo after removing a trial; search results paged 10 at a time with select-all per page. Out: Stop check; Check this trial.
4. **Desktop only.** No phone or small-screen work at all: the user does not expect phones to be used, and if they are needed they will be a future update (decided 8 November 2026, replacing the earlier "fluid down to 390 px"). Page 14 of the design and every phone clause elsewhere are out. The layout is designed at 1440 px wide and works without horizontal scrolling down to a 1024 px browser window, the smallest width the build supports.
5. **The "Design sample · Simulated" header badge is a mockup marker** and is not built. Per-trial "Simulated changes" labels are.
6. **Fidelity.** As under "The design" above.
7. **End state.** Every numbered design note on the 14 pages, less the items ruled out in 3 and 4, maps to at least one acceptance box proven by a browser walk or a test; Streamlit and the Pages tooling are deleted and every check is green; one keyboard-only end-to-end walk passes (create a watchlist, search, add trials, check for updates, review, undo, export); a final hand-over ticket for the user. Anything new the user wants after that is a follow-up spec, not this one.
8. **History is kept when a trial leaves its last watchlist** (removed, or its watchlist deleted). It stops being checked. Adding it back resumes from its history: the next check reports whatever moved meanwhile.
9. **Vocabulary**, as in `CONTEXT.md`: Watchlist; Saved search ("Saved search is on"); New matches; Add to watchlist (replacing Adopt); Check for updates; Full recheck.
10. **No check-activity page.** The design's "View check activity" menu item is dropped; History and the Change summary cover it.
11. **No cross-watchlist "Everything monitored" view.** Summary and export are per watchlist.
12. **Dates in the machine's local time zone**, named in the summary line.
13. **Search results capped at 100** (10 pages of 10), showing the registry's true total and saying when the cap cut the list. The same cap bounds new matches from one saved-search run.

Also agreed, proposed by the assistant and not objected to: trial details as the design's five sections with sponsor and status in "At a glance", missing values shown as "Not reported"; trial heading is the registry acronym, else the brief title; Undo review lasts until the user leaves the trial or acts again; deleting a watchlist is confirmed and cannot be undone; walks at 1440 px and 1024 px; current Chrome and Safari; README rewritten for the local app; one launch command; the simulator stays a developer tool; Next trial moves through Needs review; All trials sorts by title, latest change or trial status; "This week" is Monday to Sunday.

Test seams agreed: the server's HTTP interface (in-process, temporary database, stub registry); the browser (Playwright against the real server); a stand-in registry server for the walks.
