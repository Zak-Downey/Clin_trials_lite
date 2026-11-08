# 05: Trial page: details, history and watchlist membership

**Blocked by:** 04

**Status:** ready-for-agent

**Touches:** storage.py, monitor.py, webapp/static/app.js, webapp/static/style.css, webapp/routes.py

**Spec sections (read these, not this ticket's paraphrase):** User Stories 43–51, 98; Implementation Decisions › Domain changes ("Retention", "The trial heading", "Trial details"); Design coverage 4/3, 4/4, 5/*.

**What to build:** The rest of the trial page. The header uses the acronym, else the brief title, and shows the last successful check with a warning when the latest check failed. Trial details: an At a glance panel and the five sections, expandable, with "Not reported" for missing values. History: one newest-first timeline of detections, reviews and undone reviews, the start of monitoring and any unmonitored gap, each check expandable to every transition. The ⋯ menu shows the watchlists holding the trial and Remove from this list, with Undo. Removing a trial from its last watchlist keeps its history; adding it back resumes it.

- [ ] Walk: the heading is the registry acronym when there is one, else the brief title; the full official title and every identifier appear under Identity, untruncated (design 5/2)
- [ ] Walk: the header shows "Last checked <time>", and a trial whose latest check failed shows a labelled warning beside it
- [ ] Walk: At a glance shows registry status, phase, lead sponsor, enrolment, the ClinicalTrials.gov link and when monitoring began (design 5/1)
- [ ] Walk: Trial details shows Identity & study design, Conditions & eligibility, Interventions & arms, Endpoints, and Dates & results; long sections expand on demand; a section holding a field with an unreviewed change is never collapsed (design 5/3)
- [ ] Test: every field of the eight existing information groups lands in exactly one of the five sections or At a glance; walk: a field the registry omits shows "Not reported" (design 5/F)
- [ ] Walk: History lists detections, reviews ("Marked N changes from the HH:MM check as reviewed"), undone reviews and the start of monitoring newest first, and expanding a check shows every previous-to-new transition, reviewed ones included (design 4/3, 4/4)
- [ ] Test: removing a trial from its last watchlist keeps the trial, its snapshots and its changes, and no check fetches it; adding it back resumes without a new baseline and the next check reports what moved meanwhile
- [ ] Walk: History shows a period when the trial was not monitored as "Stopped monitoring" and "Resumed monitoring" (design 4/3)
- [ ] Walk: the ⋯ menu lists the watchlists holding the trial and "Remove from this list"; removing offers Undo, which restores the membership; removing touches no other watchlist (design 5/4, 13/3)

## Comments
