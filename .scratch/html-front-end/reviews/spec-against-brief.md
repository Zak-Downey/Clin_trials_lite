# Spec against brief: html-front-end

Read on main at 6c3dc35. Brief: `.scratch/html-front-end/brief.md`. Spec: `.scratch/html-front-end/spec.md`. Design: `design.pdf`, all 14 pages read both as extracted text and as rendered images (numbered notes, footer notes and mockup wording). Also read: `CONTEXT.md` (vocabulary entries only), ADR 0003's head, `docs/agents/local/factory.json`, and `docs/agents/evidence.md`.

Exclusions applied, as the dispatch says: decisions 3 (Stop check, Check this trial), 4 (page 14's sticky footers, view picker, list-title picker), 5 (header badge), 10 (check activity) and 11 (Everything monitored).

Counts: 5 blocking, 17 notes.

Most of the brief and design is in the spec. Every item in decision 3 has a story. The vocabulary (decision 9) follows the brief where the design's mockups differ: "Saved search is on", not the mockup's "New-trial search is on"; "Full recheck", not "Recheck all monitored fields". Decisions 8, 12 (summary), 13 (search) and the "also agreed" list all appear. The findings are about the End State, plus a set of design-note clauses with no story.

---

## Blocking

### B1. End State 1 accepts `needs-human` as proof, which the brief does not allow and the repo does not count as a tick

- Brief, decision 7: "Every numbered design note ... maps to at least one acceptance box **proven by a browser walk or a test**".
- Spec, End State 1: "each box is ticked with evidence (a walk, a test, **or `needs-human` where only the user can judge**)".
- `docs/agents/evidence.md`: "A ticked box has at least one of the first five. An unticked box has `needs-human`, or it is open." So a `needs-human`-only box is not ticked, and End State 1 asks for something the gate's box audit cannot record.

The spec loosens the brief. Any design note can be covered by a `needs-human` box. Fix: every note maps to at least one box proven by a `walk:` or `test:`. `needs-human` may sit next to that proof (for the wording or look) but never replaces it.

### B2. The excluded set is not listed, so End State 1 is not finite or checkable

- Brief, decision 7: "less the items ruled out in 3 and 4". (The dispatch adds 5, 10 and 11.)
- Spec, End State 1: "less the items **ruled out above**". "Above" is the whole Out of Scope section, which also holds items that are not design notes (scheduled checking, import/export, browsers). Several notes are only partly ruled out:
  - 12/1: Stop is out, but "Keep the current list and open trial readable. Prevent duplicate checks" is in.
  - 5/4: Check this trial is out, but "The menu contains list membership and Remove from this list" is in.
  - 13/1: check activity is out, but "One task per dialog ... Never place creation, renaming and deletion in the same expanded form" is in.
  - 14/1: the picker is out, but "Two top-level destinations fit without a hamburger menu" is in.
  - 14/2: the view selector is out, but "Keep title, ID and what changed visible ... counts remain explicit" is in.
  - 14/4: the sticky footer is out, but "Aim for 44 px targets; use real controls, clear focus and text labels, not colour alone" is in.
  - Two phone-only clauses not on page 14 are in neither list: 7/4 "On a phone, the Search action stays at the bottom of the viewport; the form scrolls behind it with padding", and 5/1 "On phones this panel becomes a compact section above the details". Decision 4 names only "the phone-specific designs on page 14 (sticky footers, ...)". The spec's Out of Scope also names only page 14, and no story covers either clause. They are therefore silently in scope and unbuilt, or silently out.
- Mapping by note: "maps to at least one acceptance box" means a note with three requirements counts as covered by one box that tests one of them.

Fix: put a table in the spec (not only in the foundational ticket) listing every note and footer by page/number, 14 × 4 notes + 14 footers = 70 rows. Mark each in, out (with the decision that rules it out), or partly in (with the clause that remains). Map at clause level for the partly-in rows. Decide 5/1 and 7/4 explicitly.

### B3. End State 5, the exploration ticket, has no bound, and the brief does not ask for it

- Brief, decision 7, lists four things: note coverage; Streamlit and the Pages tooling deleted and every check green; one keyboard walk; a hand-over ticket. "Anything new the user wants after that is a follow-up spec".
- Spec, End State 5: "**The exploration ticket is done**: its walkers' defects are fixed, each with the check that found it green."

This adds a fifth condition, and nothing limits what a walker may call a defect or how many rounds run. That is the build loop the user's ask ("a clearly defined end state so we do not get stuck in a build loop") rules out. The spec's own closing rule limits fixes to "A defect against a box in this spec". End State 5 does not repeat that limit, and it does not say there is one round. Fix: one exploration round. Fix only walker findings that break a box or a design note in scope. Everything else goes under Further Notes for the follow-up spec.

### B4. End State 2 cannot be met as written

- Spec, End State 2: "nothing refers to them except the ADRs and closed tickets."
- Seen on main (`grep -ril streamlit`): Streamlit is named in this feature's own `spec.md` and `brief.md`, in the earlier features' `spec.md` files (`.scratch/github-pages-deployment/spec.md`, `.scratch/trial-change-monitor/spec.md`), which are specs and not tickets, and in `docs/agents/local/repo.md`. It is also in kept domain modules and tests the spec retains: `monitor.py:1133`, `display.py:3,38,130,252,335,351,587`, `tests/test_lists.py:6`, `tests/test_watchlist.py:5`, `tests/test_display.py:324`.
- Brief, decision 7, asks only: "Streamlit and the Pages tooling are deleted".

Literally, the condition can never hold, because the spec names itself. Fix: state it as a check that can be run. No `streamlit`/`stlite` import, dependency, workflow or file remains. A named grep finds no match outside `docs/adr/` and `.scratch/`. Comments in kept modules are reworded.

### B5. The acceptance walk (End State 4) needs a step it cannot take keyboard-only, and the spec does not say how

- Spec, End State 4: "start the app on an empty database; ... check for updates; **open a trial with a simulated change**; review it ...".
- Brief, "also agreed": "the simulator stays a developer tool". Spec story 103: "the simulator runnable from the command line".

On an empty database, a trial added in the walk takes its baseline (story 68). It has a change after "check for updates" only if the stand-in registry serves a different record, or someone runs the simulator CLI between steps. Neither is a keyboard action in the page, and the spec does not say which happens. The brief's walk step list ("create a watchlist, search, add trials, check for updates, review, undo, export") also needs a change to review. Fix: name the mechanism (for example, a stand-in registry switch that serves a later version of the record, or a walk fixture step that runs the simulator), and say it is the walk's only non-keyboard step.

---

## Notes

### Design notes and footers with no story (in scope; the coverage table needs them)

**N1. 2/4: All trials opens Trial details.** Design: "Open Trial details from this inventory; the Changes tab is available immediately." Spec story 31 says only "opening on Changes when I come from the queue". It does not say which tab opens from All trials.

**N2. 4/1 and 4/2: the Reviewed label and the count update.** Design 4/1: "remain on Changes with a Reviewed label". Design 4/2: "The queue count updates, but the page and scroll position do not jump." Spec story 40 has the confirmation and "the page not jumping". It does not have the Reviewed label on Changes, or the queue/sidebar counts updating in place.

**N3. 4/3: "monitoring events".** Design: "Combine field changes, monitoring events and review events." Spec story 48: "change detections, reviews (with time and count) and the start of monitoring". Under decision 8 a trial can stop and resume being monitored ("It stops being checked. Adding it back resumes"). The spec does not say whether History shows that gap. Without it, the analyst cannot tell "nothing changed" from "not watched".

**N4. 5 mockup: the trial header's last-checked time.** The page-5 header reads "NCT03275285 · Last checked 8 Nov 2026, 16:45". 2/3 says freshness "belongs to each trial". Spec stories 43–44 give the trial page no last-successful-check time or failure warning. Only All trials has one (story 27).

**N5. 6/3: selection kept when "returning".** Design: "Keep selection when viewing a trial, paging or returning." Spec story 63: "persist across pages and while I look at a trial's details". The spec drops "returning", for example leaving for Watchlists and coming back to Find trials.

**N6. 6/4: the action bar reserves space.** Design: "The action bar appears on selection and reserves space below results." Spec story 64 says when the bar appears but not that it must not cover results. Story 37 says this only for the trial page's bar. The same gap applies to the New matches bar (page 9).

**N7. 9/4 and 9/1: the scope and label of dismissal.** Design 9/4: "nothing is deleted from another list". Design 9/1: "New matches are results of the saved search, not recently registered studies and not changes to monitored trials. Keep the label precise." Neither the per-watchlist scope of a dismissal (as a domain rule) nor the wording of the label has a story.

**N8. 13/2: return to the same view.** Design: "Saving or cancelling returns to the same view and scroll position." Spec story 97 covers focus return only.

**N9. 14/3 and 14/4: the narrow-width clauses not ruled out.** Design 14/4: "Aim for 44 px targets". Design 14/3: "Previous first, Now second" when stacked. Spec story 32 stacks only "when the values are long", and nothing names the 44 px target. Spec "Look": "tables reflow into rows", against 14/2's "Keep title, ID and what changed visible". The intent matches, but nothing says what must stay visible.

### Brief items the spec narrows

**N10. Deleting a watchlist cannot be undone.** Brief, "also agreed": "deleting a watchlist is confirmed and cannot be undone". Spec story 96 lists what the dialog says, but not that the deletion is final. That matters because nearly every other destructive action in the spec offers Undo.

**N11. Safari.** Brief: "current Chrome and Safari". The spec puts other browsers out of scope, but its walks run "in Chromium" only (Testing Decisions, Seam 2). No End State item checks Safari. Either add a WebKit run (Playwright has one) or a hand-over `needs-human` for Safari, or say Safari is unverified.

**N12. "Start fresh" against reusing `monitor.db`.** Brief, decision 2: "No data migration. Start fresh from a local database file." Spec, Shape: "The database location stays as it is today: `MONITOR_DB` if set, else `monitor.db` in the folder the app is started from". The schema gains review events, check failures and retention. The spec does not say what happens when the new server finds an old-schema `monitor.db` from local Streamlit use: migrate it (which the brief rules out), refuse it, or start a new file.

**N13. The new-matches cap shown on screen.** Brief, decision 13: "showing the registry's true total and saying when the cap cut the list. The same cap bounds new matches from one saved-search run." The spec's domain section has "the result says when the cap applied" for new matches. No story shows it in the New matches tab or the check result.

**N14. Local time zone beyond the summary.** Brief, decision 12: "Dates in the machine's local time zone, named in the summary line." The spec applies local time to the summary (story 85, domain). It does not say that Detected, Last checked and History times are local too.

**N15. "View details" for a trial not yet monitored.** Design 6/3 and page 9 show "View details" on search results and new matches. Spec stories 62 and 78 ask for title links that open details. The API's "A trial" resource implies a monitored trial (changes, history, watchlists holding it). "Look up a trial" returns only "NCT ID, heading, official title, sponsor and status". The spec does not say what the details view of an unmonitored trial shows, or which call serves it.

### What the spec adds that the brief does not ask for (acceptable unless the user objects)

**N16. Additions, technical side delegated.**
- Story 6 and Shape: URL routing, so Back, Forward and reload restore state.
- Story 101: the app reachable only from localhost.
- The stdlib-only server with no framework and no build step.
- Server-enforced one check at a time (design 12/1 asks only to "Prevent duplicate checks").

All are within "the technical side was delegated". End State 1 also adds footer notes to the coverage, which matches the brief's "The design" section ("the note under each page are the requirements"). Decision 7 does not say this, and the extra coverage is welcome.

**N17. The acceptance walk is wider than the brief's.**
- Brief, decision 7: "one keyboard-only end-to-end walk passes (create a watchlist, search, add trials, check for updates, review, undo, export)".
- Spec, End State 4, runs it at two viewports and adds: select across two pages; save the search; open a simulated change; review again; add a new match; dismiss and restore; view the summary; copy it.

This is a superset, so it does not contradict the brief. Two of the additions are costly:
- "copy it" needs clipboard permission in Playwright.
- "add a new match" needs the stand-in registry to return a result the saved search did not hold at save time. That is the same unstated-mechanism problem as B5.

End State 6 also makes completion depend on the user clicking through. The brief asks only for "a final hand-over ticket for the user". Both are reasonable; the user should know they were added. "This month" (story 83) is also undefined, where the brief defines only "This week". Probably the calendar month, but say so.

---

## Not read

- The rest of `CONTEXT.md` beyond the vocabulary entries, ADRs 0001 and 0002, and the body of ADR 0003 past its first paragraphs.
- `docs/agents/tickets.md`, `walkthrough.md`, `orchestrator.md`.
- The UX overview PDF the spec's Further Notes cite (`~/Downloads/Trial-Change-Monitor-UX-overview.pdf`), and the design's "Current screens" footers, which point into it.
- No code beyond the `grep` for Streamlit references in B4.
