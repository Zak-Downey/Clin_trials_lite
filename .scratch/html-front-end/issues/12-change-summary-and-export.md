# 12: Change summary and export

**Blocked by:** 04

**Status:** needs-triage

**Touches:** briefing.py, webapp/static/app.js, webapp/static/style.css, webapp/routes.py

**Spec sections (read these, not this ticket's paraphrase):** User Stories 83–90; Implementation Decisions › Domain changes ("The change summary"), › API (summary); Design coverage 10/*.

**What to build:** The Summary tab: This week (Monday to Sunday), This month (the calendar month) and Custom dates, filtering by detection time in the local zone. Headed with the period, trials, field changes, how many await review and how many are reviewed, and the time zone. Grouped by trial and then by check, each trial expandable to every transition, simulated changes labelled. Copy summary gives plain text with trial links; Export CSV gives one row per field change with the agreed columns. An empty period says so, keeps the controls and disables export with a reason.

- [ ] Walk: Summary offers This week, This month and Custom dates; the heading states the period, "N trials · M field changes", how many await review and how many are reviewed, and the time zone (design 10/1)
- [ ] Test: the period filters on detection time in the local zone, This week runs Monday to Sunday and This month is the calendar month, and reviewed changes are included (design 10/1)
- [ ] Walk: Custom dates opens labelled From and To with Apply and Cancel; the previous summary stays until both dates are valid and Apply is pressed; Cancel leaves it unchanged (design 10/2)
- [ ] Walk: the summary groups by trial and then by check, shows each trial's change count and checks with changes, and expanding a trial lists every field transition without merging repeats; simulated changes are labelled (design 10/4)
- [ ] Test: the summary keeps every transition of a field that moved in two checks, in order
- [ ] Walk: Copy summary puts plain text on the clipboard containing each trial's ClinicalTrials.gov link (design 10/3)
- [ ] Test: the CSV has one row per field change with watchlist, NCT ID, title, field, previous value, new value, registry-updated date, detected date and time, review status and simulated flag (design 10/3)
- [ ] Walk: Export CSV downloads that file for the shown period
- [ ] Walk: an empty period says "No changes detected in this period.", keeps the controls, disables export with its reason, and offers a wider range (design 10/F)

## Comments
