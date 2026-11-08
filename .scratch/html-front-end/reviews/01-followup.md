# Follow-up: ticket 01 foundation read

Tip reviewed: 58c38db

1. Host/Origin not checked | blocking — fixed — test: test_a_foreign_host_header_is_refused, test_a_write_from_a_foreign_origin_or_without_json_is_refused — red: .scratch/html-front-end/red/01-unit-58c38db.txt
2. Folded move carries one change ID | blocking — fixed — test: test_a_folded_move_carries_every_id_it_folds_and_is_reviewed_only_if_all_are — red: .scratch/html-front-end/red/01-unit-58c38db.txt
3. Queue and /changes count differently | design — fixed — test: test_a_value_and_its_qualifier_moving_together_are_one_change_with_both_ids — red: .scratch/html-front-end/red/01-unit-58c38db.txt
4. Two servers on one database | design — fixed — test: test_a_second_run_on_the_same_database_points_at_the_running_server — red: .scratch/html-front-end/red/01-unit-58c38db.txt
5. Handlers must remember ctx.lock | sweep — fixed: the dispatcher takes the lock around every handler; handler locks removed. Ticket 03 must not hold it across registry fetches (noted in the dispatcher comment).
6. Time zone mismatch in when() | sweep — fixed: formats the wall clock in iso as UTC, labelled with the server zone (JS, no browser walk here).
7. Stand-ins table and docstring | sweep — fixed — doc: docs/agents/local/repo.md#Stand-ins
8. Errors at start are tracebacks | nit — fixed — test: test_a_busy_port_or_a_missing_folder_is_a_plain_line_not_a_traceback — red: .scratch/html-front-end/red/01-unit-58c38db.txt
9. user_version stamped back | nit — fixed — test: test_a_database_from_a_later_version_is_not_stamped_back — red: .scratch/html-front-end/red/01-unit-58c38db.txt
10. Wording differs from the spec | nit — fixed: heading, "Simulated changes", "All caught up", sidebar shows both numbers (JS, unchecked in a browser); lowercase nct in the changes route now answers trial_not_found.

## Reviewer (follow-up)

Tip reviewed: befbda2. Closures 1-4, 8, 9 checked against the red file (all named tests FAILED there; they pass now, 479 passed). No Hand sample in the prompt. No mutate_paths, so the draw was by hand over the whole diff. Mutation sample: 5 tried, 4 caught: `all`->`any` in history (caught), POST JSON check disabled (caught), Origin compare disabled (caught), `ids[:1]` in /changes (caught), and `if address or time.monotonic() >= deadline` -> `if True` in webapp/instance.py (SURVIVED).

1. A second start that arrives before the first has published its address must wait for it; nothing asserts that | `webapp/instance.py:35`: with the wait loop's exit forced to `if True`, all of tests/test_run.py, test_api_review_queue.py, test_history_ids.py and test_database_upgrade.py still pass. A test would have to hold the lock with an empty lock file, start `claim` with a short `wait`, publish after a delay, and assert the address is returned (and, with no publish, that it returns None at the deadline) | blocking-instance-wait-loop-untested | open
2. A stale address can be returned while the first server is still starting | the lock file is opened `a+` and only truncated in `publish`, so a crashed earlier run leaves its old address in the file; a new first server holding the lock but not yet published makes a second start read that dead address and open it in the browser | `webapp/instance.py:24-40` | open
3. `/changes` now goes through `monitor.history`, which only folds per snapshot check; a move with no snapshot yields `registry_updated` None where the old code did the same, so no regression found. The queue's `moves` can hold one ID where `/changes` holds two (value reviewed, qualifier not); acceptable, but ticket 04 should review by the queue's IDs | `monitor.py:1195-1200` | left: consistent with "reviewed only if all are"
4. JS changes (`when`, sidebar, queue wording) were not run in a browser and no walk covers them; the spec wording for the sidebar and zone is unverified | `webapp/static/api.js:13-21` | left: no walk tooling in this repo yet (repo.md)
5. Finding 7: repo.md Stand-ins table now has both rows, and the `make_server` docstring matches the code | `docs/agents/local/repo.md` | left: holds
6. Finding 5: the lock is taken in `_dispatch` around the handler; checked in the diff, and no handler lock remains | `webapp/server.py:92` | left: holds
7. Finding 10: wording matches the quoted story text; lowercase `nct` route now reaches `trial_not_found` (route regex only; no test run by me for it) | `webapp/routes.py:12` | left: holds
