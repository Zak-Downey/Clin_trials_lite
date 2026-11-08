# Follow-up: ticket 02 walk-tooling read (02-foundation.md)
Tip reviewed: ac59568

## Blocking
1. The walk runner reports green when a walk errors in setup and another flakes | walks/run_walks.py | fixed — walk: test_runner_lists_a_walk_that_erred_in_setup_as_well_as_one_that_failed — red: .scratch/html-front-end/red/02-walks-ac59568.txt
2. The requestfailed guard has never been seen red | walks/helper.py | fixed — walk: test_walk_guard_fails_a_walk_on_a_request_to_the_app_that_gets_no_answer — red: .scratch/html-front-end/red/02-walks-requestfailed-guard-ac59568.txt

## Design
3. A walk cannot declare a response it expects | walks/helper.py | fixed — walk: test_walk_a_stale_watchlist_address_shows_not_found_and_the_walk_expects_the_404 — red: .scratch/html-front-end/red/02-walks-ac59568.txt

## Sweep
4. The sideways guard measures once, at the end, and only the document | walks/helper.py | fixed — walk: test_walk_guard_fails_a_walk_that_was_wide_only_at_a_screenshot_or_in_a_region — red: .scratch/html-front-end/red/02-walks-ac59568.txt
5. A second page loses the first page's guards | walks/conftest.py | fixed — walk: test_walk_guard_keeps_the_first_of_two_pages_and_a_closed_pages_findings — red: .scratch/html-front-end/red/02-walks-ac59568.txt
6. walks/serve.py has no stand-ins row | docs/agents/local/repo.md | fixed — doc: docs/agents/local/repo.md#Stand-ins
7. The fidelity row reads as covering search | docs/agents/local/repo.md | fixed — doc: docs/agents/local/repo.md#Stand-ins

## Nit
8. Origin matched by string prefix | walks/helper.py | fixed — walk: test_walk_guard_does_not_take_a_longer_port_for_the_apps_own_origin — red: .scratch/html-front-end/red/02-walks-ac59568.txt
9. A closed page drops the guards' findings | walks/conftest.py | fixed — walk: test_walk_guard_keeps_the_first_of_two_pages_and_a_closed_pages_findings — red: .scratch/html-front-end/red/02-walks-ac59568.txt
