# 07: Find trials: the search form and paged results

**Blocked by:** 02

**Status:** ready-for-agent

**Touches:** monitor.py, ctgov.py, webapp/static/app.js, webapp/static/style.css, webapp/routes.py, walks/standin_registry.py

**Spec sections (read these, not this ticket's paraphrase):** User Stories 52–61; Implementation Decisions › Domain changes ("Search returns a page and a total"), › API (Search); Design coverage 6/1, 6/F, 7/*.

**What to build:** Find trials with its Search tab. The form shows Condition, Intervention, Sponsor and Phase with the four-field rule above them; phases are labelled toggle buttons; More filters (lead sponsor type, trial status, start dates) is folded with its help text visible. Enter submits. After results arrive the form collapses to a plain-language summary with Edit search. Results show the registry's true total, ten per page, capped at 100 with the cap stated. Zero results and registry errors keep the query and offer a way on. Selecting and adding results is ticket 08.

- [ ] Walk: the form opens expanded with "Start with at least one of these four fields" above Condition, Intervention, Sponsor and Phase (design 6/1, 7/1)
- [ ] Walk: submitting with none of the four shows the error beside that group and keeps every value typed, including More filters (design 7/1)
- [ ] Walk: Phase is a row of labelled buttons; several can be selected, a selected one differs by more than colour, and Clear all clears them (design 7/2)
- [ ] Walk: More filters starts folded; opened, it shows lead sponsor type, trial status with every selected status written out in full, and the two start dates, with the help lines "Sponsor type uses the lead sponsor, not collaborators" and "Date filters exclude trials without a reported start date" visible, not in tooltips (design 7/3)
- [ ] Walk: Enter in any field submits the search (design 7/4)
- [ ] Walk: after results arrive the form is replaced by a one-line summary of the query and its filters with "Edit search", which reopens the form with every value kept (design 6/1)
- [ ] Test: a search returns one page of up to 10 rows, the registry's total for the same query on every axis, and whether the 100-result cap applies
- [ ] Walk: results show "N matches" and "1–10 of N", page with Next and Previous without any nested scrolling area, and over the cap say "Showing the first 100 of N. Narrow your search to see the rest" (design 6/F)
- [ ] Walk: zero matches keep the query summary and offer "Edit search" and "Clear optional filters" (design 7/F)
- [ ] Walk: with the stand-in returning a server error, the form and values stay and "Retry" runs the search again, never a blank results area (design 7/F)

## Comments
