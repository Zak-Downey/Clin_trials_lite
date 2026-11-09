# 06: Find trials keeps every sponsor type on edit and shows a refused search by its kind

**Blocked by:** 01, 05

**Status:** needs-triage

**Touches:** webapp/static/views/find.js, monitor.py, webapp/api_search.py, webapp/api_saved_search.py

**Kind:** design

**Spec sections (read these, not this ticket's paraphrase):** Findings › F10, F11. Root: User Stories 52–61, 76; Implementation Decisions › API (errors as kinds); Design coverage 7/1, 7/3, 7/F.

**What to build:** Lead sponsor type holds several values, as Trial status does, so a query with two survives Edit search and Replace saved search. `monitor._refuse_unanswerable` raises its two refusals with their own kinds, which the handlers pass through without reading the message. The page shows `nothing_asked` and `bad_dates` beside their fields with the form open, and keeps Retry for `registry_error`.

- [ ] Test: an empty query and an inverted start-date window are refused with kinds `nothing_asked` and `bad_dates`, and changing the wording of either message does not change its kind
- [ ] Walk: a saved search with lead sponsor types Industry and NIH, opened with Manage saved search, Edit search, then Search trials, still reads "Industry or NIH" and keeps both `sponsor_type` values in the address
- [ ] Walk: Search trials with the start dates the wrong way round shows the swap-dates message beside the date fields with More filters open, and no Retry
- [ ] Walk: a registry error still shows the error box with Retry, keeping the form

## Comments
