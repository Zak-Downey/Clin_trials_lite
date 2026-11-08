# 05: Trial page: details, history and watchlist membership

**Blocked by:** 04

**Status:** done

**Touches:** storage.py, monitor.py, webapp/static/app.js, webapp/static/style.css, webapp/routes.py

**Spec sections (read these, not this ticket's paraphrase):** User Stories 43–51, 98; Implementation Decisions › Domain changes ("Retention", "The trial heading", "Trial details"); Design coverage 4/3, 4/4, 5/*.

**What to build:** The rest of the trial page. The header uses the acronym, else the brief title, and shows the last successful check with a warning when the latest check failed. Trial details: an At a glance panel and the five sections, expandable, with "Not reported" for missing values. History: one newest-first timeline of detections, reviews and undone reviews, the start of monitoring and any unmonitored gap, each check expandable to every transition. The ⋯ menu shows the watchlists holding the trial and Remove from this list, with Undo. Removing a trial from its last watchlist keeps its history; adding it back resumes it.

- [x] Walk: the heading is the registry acronym when there is one, else the brief title; the full official title and every identifier appear under Identity, untruncated (design 5/2) — walk: test_walk_the_heading_is_the_acronym_else_the_brief_title_and_identity_is_untruncated; red: .scratch/html-front-end/red/05-walks-2b49bfe.txt
- [x] Walk: the header shows "Last checked <time>", and a trial whose latest check failed shows a labelled warning beside it — walk: test_walk_the_header_shows_last_checked_and_a_failed_check_carries_a_labelled_warning; red: .scratch/html-front-end/red/05-walks-2b49bfe.txt
- [x] Walk: At a glance shows registry status, phase, lead sponsor, enrolment, the ClinicalTrials.gov link and when monitoring began (design 5/1) — walk: test_walk_at_a_glance_shows_status_phase_sponsor_enrolment_link_and_when_monitoring_began; red: .scratch/html-front-end/red/05-walks-2b49bfe.txt
- [x] Walk: Trial details shows Identity & study design, Conditions & eligibility, Interventions & arms, Endpoints, and Dates & results; long sections expand on demand; a section holding a field with an unreviewed change is never collapsed (design 5/3) — walk: test_walk_trial_details_has_five_sections_long_ones_expand_and_an_unreviewed_field_is_never_collapsed; red: .scratch/html-front-end/red/05-walks-2b49bfe.txt
- [x] Test: every field of the eight existing information groups lands in exactly one of the five sections or At a glance; walk: a field the registry omits shows "Not reported" (design 5/F) — test: test_every_field_of_the_eight_groups_lands_in_exactly_one_section_or_at_a_glance; walk: test_walk_a_field_the_registry_omits_shows_not_reported; red: .scratch/html-front-end/red/05-walks-2b49bfe.txt; red: .scratch/html-front-end/red/05-unit-e6f6d7c.txt
- [x] Walk: History lists detections, reviews ("Marked N changes from the HH:MM check as reviewed"), undone reviews and the start of monitoring newest first, and expanding a check shows every previous-to-new transition, reviewed ones included (design 4/3, 4/4) — walk: test_walk_history_is_newest_first_with_detections_reviews_undos_and_start_and_expands_every_transition; red: .scratch/html-front-end/red/05-walks-2b49bfe.txt
- [x] Test: removing a trial from its last watchlist keeps the trial, its snapshots and its changes, and no check fetches it; adding it back resumes without a new baseline and the next check reports what moved meanwhile — test: test_removing_a_trial_from_its_last_watchlist_keeps_it_and_no_check_fetches_it_and_adding_it_back_resumes; red: .scratch/html-front-end/red/05-unit-e6f6d7c.txt
- [x] Walk: History shows a period when the trial was not monitored as "Stopped monitoring" and "Resumed monitoring" (design 4/3) — walk: test_walk_history_shows_a_period_when_the_trial_was_not_monitored; red: .scratch/html-front-end/red/05-walks-2b49bfe.txt
- [x] Walk: the ⋯ menu lists the watchlists holding the trial and "Remove from this list"; removing offers Undo, which restores the membership; removing touches no other watchlist (design 5/4, 13/3) — walk: test_walk_the_menu_lists_the_watchlists_and_removing_offers_undo_and_touches_no_other_list; red: .scratch/html-front-end/red/05-walks-2b49bfe.txt

## Comments
