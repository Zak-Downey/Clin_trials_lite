# 18: A check counts and writes only the trials its watchlist still holds

**Blocked by:** None

**Status:** ready-for-agent

**Touches:** webapp/api_checks.py, tests/test_api_checks.py

**Spec sections (read these, not this ticket's paraphrase):** Round 1 findings (`.scratch/pr-1-review/findings/round-1.md`) 1 and 2: follow-up to ticket 07 (F13).

**What to build:** A trial removed from the watchlist while its check runs is dropped from the run's total, so a finished check reads "2 of 2", not "2 of 3". Membership is re-read after the trial's own fetch, before any write: a trial removed during its fetch is not marked checked and gets no change rows.

- [x] Test: a finished check after a trial was removed mid-run counts only the trials it still held (2 of 2, not 2 of 3) — test: test_a_finished_check_counts_only_the_trials_it_still_held_after_one_was_removed; red: .scratch/pr-1-review/red/18-unit-0312f9b.txt
- [x] Test: a trial removed during its own fetch is not marked checked and gets no change rows — test: test_a_trial_removed_during_its_own_fetch_is_not_marked_checked_or_given_changes; red: .scratch/pr-1-review/red/18-unit-0312f9b.txt

## Comments
