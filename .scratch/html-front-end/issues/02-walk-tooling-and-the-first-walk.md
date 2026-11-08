# 02: Browser-test tooling, the stand-in registry and the first walk

**Blocked by:** 01

**Status:** needs-triage

**Touches:** *

**Kind:** walk-tooling

**Spec sections (read these, not this ticket's paraphrase):** Testing Decisions › Seam 2, › The stand-in registry, › The walk suite; End State 3 and 4.

**What to build:** The walk suite every user-facing ticket proves its boxes with. Playwright for Python as a development dependency, a walk folder outside the unit tests, and a shared helper that starts the server on a free port with a fresh temporary database pointed at the stand-in registry, gives each worker its own browser, fails a walk on any console error, failed request or horizontal scrolling, and saves screenshots under `.scratch/html-front-end/walks/` (git-ignored). The stand-in registry answers the two ClinicalTrials.gov calls the app makes from the captured fixture records, with switches for not-found, server error, slow, **revise** and **register**, flipped over its own control endpoint. Then one walk through the thin slice from ticket 01.

- [ ] Playwright is a development dependency only; the walk suite lives outside the unit test folder and the unit suite runs without a browser
- [ ] The walk helper starts the server on a free port with a fresh temporary database and the stand-in registry, and runs at 1440 × 900 and 1024 × 768
- [ ] Each guard fails a walk when its condition occurs, each shown red on a deliberately broken page: a console error, a failed request, horizontal scrolling
- [ ] The stand-in registry serves one study by NCT ID and a paged study search with a total count from the captured fixtures, and its not-found, server-error and slow switches change the app's responses as the real registry would
- [ ] The stand-in's **revise** switch makes the next check for updates detect a change through the normal check path, and **register** makes the next saved-search run find a new match
- [ ] The stand-in's fidelity check fetches one captured study live and compares its structure with the fixture; its row is added to the Stand-ins table in `docs/agents/local/repo.md` with the date it was run
- [ ] `docs/agents/local/factory.json` gains the walk suite as a check named `walks`, the walk folder under `evidence.walk`, and the front-end paths under `user_facing`; `gate.py config` passes
- [ ] `docs/agents/local/repo.md`'s Walks section is filled in for the new tooling (tooling, helpers, evidence, shared plumbing, areas, viewports)
- [ ] Walk: the sidebar lists every watchlist with its trial count and the number of trials needing review, and a long watchlist name wraps instead of truncating (design 1/1)
- [ ] Walk: a watchlist opens on Needs review, listing only trials with unreviewed changes, newest detection first, headed with "N trials need review" and "M unreviewed field changes" (design 1/2)
- [ ] Walk: each queue entry shows heading, NCT ID, phase, sponsor, status, the changed field names, the detected time and the change count, with no selection checkboxes; a trial with simulated changes is labelled "Simulated changes" (design 1/F, 1/3)
- [ ] Walk: the trial heading and "Review changes" link to the same trial address (design 1/3)
- [ ] Walk: reloading and using Back and Forward keep the chosen watchlist and tab

## Comments
