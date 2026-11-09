# Exploration: saved search and new matches
## Tried
- Focus after Dismiss, Undo, Add, View dismissed, Back, Restore (keyboard Enter on Undo), Escape from the Watch dialog, Turn off, Check for new matches
- Dismiss every match (empty tab, count 0), then Undo
- Undo of a dismissal after the trial was added by another request: not re-offered (fine)
- A second window left open: add in one, dismiss the same trial in the other; restore then add
- Server stopped before Undo, before Watch save, before Turn off
- Undo after the watchlist was deleted in another window
- Turn off the saved search: banner goes, New matches keeps its offers
- Odd query (markup characters, quotes, accents, CJK, emoji, %20, #, ?, 150-letter word): Find, Watch dialog, Manage, Edit search round trip (exact), double-click on save
- Find with no filters: no Watch this search button offered
- Check for new matches on an empty watchlist with registry server error, register switch, plain, slow (button disables)
## Defects
1. After Dismiss, Undo and Add on New matches, and after Turn off closes Manage, keyboard focus is on the page body, so a keyboard user restarts from the top (ticket 15 fixed this for Mark reviewed) | steps: select a match, Dismiss 1, Yes dismiss, look at focus; same after Undo, Add 1; open Manage, Turn off | red script: .scratch/html-front-end/explore/saved-search-and-new-matches/test_explore_saved_search_new_matches.py, test_focus_stays_in_the_page_after_dismiss_undo_and_add and test_focus_returns_after_turn_off_closes_the_dialog | .scratch/html-front-end/walks/test-focus-stays-in-the-page-after-dismiss-undo-and-add-1440x900-final.png | wrong but workable
2. Undo (and Restore, which has the same code) has no error handling: if the server refuses it (watchlist deleted in another window) nothing is shown, the button stays disabled forever, and a page error is logged | steps: dismiss a match, delete the watchlist in another window, press Undo | red script: .scratch/html-front-end/explore/saved-search-and-new-matches/test_explore_saved_search_new_matches.py, test_undo_that_the_server_refuses_says_so_and_can_be_pressed_again | .scratch/html-front-end/walks/test-undo-that-the-server-refuses-says-so-and-can-be-pressed-again-1440x900-02-undo-refused.png | wrong but workable
3. Dismissing a match that another window already added says "0 trials dismissed. These trials will not be suggested again for this list." with an Undo | steps: two windows on New matches; add the trial in one, dismiss it in the other | red script: .scratch/html-front-end/explore/saved-search-and-new-matches/test_explore_saved_search_new_matches.py, test_dismissing_a_match_already_added_elsewhere_does_not_claim_it_was_dismissed | .scratch/html-front-end/walks/test-dismissing-a-match-already-added-elsewhere-does-not-claim-it-was-dismissed-1440x900-01-stale-dismiss.png | wrong but workable
4. A long unbroken word in the condition makes Find trials results 189px (1440) or 605px (1024) wider than the window; Watch this search and Edit search are pushed off the right edge | steps: Find trials, condition of 150 letters, Search | red script: .scratch/html-front-end/explore/saved-search-and-new-matches/test_explore_saved_search_new_matches.py, test_a_long_unbroken_condition_keeps_find_trials_inside_the_window | .scratch/html-front-end/walks/test-a-long-unbroken-condition-keeps-find-trials-inside-the-window-1024x768-01-long-condition.png | wrong but workable (the Find area may own the fix)
5. The Watch this search dialog draws an empty orange 24px strip above Cancel when the watchlist has no saved search | steps: Find, search, Watch this search | red script: .scratch/html-front-end/explore/saved-search-and-new-matches/test_explore_saved_search_new_matches.py, test_the_watch_dialog_shows_no_empty_warning_strip_for_a_watchlist_without_a_saved_search | .scratch/html-front-end/walks/test-the-watch-dialog-shows-no-empty-warning-strip-for-a-watchlist-without-a-saved-search-1440x900-01-empty-strip.png | cosmetic
## Odd, not wrong
- Turn off keeps the old offers in New matches and the tab count (it says "Not monitored yet. Select the trials you want to add."); replacing a saved search likewise leaves matches of the old query offered. Not specified either way.
- A failed save or Turn off shows the browser's raw "Failed to fetch" in the dialog.
- After a check finishes on an empty watchlist, focus is on the body (the Check button is replaced); the check area is another walker's.
- The sidebar still lists a watchlist deleted in another window until it redraws.
- Going to a trial and back from New matches drops the selection.
- Find with no filters offers no Watch this search (no explanation shown).
## Not checked
- Stale page across a server restart; data written by an earlier version
- Hundreds of offered matches beyond the cap of 100 with distinct titles (stand-in has one title)
- Registry failure while adding from New matches; WebKit; screen-reader wording
- Replace saved search when matches were already offered, beyond the odd note above
