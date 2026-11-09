# 15: Acceptance walk: the whole journey, keyboard only

**Blocked by:** 14

**Status:** done

**Touches:** walks/

**Kind:** acceptance-walk

**Spec sections (read these, not this ticket's paraphrase):** End State 4; Testing Decisions › Seam 2, › The stand-in registry.

**What to build:** One end-to-end walk across the whole spec, keyboard only, at 1440 × 900 and 1024 × 768 in Chromium and at 1440 × 900 in WebKit, on an empty database against the stand-in registry. The only step not taken through the page is the stand-in's revise and register switch.

- [x] Walk: keyboard only, from an empty database: create a watchlist; search; select across two pages; add trials; save the search; check for updates; stand-in revise and register; check for updates again; open the changed trial; review it; undo; review again; add the new match; dismiss one match and restore it; view the summary; copy it; export the CSV — walk: test_walk_the_whole_journey_by_keyboard_alone; red: .scratch/html-front-end/red/15-walks-4ac0d37-unfixed-app.txt; red: .scratch/html-front-end/red/15-walks-4ac0d37-focus-ring-broken.txt
- [x] The walk passes at 1440 × 900 and 1024 × 768 in Chromium — walk: test_walk_the_whole_journey_by_keyboard_alone; red: .scratch/html-front-end/red/15-walks-4ac0d37-unfixed-app.txt; red: .scratch/html-front-end/red/15-walks-4ac0d37-focus-ring-broken.txt
- [x] The walk passes at 1440 × 900 in WebKit — walk: test_walk_the_whole_journey_by_keyboard_alone; red: .scratch/html-front-end/red/15-walks-4ac0d37-unfixed-app.txt; red: .scratch/html-front-end/red/15-walks-4ac0d37-focus-ring-broken.txt
- [x] No console error, failed request or horizontal scroll occurs at any step — walk: test_walk_the_whole_journey_by_keyboard_alone; red: .scratch/html-front-end/red/15-walks-4ac0d37-unfixed-app.txt; red: .scratch/html-front-end/red/15-walks-4ac0d37-focus-ring-broken.txt
- [x] Walk: every control reached in the journey is a real control with a visible focus ring and a text label, and no state on the way (selected, reviewed, failed) is shown by colour alone (design 14/4) — walk: test_walk_every_stop_in_every_view_is_a_real_labelled_control_with_a_focus_ring_and_states_are_not_colour_alone; walk: test_walk_a_failed_trial_in_a_check_is_named_in_words_and_its_retry_is_reachable_by_keyboard; walk: test_walk_the_whole_journey_by_keyboard_alone; red: .scratch/html-front-end/red/15-walks-4ac0d37-unfixed-app.txt; red: .scratch/html-front-end/red/15-walks-4ac0d37-focus-ring-broken.txt

## Comments
- Notes: the fixed defects: Mark reviewed disabled the focused button so focus fell to the page (WebKit then could not Tab on), fixed by moving focus to Undo and back to Mark reviewed; the sidebar's current watchlist was shown by background colour alone, now aria-current plus a left bar. WebKit reaches links and buttons with Option+Tab, as Safari does by default. Plain Tab there skips them.

