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
- [x] Walk: the gate's `checks.walk_results` reads the runner's verdicts from a real run (the `## Result` section is in the named file, in the gate's line shape) — walk: test_gate_reads_the_runner_verdicts_with_walk_results; red: .scratch/pr-1-review/red/01-walks-45a3a90.txt
- [x] Walk: at most 10 red walks are re-run alone; the rest are listed red as "not re-run" and the gate still reads all — walk: test_runner_re_runs_at_most_ten_red_walks_alone_and_lists_the_rest_as_red; red: .scratch/pr-1-review/red/01-walks-45a3a90.txt
- [x] Walk: same-named walks in different files keep separate alone outputs — walk: test_runner_keeps_the_alone_output_of_same_named_walks_in_different_files_apart; red: .scratch/pr-1-review/red/01-walks-45a3a90.txt
- [x] Walk: targets on the command line are the run's targets and options reach each re-run — walk: test_runner_takes_targets_from_its_command_line_and_gives_options_to_each_re_run; red: .scratch/pr-1-review/red/01-walks-45a3a90.txt

## Comments
