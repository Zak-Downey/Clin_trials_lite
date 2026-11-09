# 09: The Summary walk checks the count it names and does not lean on the clock

**Blocked by:** 01

**Status:** ready-for-agent

**Touches:** walks/test_summary_walk.py

**Spec sections (read these, not this ticket's paraphrase):** Findings › F15. Root: `docs/agents/evidence.md` › Every check can fail.

**What to build:** The Summary walk asserts the field-change count it seeds, not a value compared with itself, and seeds its changes at times inside the period whatever the hour of the run.

- [x] Walk: the Summary walk's heading assertion compares the trial count and the field-change count each with a fixed expected number, and fails when one seeded change is dropped — walk: test_walk_summary_offers_three_periods_and_a_heading_with_the_period_counts_and_zone; red: .scratch/pr-1-review/red/09-walks-beffd04.txt
- [x] Walk: the Summary walk's seeded changes fall inside This week and This month at any time of the run, including the first half hour of a Monday and of the 1st (shown by seeding against a fixed clock, or by the seed's stamps being computed from the period's bounds) — walk: test_walk_summary_offers_three_periods_and_a_heading_with_the_period_counts_and_zone (the seed's earlier stamp is computed from the later of This week's and This month's start in America/New_York and now, so it is inside both at any hour)

## Comments
