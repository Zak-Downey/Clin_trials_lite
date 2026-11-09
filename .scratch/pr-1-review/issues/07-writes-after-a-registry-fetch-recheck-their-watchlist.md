# 07: Writes after a registry fetch re-check their watchlist and membership

**Blocked by:** None

**Status:** done

**Touches:** webapp/api_membership.py, webapp/api_checks.py

**Spec sections (read these, not this ticket's paraphrase):** Findings › F12, F13. Root: Implementation Decisions › Domain changes (monitoring retention), › API (Checks).

**What to build:** Every write made after the lock was released for a registry call first re-reads what it writes to. `add_trials` re-reads the watchlist after the fetch and answers 404 `watchlist_not_found` if it is gone. A check re-reads membership under the lock before each step, skips a trial its watchlist no longer holds, and ends if the watchlist is gone. The run's `finally` sets `running = False` even when `finish_run` raises.

- [x] Test: a watchlist deleted while `add_trials` is fetching gets no `list_members` row, and the add answers 404 `watchlist_not_found` — test: test_a_watchlist_deleted_while_add_trials_is_fetching_gets_no_row_and_the_add_answers_404; red: .scratch/pr-1-review/red/07-unit-37ea56c.txt
- [x] Test: a trial removed from the watchlist while a check runs, held by no other list, is not fetched, not marked checked and gets no change rows — test: test_a_trial_removed_while_a_check_runs_is_not_fetched_marked_checked_or_given_changes; red: .scratch/pr-1-review/red/07-unit-37ea56c.txt
- [x] Test: a watchlist deleted while its check runs ends the run without checking its remaining trials — test: test_a_watchlist_deleted_while_its_check_runs_ends_the_run_without_checking_the_rest; red: .scratch/pr-1-review/red/07-unit-37ea56c.txt
- [x] Test: when `finish_run` raises, the run is no longer running and a new check of that watchlist is accepted — test: test_when_finish_run_raises_the_run_is_no_longer_running_and_a_new_check_is_accepted; red: .scratch/pr-1-review/red/07-unit-37ea56c.txt

## Comments
