# Exploration: trial page
Screenshots are written by the red scripts to `.scratch/html-front-end/walks/` (git-ignored), named `<test>-<viewport>-NN-<step>.png`. Run a script: `.venv/bin/python -m pytest -p walks.conftest .scratch/html-front-end/explore/trial-page/<file> -q`.
## Tried
- Double-click Mark reviewed: one review, no error banner (fine).
- Mark reviewed in a second browser tab, then in the first (stale): the first says "5 changes marked reviewed" with nothing marked, no error.
- Mark reviewed, then Remove from this list: the review's Undo is replaced by the removal banner.
- Remove from this list: action bar still shows the removed list's "Also clears..." text; Next trial and Back still work.
- Next trial through all 16 queue entries: every trial visited once; last one disabled with a reason.
- Mark reviewed then Next trial then Back: reviewed trial is gone from the queue.
- Unknown trial NCT on Changes, Details and History: "NCT99999999 is not being monitored." (no 404 on details/history).
- Menu by keyboard: open with Enter, Escape, Tab away, Remove with Enter, Undo with Enter.
- Tab strip by keyboard: Enter on History, ArrowLeft.
- Trial held by 41 watchlists, one a 70-letter word, others long with `<b>"&` and accents, at both viewports.
- Server stopped, then Mark reviewed.
## Defects
1. Escape does not close the actions menu when focus is on the ⋯ button (the normal state after opening it by keyboard or click); only works once focus is inside the menu | focus ⋯, Enter, Escape | red script: `trial-page/test_red_menu_keyboard.py`, test_escape_closes_the_menu_while_focus_is_still_on_its_button | test-escape-closes-the-menu-while-focus-is-still-on-its-button-1440x900-02-after-escape.png | wrong but workable
2. Tabbing out of the open menu leaves it open, covering the page | open menu, Tab x4 | `test_red_menu_keyboard.py`, test_tabbing_out_of_the_open_menu_closes_it | ...-tabbed-away.png | wrong but workable
3. After "Remove from this list" by keyboard, focus falls to the page body (the menu closed under it); keyboard user restarts from the top. (Undo does keep focus.) | ⋯, Enter, Remove, Enter | `test_red_menu_keyboard.py`, test_focus_is_not_dropped_to_the_page_after_remove_from_this_list | ...-removed.png | wrong but workable
4. Choosing a trial tab (Details, History, Changes) by keyboard drops focus to the page body, because the whole view redraws. Same class as the Mark reviewed fix in ticket 15; Next trial likely the same | focus History tab, Enter | `test_red_tab_focus.py`, test_choosing_a_trial_tab_by_keyboard_leaves_focus_in_the_tab_strip | ...-history.png | wrong but workable
5. A trial held by many watchlists makes the sticky review bar and the menu enormous: the bar is 600-800px tall (taller than the screen at 1024 x 768) and its "Also clears..." list buries the changes; the menu is 1100px tall and "Remove from this list" sits below the fold. A 70-letter list name makes the page scroll sideways at 1024 x 768 (Next trial and Mark reviewed are off the right edge, reachable only by scrolling sideways) | seed 41 lists holding the trial; open the trial | `test_red_many_watchlists.py`, test_the_review_bar_stays_small_and_the_page_does_not_scroll_sideways_with_many_long_named_lists | ...-1024x768-01-bar.png, ...-1440x900-02-menu.png | wrong but workable (cosmetic at 1440 x 900)
6. With the server stopped, a failed action shows the browser's raw "Failed to fetch" in the banner, not a sentence saying the app could not be reached | stop server, Mark reviewed | `test_red_server_down.py`, test_a_stopped_server_is_told_in_words_not_failed_to_fetch | ...-down.png | cosmetic
## Odd, not wrong
- Mark reviewed in a stale second tab says "5 changes marked reviewed" though they were already reviewed there; it is idempotent.
- Removing the trial after reviewing it replaces the review's Undo; the review can no longer be undone from the page.
- Next trial is clickable but dead until the needs-review queue fetch returns (a slow answer leaves a button that does nothing).
- Each page render adds another document click listener for the menu (leak, harmless).
## Not checked
- Slow, empty or nonsense registry answers (the trial page reads only its own API); a failed check's warning on a trial that has changes.
- A page left open across a restart, then acted on.
- Trial opened from All trials (opens on Details) beyond the existing walks; Safari and real hardware.
- Helper change needed: a way to declare an expected network failure (server stopped) so the guards do not trip on it; defect 6's script is red from the guard as well as the assertion until then.
