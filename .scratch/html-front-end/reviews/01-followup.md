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
