# 09: New watchlist, Add by NCT ID, and the first-use screen

**Blocked by:** 08

**Status:** ready-for-agent

**Touches:** storage.py, monitor.py, webapp/static/app.js, webapp/static/style.css, webapp/routes.py

**Spec sections (read these, not this ticket's paraphrase):** User Stories 5, 66, 69–71, 91, 92, 94, 97; Implementation Decisions › Domain changes ("Look up a trial without adding it", "Distinct error kinds"); Design coverage 8/3, 8/F, 11/*.

**What to build:** Three small flows that share a destination. The New watchlist dialog, from the sidebar and from inside every destination picker, checks empty and duplicate names inline and returns the analyst to their task with the new watchlist selected. The Add by NCT ID tab looks a trial up and shows it before Add to watchlist, with distinct messages for each failure. An empty watchlist shows only "Monitor your first trial" with Find trials and Add by NCT ID, each carrying the watchlist as destination. This ticket also builds the shared dialog behaviour every later dialog uses.

- [x] Walk: "+ New watchlist" in the sidebar and "New watchlist" inside the Add to picker each open the dialog; an empty or duplicate name is refused inline; Create returns to the task with the new watchlist selected as destination (design 8/3) — walk: test_walk_new_watchlist_from_the_sidebar_and_the_picker_validates_inline_and_selects_the_new_destination; red: .scratch/html-front-end/red/09-walks-ba89d75-sidebar.txt
- [x] Walk: every dialog traps focus, Escape cancels without changes and returns focus to the control that opened it, and saving or cancelling leaves the page on the same view and scroll position (design 8/F) — walk: test_walk_every_dialog_traps_focus_and_escape_cancels_and_returns_to_the_opener_in_place; red: .scratch/html-front-end/red/09-walks-ba89d75-sidebar.txt
- [x] Walk: Add by NCT ID names its destination; "Look up trial" shows the ID, title, sponsor and status with "Add to watchlist"; nothing is added before that button (design 11/3) — walk: test_walk_add_by_nct_id_names_its_destination_and_shows_the_trial_before_adding_it; red: .scratch/html-front-end/red/09-walks-ba89d75-addbutton.txt
- [x] Test: looking up a trial returns its ID, heading, official title, sponsor and status without adding it, and the four failures are distinct error kinds: invalid format, not found, already in this watchlist, registry unavailable — test: test_looking_up_a_trial_returns_its_facts_and_adds_nothing; test: test_the_four_lookup_failures_are_distinct_error_kinds; red: .scratch/html-front-end/red/09-unit-89b111f.txt
- [x] Walk: each of the four failures shows its own message in place, keeps the typed ID and focuses the input; the invalid-format message explains "NCT followed by 8 digits" (design 11/4) — walk: test_walk_each_lookup_failure_shows_its_own_message_in_place_keeps_the_id_and_focuses_the_input; red: .scratch/html-front-end/red/09-walks-ba89d75-addbutton.txt
- [x] Walk: an empty watchlist shows only "Monitor your first trial", the baseline explanation and "You choose when to check for updates", with no summary, activity or check controls (design 11/1) — walk: test_walk_an_empty_watchlist_shows_only_the_first_trial_screen_and_its_buttons_carry_the_destination; red: .scratch/html-front-end/red/09-walks-ba89d75-firstuse.txt
- [x] Walk: its "Find trials" and "Add by NCT ID" buttons open those tabs with this watchlist as destination (design 11/2) — walk: test_walk_an_empty_watchlist_shows_only_the_first_trial_screen_and_its_buttons_carry_the_destination; red: .scratch/html-front-end/red/09-walks-ba89d75-firstuse.txt
- [x] Walk: the first trial added to a watchlist takes its baseline and does not appear in Needs review (design 11/F) — walk: test_walk_the_first_trial_added_takes_its_baseline_and_is_not_in_needs_review; red: .scratch/html-front-end/red/09-walks-ba89d75-firstuse.txt

## Comments
