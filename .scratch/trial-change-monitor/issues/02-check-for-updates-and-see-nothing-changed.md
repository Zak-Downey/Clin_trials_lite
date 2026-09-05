# 02: Check for updates and see nothing changed

**What to build:** The analyst presses a single "Check all" button and the app works through every trial on the watchlist, showing progress as it goes so the page never looks frozen. For each trial it compares the registry's own last-updated timestamp against what was stored at the last check. When the record hasn't been touched, it stops there rather than doing the expensive comparison — this keeps checks fast as the watchlist grows.

Each trial's "last checked" time updates, and the feed honestly reports that nothing changed.

Against NCT03412565 — a completed trial last updated in April 2025 — "nothing changed" is the genuinely correct answer, so this slice is verifiable against live data without fabricating anything.

**Blocked by:** 01

**Status:** ready-for-human

- [x] A single control re-checks every trial on the watchlist
- [x] Progress is visible to the analyst while the check runs
- [x] Trials are checked one at a time with a short pause between them, to stay polite to a public government API
- [x] A trial whose registry record is untouched since the last check short-circuits without a full comparison
- [x] Each trial's "last checked" time updates whether or not anything changed
- [x] The analyst is clearly told when a check found no changes
- [x] A trial that fails to fetch reports its error without aborting the rest of the run
- [x] Tests cover: the short-circuit path, the last-checked update, and one trial failing mid-run while others succeed
- [x] Verified by hand: checking NCT03412565 against the live API reports no changes
