# 04: Trial page: read the changes and review them without losing your place

**Blocked by:** 02

**Status:** done

**Touches:** storage.py, monitor.py, webapp/static/app.js, webapp/static/style.css, webapp/routes.py

**Spec sections (read these, not this ticket's paraphrase):** User Stories 31–42; Implementation Decisions › Domain changes ("Review by change ID", "Review events persist"), › API (A trial, Review); Design coverage 3/*, 4/1, 4/2, 4/F.

**What to build:** The trial page with its Changes tab: each unreviewed change as labelled Previously / Now values, registry-updated and detected dates, grouped by check. The action bar states the review's scope, including the other watchlists holding the trial, before the analyst acts. Mark reviewed marks exactly the change IDs shown and records a review event; the page stays put with a Reviewed label and Undo. Next trial moves through the queue. Back returns to the list position. The Trial details and History tabs exist as tabs here; their content is ticket 05.

- [x] Walk: opening a trial from Needs review lands on its Changes tab with Trial details and History one click away, and "Back to <watchlist>" returns to the queue at the same scroll position (design 3/1) — walk: test_walk_a_trial_opens_on_changes_with_the_other_tabs_near_and_back_keeps_the_queue_position; red: .scratch/html-front-end/red/04-walks-a348fc2.txt
- [x] Walk: each change shows the field name with labelled Previously and Now values; a long value (an endpoint or eligibility text) stacks Previously first, Now second, and all text wraps (design 3/2) — walk: test_walk_each_change_has_labelled_previously_and_now_and_a_long_value_stacks_and_wraps; red: .scratch/html-front-end/red/04-walks-a348fc2.txt
- [x] Walk: each check's group shows "Registry updated <date> · Detected <local time>", and a field that moved in two checks shows both transitions (design 3/3) — walk: test_walk_each_check_group_shows_both_dates_and_a_field_that_moved_twice_shows_both_transitions; red: .scratch/html-front-end/red/04-walks-a348fc2.txt
- [x] Walk: the action bar reads "Review covers all N changes shown above", names the other watchlists holding the trial, stays visible while scrolling, and never covers the last change (design 3/4, 4/F) — walk: test_walk_the_action_bar_states_its_scope_stays_visible_and_leaves_the_last_change_clear; red: .scratch/html-front-end/red/04-walks-a348fc2.txt
- [x] Test: marking reviewed takes the change IDs shown and marks exactly those; a change detected after the page loaded stays unreviewed (design 3/F) — test: test_marking_reviewed_marks_exactly_the_ids_sent_and_a_later_change_stays_unreviewed; red: .scratch/html-front-end/red/04-unit-a348fc2.txt
- [x] Test: a review applies to the trial in every watchlist holding it, records its time and change IDs, and undoing it returns exactly those changes to unreviewed and records the undo (design 4/2, 4/F) — test: test_a_review_applies_in_every_watchlist_records_its_time_and_ids_and_undo_returns_exactly_those; red: .scratch/html-front-end/red/04-unit-a348fc2.txt
- [x] Walk: after Mark reviewed the page stays on Changes with each change labelled Reviewed, shows "N changes marked reviewed. This trial stays open." with Undo, the queue and sidebar counts drop in place, and the scroll position does not move (design 4/1, 4/2) — walk: test_walk_marking_reviewed_keeps_the_page_labels_each_change_drops_the_counts_and_holds_the_scroll; red: .scratch/html-front-end/red/04-walks-a348fc2.txt
- [x] Walk: Undo restores the changes to unreviewed and the counts; Undo is gone after leaving the trial or taking another action — walk: test_walk_undo_restores_the_changes_and_counts_and_is_gone_after_leaving; red: .scratch/html-front-end/red/04-walks-a348fc2.txt
- [x] Walk: "Next trial" opens the next trial in Needs review and marks nothing reviewed (design 3/4) — walk: test_walk_next_trial_opens_the_next_in_needs_review_and_marks_nothing; red: .scratch/html-front-end/red/04-walks-a348fc2.txt
- [x] Walk: a trial with simulated changes shows the "Simulated changes" label on its Changes tab, on a database seeded by the simulator before the walk — walk: test_walk_a_trial_with_simulated_changes_carries_the_simulated_label_on_its_changes_tab; red: .scratch/html-front-end/red/04-walks-a348fc2.txt

## Comments
