# 02: A wobbling browser test fails the checks

**What to build:** A walk that is red beside the others and green when run alone now ends the `walks` check red. The setting exists: `FLAKY_IS_RED` in `walks/run_walks.py` becomes true, and the test that pins it is changed on purpose. The runner's printed lines name each such walk and say that it wobbled: failed beside the others, passed alone. The record of wobbling walks (`flaky.jsonl`) and the hand-over page's list of them are unchanged. `docs/agents/local/repo.md` says, where it describes the walk runner, that a wobble is red, why (a walk that needs a second go is reading something too early, and on a slower machine fails outright: E-039, E-040), and what to do (make the walk wait for what it reads; never a retry or a fixed pause). It also says this is on trial until the next retro. The change names nothing of this product. Spec: `.scratch/kit-phase-5/spec.md`, "A wobble is red".

**Blocked by:** 01

**Status:** done

- [x] Red first, with a hand-made first run and re-run as the runner's tests already use: a walk red beside the others and green alone ends the run red and is named with the word for a wobble; a walk red both times is reported as before; a run with neither is green
- [x] The record of wobbling walks and the page's list of them read as they did before this ticket
- [x] `repo.md` says a wobble is red, why, what to do, and that it is on trial
- [x] A full `python3 checks.py`, not quick and not picked, ends green on this ticket's commit

## Comments

- `FLAKY_IS_RED` is now true in `walks/run_walks.py`; each wobbling walk adds a line `<node id> wobbled: failed beside the others, passed alone` to the `## Result` section (printed and written to `walks-run.txt`). The result lines, `flaky.jsonl` and `handover.py` are untouched, and `tests/test_handover.py` passes as before.
- Tests, seen red first on the hand-made once-red walk (exit 0 where 1 was wanted): `walks/test_run_walks.py::test_a_walk_red_beside_the_others_and_green_alone_ends_the_run_red_and_is_named_as_a_wobble`, `::test_a_walk_red_both_times_is_reported_red_alone_and_not_as_a_wobble`; a run with neither stays green in `::test_a_run_where_every_walk_passed_first_time_records_that_none_was_flaky`. Changed on purpose because the spec changed the behaviour: `::test_runner_is_red_when_a_walk_is_red_alone_and_when_a_run_failed_with_nothing_to_re_run` (a flaky-only result now exits 1) and the switch-off test `test_a_run_whose_only_failures_were_flaky_exits_0_with_the_switch_off_and_1_with_it_on` is replaced by the first new test.
- `docs/agents/local/repo.md`, the walk suite line: a wobble is red, why (E-039, E-040), what to do, on trial until the next retro.
- A full `python3 checks.py` (not quick, not picked) ran green on the tree of this commit: lint, patterns, escapes, unit, walks all green in 2.1 min; no walk wobbled, so the walks check was not turned red.
