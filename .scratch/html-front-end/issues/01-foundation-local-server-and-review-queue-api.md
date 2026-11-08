# 01: Foundation: the local server, its API seam and the Needs review queue

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

**Touches:** *

**Kind:** foundational

**Spec sections (read these, not this ticket's paraphrase):** Solution; Implementation Decisions › Shape, › Domain changes ("Changes carry their IDs to callers", "An existing database file is upgraded in place"), › API; Testing Decisions › Seam 1; Further Notes (the foundational ticket).

**What to build:** The skeleton every other ticket builds on. One command starts a standard-library HTTP server bound to localhost and opens the browser on a static HTML page (no build step, no framework, no CDN). The page shell has the two top-level destinations and a sidebar of watchlists with counts; a watchlist opens on a read-only Needs review queue served by the JSON API. The server is made by a factory taking the database path and the registry fetch and search functions, so the API is tested in-process against a temporary database with the suite's existing stub fetchers and finders. Changes now reach callers with their IDs and check identity. Code layout set here and kept by every later ticket: a `webapp` package (server and factory, a route table, one API module per area), static files under it (shell and router, one stylesheet with colours as custom properties, one view module per screen), `run.py` at the root, API tests as `tests/test_api_*.py`.

- [x] `python run.py` starts the server on 127.0.0.1 only, on a free port unless one is given, prints the address and opens the browser; the database is `MONITOR_DB` if set, else `monitor.db` in the start folder (Implementation Decisions › Shape) — test: test_run_py_serves_the_page_on_localhost_only_and_prints_the_address; test: test_the_database_is_monitor_db_in_the_start_folder_unless_monitor_db_is_set; test: test_the_server_refuses_to_bind_beyond_the_local_machine; red: .scratch/html-front-end/red/01-unit-9fe8a3d.txt
- [x] The server factory takes the database path and the registry fetch and search functions; an API test runs it in-process against a temporary database with the stub fetchers and finders from the test fixtures, and no test reaches the live registry — test: test_a_queue_entry_carries_what_the_row_shows; red: .scratch/html-front-end/red/01-unit-9fe8a3d.txt
- [x] Every API error response carries a stable `kind` and a human-readable message — test: test_an_unknown_address_answers_with_a_stable_kind_and_a_message; test: test_an_unknown_watchlist_answers_with_its_own_kind; test: test_a_known_address_with_the_wrong_method_says_so; red: .scratch/html-front-end/red/01-unit-9fe8a3d.txt; red: .scratch/html-front-end/red/01-unit-b432a87.txt
- [x] A `monitor.db` written by the current app opens with its data intact and its schema upgraded in place — test: test_an_older_database_opens_with_its_data_and_an_upgraded_schema; red: .scratch/html-front-end/red/01-unit-9fe8a3d.txt
- [x] Listing a trial's changes returns each change's ID, its check (the shared detection time of one check of one trial), previous and new values, registry-updated date, detected time, review state and simulated flag — test: test_listing_a_trials_changes_carries_ids_check_and_review_state; test: test_history_moves_carry_the_change_id_and_the_check; red: .scratch/html-front-end/red/01-unit-9fe8a3d.txt
- [x] The watchlists endpoint returns each watchlist with its trial count, the number of its trials needing review, its last-checked time and whether a saved search is on (design 1/1) — test: test_watchlists_carry_counts_last_checked_and_saved_search_flag; red: .scratch/html-front-end/red/01-unit-9fe8a3d.txt
- [x] The Needs review endpoint returns only the watchlist's trials with unreviewed changes, newest detection first, with the counts of trials and of unreviewed field changes as separate numbers (design 1/2) — test: test_needs_review_holds_only_unreviewed_trials_newest_detection_first; red: .scratch/html-front-end/red/01-unit-9fe8a3d.txt
- [x] Each queue entry carries the trial heading (acronym, else brief title), NCT ID, phase, sponsor, registry status, the names of the changed fields, the detected time, its change count and whether any change is simulated (design 1/F) — test: test_a_queue_entry_carries_what_the_row_shows; red: .scratch/html-front-end/red/01-unit-9fe8a3d.txt
- [x] Times the API returns are in the machine's local time zone, with the zone named — test: test_times_are_in_the_machines_zone_with_the_zone_named; test: test_a_stamp_without_an_offset_is_read_as_utc; red: .scratch/html-front-end/red/01-unit-9fe8a3d.txt; red: .scratch/html-front-end/red/01-unit-b432a87.txt
- [ ] The page shell, sidebar and Needs review queue render from the API; their visible behaviour is proven by the walk in ticket 02 — test: test_the_shell_and_its_assets_are_served_and_nothing_outside_static_is; needs-human: no browser walk exists yet; the rendering is proven by ticket 02's walk

## Comments
