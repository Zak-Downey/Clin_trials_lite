# 06: All trials: the whole watchlist, easy to scan

**Blocked by:** 03, 05

**Status:** ready-for-agent

**Touches:** webapp/static/app.js, webapp/static/style.css, webapp/routes.py

**Spec sections (read these, not this ticket's paraphrase):** User Stories 25–30; Design coverage 2/*.

**What to build:** The All trials tab: one row per trial with its title link, phase and sponsor, registry status, review state and last successful check (with a failure warning). A filter that searches only this watchlist and says so, and sorting by title, latest change or trial status. A title opens the trial on Trial details. The tab the analyst chooses is remembered; the default entry stays Needs review.

- [ ] Walk: All trials lists every trial with title, phase and sponsor, registry status, review state and last successful check; headers stay visible while scrolling and long titles wrap onto taller rows (design 2/4)
- [ ] Walk: the review state reads "N changes", "Reviewed" or "No changes", independent of the registry status in its own column (design 2/2)
- [ ] Walk: a trial whose latest check failed shows a labelled warning and keeps its earlier last-successful time (design 2/3)
- [ ] Walk: "Filter by title, NCT ID or sponsor" narrows the table to this watchlist's matching trials and is labelled as separate from searching ClinicalTrials.gov (design 2/1)
- [ ] Walk: sorting by title, latest change and trial status each reorder the table
- [ ] Walk: a title opens the trial on Trial details, with Changes available at once (design 2/4)
- [ ] Walk: a watchlist opens on Needs review; choosing All trials, leaving and returning keeps All trials; a check or review that changes the counts does not switch the tab (design 2/F)

## Comments
