# 01: Add a trial and see its profile

**What to build:** An analyst opens the app with a single command and is shown an empty watchlist with a box to paste an NCT ID. Pasting a valid ID fetches that trial from ClinicalTrials.gov, records a baseline of its current state, and adds it to the watchlist showing NCT ID, lead sponsor, brief title and overall status. Expanding the row reveals every monitored field of the trial's profile. The feed shows a "started monitoring" entry, so the analyst gets visible confirmation the tool is working before anything has changed.

Pasting an ID that doesn't exist, or attempting this while ClinicalTrials.gov is unreachable, shows an error next to the input and leaves the watchlist exactly as it was. No retries.

Adding a trial records the baseline only — it must not report the trial's forty-one fields as forty-one changes.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] The app starts with one command and serves a page locally
- [x] An NCT ID can be pasted to begin monitoring a trial
- [x] A newly added trial appears in the watchlist with NCT ID, lead sponsor, brief title and overall status
- [x] The watchlist row expands to show all monitored profile fields
- [x] Adding a trial writes a baseline record of the trial's state and produces no change entries
- [x] The stored record retains the raw registry response with the results section removed, not just the derived profile
- [x] A "started monitoring" entry appears in the feed with a timestamp
- [x] An unknown NCT ID shows an inline error and leaves stored state untouched
- [x] An unreachable API shows an inline error and leaves stored state untouched
- [x] Adding a trial already on the watchlist does not create a duplicate
- [x] The database file is git-ignored
- [x] The trial-fetching function is injectable so tests never touch the network
- [x] Tests cover: successful add, duplicate add, unknown ID, and API failure — driven through the fetching seam against a temporary database
- [x] Verified by hand against the live record for NCT03412565
