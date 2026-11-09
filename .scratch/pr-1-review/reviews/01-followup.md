# Review: ticket 01 (follow-up)
Tip reviewed: 9255def. Mutation sample: 4 tried, 1 caught. Prompt carried no Hand sample line; `mutate_paths` is empty, so the draw is from the changed lines of `walks/run_walks.py`.
Red file `.scratch/pr-1-review/red/01-walks-45a3a90.txt` (old code, tip 45a3a90): shows all five new/changed checks FAILED (including the four named in findings 1, 2, 3, 5), so each check can go red.

## Blocking
1. Option pass-through to the alone re-run is not checked | foundation finding 5 ("Its pytest args are also not passed to the alone re-run"); the test comment claims "the option reached the re-run (short traceback)" | walks/test_run_walks.py:123, walks/run_walks.py:90 | fixed — walk: test_runner_takes_targets_from_its_command_line_and_gives_options_to_each_re_run — red: .scratch/pr-1-review/red/01-walks-9255def-options.txt
   Mutant `pytest(options, alone, ...)` -> `pytest([], alone, ...)` survived (8 passed). The assertion `"test_wanted.py:" in alone` is also true under the default traceback, so it cannot fail. Assert something only `--tb=short` produces (e.g. no `def test_wanted` source lines in `alone`), or pass `-k`/`-m` and check what the re-run selected.
2. Target detection by existing path is not checked | foundation finding 5 | walks/run_walks.py:52 (`split_args`) | fixed — walk: test_runner_takes_targets_from_its_command_line_and_gives_options_to_each_re_run — red: .scratch/pr-1-review/red/01-walks-9255def-targets.txt
   Mutant dropping `and pathlib.Path(a.split("::")[0]).exists()` survived (8 passed). The only option in the test starts with `-`. Add a case where an option's value (e.g. `-k wanted`) is not a path and must stay an option, and a `file::node` target.

## Notes
1. Findings 1-4 verified: `test_gate_reads_the_runner_verdicts_with_walk_results` feeds stdout to `checks.walk_results`; the cap test counts 10 alone files and 2 "not re-run"; the same-name test needs two distinct paths; the cap mutant `>=` -> `>` was caught. | walks/test_run_walks.py | left: no change needed
2. `## Result` is appended to the output file after the tail print; section is written even when empty (header only). | walks/run_walks.py:93 | left: gate reads an empty section as no verdicts

## Not checked
Full walk suite (the diff touches only the runner and its tests); spec text beyond F1; gate code beyond calling `walk_results`.
