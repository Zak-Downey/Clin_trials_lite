# 01: The walk runner re-runs a failed walk alone

**Blocked by:** None

**Status:** done

**Touches:** walks/run_walks.py, walks/test_run_walks.py

**Kind:** foundational

**Spec sections (read these, not this ticket's paraphrase):** Findings › F1. Root: `docs/agents/evidence.md` › The runner contract.

**What to build:** The "alone" re-run of a failed walk collects and runs that one walk and nothing else, so its verdict (`red alone` or `red under load, green alone`) is about that walk. Every later walk verdict in this spec rests on it.

- [x] Walk: the re-run of a failed walk is given only that walk's node id, and collects exactly one test (not the `walks` folder as well) — walk: test_runner_reports_red_alone_and_red_under_load_green_alone_in_one_run; red: .scratch/pr-1-review/red/01-walks-37ea56c.txt
- [x] Walk: in one run with a walk that is red alone and another that is red under load and green alone, the `## Result` section reports the first `red alone` and the second `red under load, green alone` — walk: test_runner_reports_red_alone_and_red_under_load_green_alone_in_one_run; red: .scratch/pr-1-review/red/01-walks-37ea56c.txt
- [x] Walk: the retained alone output of a failed walk holds that walk's run only (one test collected) — walk: test_runner_reports_red_alone_and_red_under_load_green_alone_in_one_run; red: .scratch/pr-1-review/red/01-walks-37ea56c.txt
- [x] The `Lacks:` line at the top of `walks/test_run_walks.py` no longer names the re-run — check: walks (the Lacks line now reads "a real browser walk")
- [x] The whole walk suite passes through `walks/run_walks.py` (the walks check) — check: walks

## Comments
