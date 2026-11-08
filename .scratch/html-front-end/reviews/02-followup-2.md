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

## Reviewer (tip ac235c9)
Every closure holds: each red file shows its named check failing at ac59568, and the check asserts on what its finding names. Mutation sample: no `mutate_paths` is configured, so the whole diff is the list, and `gate.py mutate` refused (untracked `.venv`), so I drew by hand. The prompt's hand sample (`_console`, `make_walk` suffix, `exit_code`) was skipped. Lines mutated, 4 tried, 4 caught: `helper.py` `_foreign` (`origin + "/"` to `origin`) caught by the longer-port walk; `_status` expected-branch condition negated, caught by 4 walks; `problems` "expected never came" filter forced empty, caught by the expected-response guard walk; `conftest.py` `Walk.shot`'s `self.guards.measure()` removed, caught by the mid-walk width walk. `git status` shows only the untracked `.venv`.

## Blocking
(none)

## Notes
1. `expect(status, path)` matches on status and path only, not on method, so an expected 404 on a GET also excuses a failing POST to the same path | walks/helper.py `_status` | left: no walk meets it yet; add a method when an error walk needs one
2. Finding 2's red file fails on the message assertion, with all 24 broken walks red at that tip, so it shows the check failing but not specifically the removed `requestfailed` guard; the mutation sample did not target that line, and the reviewed fixed tip's check asserts `/static/aborted.js (net::ERR` and the absence of the foreign-server message, which only the `requestfailed` handler can produce | .scratch/html-front-end/red/02-walks-requestfailed-guard-ac59568.txt | left: the assertion is specific to that guard

## Layout follow-up (queue and sidebar against design-01)
The Needs review queue was a wide table and the sidebar a plain list; both now follow design-01 (cards, "Your watchlists", count badges, footnote). Walks assert the new structure.
1. The queue was a wide table with Phase, Sponsor and Status columns | webapp/static/views/needs_review.js | fixed — walk: test_walk_a_queue_entry_is_a_narrow_card_and_labels_simulated_changes — red: .scratch/html-front-end/red/02-walks-4476f24.txt
2. The sidebar lacked its heading, per-entry badge and footnote | webapp/static/app.js | fixed — walk: test_walk_sidebar_lists_every_watchlist_with_counts_and_a_long_name_wraps — red: .scratch/html-front-end/red/02-walks-4476f24.txt
