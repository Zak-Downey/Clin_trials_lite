# 10: The acceptance walk measures every step and checks every stop

**Blocked by:** 01, 02, 03, 04, 05, 06, 07, 08, 09

**Status:** ready-for-agent

**Touches:** walks/test_acceptance_walk.py

**Kind:** acceptance-walk

**Spec sections (read these, not this ticket's paraphrase):** Findings › F16, F17. Root: End State 4; ticket 15's boxes 18 and 19.

**What to build:** The acceptance journey, run once more over the fixed branch, keyboard only, at 1440 x 900 and 1024 x 768 in Chromium and 1440 x 900 in WebKit, with `Keys.focus` measuring sideways scroll on every keyboard move and checking every Tab stop it passes (a real control, a name, a visible ring), not only its target.

- [x] Walk: the acceptance journey measures horizontal scroll on every keyboard move, and fails when the New watchlist dialog alone is made wider than the viewport — walk: test_walk_the_acceptance_journey_measures_horizontal_scroll_on_every_keyboard_move_and_fails_on_a_wide_new_watchlist_dialog; red: .scratch/pr-1-review/red/10-walks-cad0273.txt
- [x] Walk: the acceptance journey checks every Tab stop it passes, and fails when a control passed on the way (not aimed at) loses its accessible name — walk: test_walk_the_acceptance_journey_checks_every_tab_stop_it_passes_and_fails_when_a_control_passed_on_the_way_loses_its_name; red: .scratch/pr-1-review/red/10-walks-cad0273.txt
- [x] Walk: the acceptance journey passes at both Chromium viewports and in WebKit at 1440 x 900 after tickets 02 to 09 (the walks check) — walk: test_walk_the_whole_journey_by_keyboard_alone; check: walks

## Comments
