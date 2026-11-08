# 03: Check for updates, with honest progress, failure and completion states

**Blocked by:** 02

**Status:** needs-triage

**Touches:** storage.py, monitor.py, webapp/static/app.js, webapp/static/style.css, webapp/routes.py, walks/standin_registry.py

**Spec sections (read these, not this ticket's paraphrase):** User Stories 14–24; Implementation Decisions › Domain changes ("Check failures persist per trial", "Retry failed"), › API (Checks); Design coverage 1/4, 2/3, 12/*.

**What to build:** The watchlist header shows its name, trial count and last-checked time, with "Check for updates" and "Add trials" (the latter opens Find trials with this watchlist as destination; Find trials itself arrives in 07). Pressing Check for updates runs the check on a server thread while the analyst keeps reading; the page polls progress. The status area shows the four states of design page 12. A failed check is recorded against the trial without moving its last successful check; Retry failed re-checks only those trials. The saved search's outcome is reported apart from the trials'.

- [ ] Walk: the header shows the watchlist name, "N trials monitored" and "Last checked <local time>", and the only checking control is "Check for updates", with no wording implying scheduled or live monitoring (design 1/4)
- [ ] Walk: during a check, "Checking for updates…" shows "N of M trials checked" and what runs next with a progress bar, while the queue and an open trial stay readable and usable (design 12/1)
- [ ] Test: a second check for the same watchlist is refused while one runs; walk: the button is disabled with its reason while a check runs (design 12/1)
- [ ] Walk: a check where the stand-in fails one trial shows "Check incomplete", "N of M trials checked · 1 trial could not be checked", the saved search's outcome on its own line, "Retry failed" and "Show details", and never an all-clear (design 12/2)
- [ ] Test: a failed check records its time and error kind on the trial and leaves its last successful check unchanged; a later success clears the failure (design 2/3, 12/2)
- [ ] Test: Retry failed re-checks only the trials whose check failed in the watchlist's last check run
- [ ] Walk: a check that finds nothing new says "Check complete · No new changes detected" with the number checked, the time, and "N trials still need review from earlier checks", and the queue keeps its earlier entries (design 12/3)
- [ ] Walk: with nothing to review, Needs review shows "All caught up", "No changes awaiting review. Last checked <time>" and "View all trials", and the tab does not change by itself after a check (design 12/4)
- [ ] Test: a watchlist's last-checked time is when its most recent check for updates finished
- [ ] Walk: after the stand-in's revise switch, Check for updates adds the changed trial to Needs review and the sidebar count rises, without the page switching tabs

## Comments
