# 07: Writes after a registry fetch re-check their watchlist and membership

**Blocked by:** None

**Status:** ready-for-agent

**Touches:** webapp/api_membership.py, webapp/api_checks.py

**Spec sections (read these, not this ticket's paraphrase):** Findings › F12, F13. Root: Implementation Decisions › Domain changes (monitoring retention), › API (Checks).

**What to build:** Every write made after the lock was released for a registry call first re-reads what it writes to. `add_trials` re-reads the watchlist after the fetch and answers 404 `watchlist_not_found` if it is gone. A check re-reads membership under the lock before each step, skips a trial its watchlist no longer holds, and ends if the watchlist is gone. The run's `finally` sets `running = False` even when `finish_run` raises.

- [ ] Test: a watchlist deleted while `add_trials` is fetching gets no `list_members` row, and the add answers 404 `watchlist_not_found`
- [ ] Test: a trial removed from the watchlist while a check runs, held by no other list, is not fetched, not marked checked and gets no change rows
- [ ] Test: a watchlist deleted while its check runs ends the run without checking its remaining trials
- [ ] Test: when `finish_run` raises, the run is no longer running and a new check of that watchlist is accepted

## Comments
