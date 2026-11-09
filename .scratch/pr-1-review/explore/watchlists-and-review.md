# Exploration: watchlists and review

Branch `ticket/11-exploration-over-what-the-fixes-changed--watchlists-and-review`, tip before this commit `5a1f34a`. Scripts: `.scratch/pr-1-review/explore/watchlists-and-review/`. Run one with
`WALK_FEATURE=pr-1-review .venv/bin/python -m pytest <file> -q -p walks.conftest --rootdir .`
Screenshots land in `.scratch/pr-1-review/walks/<test title>-<viewport>-NN-<step>.png` (git-ignored); the paths below give the title part. Every script is red at both viewports; each was shown red for the stated reason (defect 1 also has a control run that is green when the late answer is not held).

## Tried
- F3: filter and sort typed in All trials, then a check finishes: value kept, typing continues in the same field (green).
- F3: scroll position on All trials, New matches and Summary when a check finishes (88-trial list): kept (green).
- F3: Summary custom dates typed, check finishes, period in the address kept; leave Summary and return: the form and typed dates are still there (see Odd).
- F3: New matches ticks, pending "Yes, dismiss", dismissed sub-view kept across a finishing check, across a tab change, across a switch to another watchlist and back (kept; see Odd).
- F3: New matches checkbox focused when a check finishes: tick and bar kept.
- F4: delayed trial and tab answers are covered by existing walks; tried instead the late check refresh drawing New matches after leaving it (defect 1), and two sidebar answers in the wrong order (defect 4).
- F5: Rename from the header menu with a hostile name (`Q<b>x</b> & "odd" 😀`) while on `summary?period=month`: mark and `aria-current` kept, name shown as text, focus back on the menu button.
- F5: New watchlist with a 400-character name and Enter pressed twice: one list made, mark kept, no sideways scroll, no second dialog.
- F5: 62 watchlists with names of different lengths: the last one opens and is marked (see Odd for the length of the page).
- F6: progress poll returns 500 mid-check: status states it, button usable (aria-disabled false); the check keeps running on the server and the header stays "Not checked yet" until the analyst acts; pressing Check again resumes the running check.
- F6: server killed mid-check: status "The check's progress could not be read: Failed to fetch", button usable; switching list then shows only "Failed to fetch".
- F6: server killed mid-check and restarted on the same database: no stuck "running" state, the button works, a fresh check completes.
- F6/F7: failed trial, Show details, Retry failed (double Enter): the second press gets 409 and the running check is shown; details lists the failing trial.
- F7: adding a match from New matches to a watchlist with a saved search and no trials: header count and button label update (existing walk); tried the add by keyboard: header "2 trials monitored".
- Two checks at once (list 1 running, check started on list 2), switching lists and browser Back/Forward while one runs: each list shows its own status, progress resumes.
- Keyboard: Check for updates (defect 2); Summary period buttons, Custom dates open, Cancel, Apply with a bad range, Apply; New matches select, Dismiss, Yes dismiss, Undo, View dismissed, Restore, Back, Add (defects 2 and 3, and Odd).
- Summary custom boundaries: one day, 1900, 9999-12-31, today, From after To: all state their period or a refusal. Hand-edited addresses (garbage dates, 13th month, 0000-01-01, From without To, markup in `period`): see Odd.
- Mark reviewed pressed twice with Enter (second press lands on Undo, as intended) and double-clicked (defect 5).
- Both viewports (1440 x 900 and 1024 x 768) for every script.

## Defects
1. Open Find trials after leaving a New matches tab, and a check that was started there finishes late: "View details" then offers "Add to Myeloma" (the New matches watchlist) instead of the Find trials destination "Quiet", and the origin set by Find trials is replaced. | Myeloma, New matches; press Check for updates; before it finishes go to `#/find/2` and search "many"; the check finishes (its sidebar re-read is slow); View details on a result. `app.js` `refresh` draws New matches after `await drawSidebar` without asking `alive()`, and `new_matches.js` `render` calls `setOrigin` on entry, overwriting Find's origin. Adding then puts the trial in the wrong list. | red script: `test_explore_wr_check_refresh_clobbers_trial_origin.py`, `test_walk_a_check_finishing_after_leaving_new_matches_does_not_change_where_find_trials_details_came_from` | `...a-check-finishing-after-leaving-new-matches-...-01-details.png` | wrong but workable (the picker shows the wrong list; a user who does not look adds to the wrong list; needs a slow sidebar answer to meet)
2. Pressing Enter on "Check for updates" moves keyboard focus to "Add trials" at once and it stays there when the check ends. A second Enter (the natural "did it start?") opens Find trials and leaves the page; Tab is needed to get back to the button. Cause: `focus.js` counts an `aria-disabled` button as unusable and moves to the neighbour; `check.js` chose `aria-disabled` to keep focus. Same on Needs review, All trials and Summary. The existing walk only asserts focus is not on the page body. | Needs review, focus Check for updates, Enter, wait. | red script: `test_explore_wr_check_for_updates_gives_up_keyboard_focus.py`, `test_walk_check_for_updates_keeps_keyboard_focus_while_it_runs_and_after` | `...check-for-updates-keeps-keyboard-focus-while-it-runs-and-after-1440x900-01-running.png` | wrong but workable
3. On New matches, View dismissed and Back to new matches leave focus on the "Summary" tab. Enter or Space then leaves the list. | New matches, focus View dismissed, Enter (then focus Back to new matches, Enter). | red script: `test_explore_wr_view_dismissed_parks_focus_on_the_summary_tab.py`, `test_walk_view_dismissed_and_back_to_new_matches_do_not_leave_focus_on_a_tab` | `...view-dismissed-and-back-to-new-matches-do-not-leave-focus-on-a-tab-1440x900-01-view-dismissed.png` | wrong but workable
4. Two quick review changes (Mark reviewed then Undo) whose sidebar answers arrive out of order leave the sidebar badges stale: "1" instead of "2" for the open list, until the next change. The `reviewchange` redraw (`app.js:81`, `drawSidebar`) has no ordering guard. The same shape exists in `check.js` `onChange` for the header (not scripted). | Trial page, Mark reviewed (its re-read is held), Undo, release the held answer. | red script: `test_explore_wr_an_older_sidebar_answer_overwrites_a_newer_one.py`, `test_walk_a_late_older_sidebar_answer_does_not_overwrite_the_newer_badges` | `...a-late-older-sidebar-answer-does-not-overwrite-the-newer-badges-1440x900-01-after-late-answer.png` | wrong but workable (needs a slow network)
5. A double click on Mark reviewed sends two review requests. The second finds nothing to review and answers with no event; the page then shows an Undo whose click prints "Cannot read properties of null (reading 'id')" in the page, and the trial stays reviewed. The review cannot be undone from the page. `trial.js` mark handler: no guard while the request is in flight. | `#/trials/NCT00000002`, double-click Mark reviewed, click Undo. | red script: `test_explore_wr_double_click_mark_reviewed_leaves_an_undo_that_fails.py`, `test_walk_undo_after_a_double_click_on_mark_reviewed_still_undoes_the_review` | `...undo-after-a-double-click-on-mark-reviewed-still-undoes-the-review-1440x900-01-after-undo.png` | wrong but workable (a review is recorded, the Undo is lost; a script error is shown to the analyst)

Items 1 and 4 need a change under `webapp/static/` (app.js, new_matches.js, focus.js, trial.js, check.js): by the ticket these are `Kind: design` tickets with Open list items.

## Odd, not wrong
- The per-watchlist memory outlives the visit: leave New matches with a pending "Yes, dismiss 1" or ticks and come back (even via another watchlist): the confirmation is still waiting. Same for Summary's open Custom dates form with typed dates (while the period itself resets to This week). Reload clears both. Spec F3 asks for this; the wording of a stale confirmation is a human call.
- Summary Cancel and Apply put focus on "Export CSV", not on "Custom dates"; an invalid range keeps focus on Apply and states the error. Cosmetic.
- Escape does nothing on the pending dismiss bar (it is not a dialog; Cancel works).
- After Retry failed completes, focus is on the header menu button (⋯), not Check for updates (same cause as defect 2).
- A hand-edited Summary address with bad custom dates (`from=garbage`, a 13th month, `0000-01-01`, From without To) replaces the whole view with one red sentence: no header, tabs or Check button; only the sidebar remains. The app never produces such an address.
- 60+ watchlists: the sidebar is not its own scrolling region; the page is about 7000 px tall and "+ New watchlist" is at the very end (62 Tab stops after the page start).
- A re-press of Check while one runs makes the server answer 409; the browser logs it as a console error (the page handles it). A walk that does this must `walk.expect(409, ...)`.
- A poll that failed leaves "The check's progress could not be read" up after the server finished, with the header still "Not checked yet" and the queue unrefreshed, until the analyst presses Check or leaves; stated, not hidden.

## Not checked
- Stale page left open across a restart on the same address (the walks' servers pick new ports).
- Data written by an earlier version of the app (the repo keeps none the walks can load).
- The header re-read race (`check.js` `onChange`) with answers out of order; Rename and New watchlist under a failing `/api/watchlists`.
- Delete watchlist and Full recheck from the header menu, and the saved-search banner paths.
- A check whose results arrive while the Remove-from-list Undo bar is open on the trial page.
- Safari/WebKit and screen readers; wording of stale confirmations.
- Walk-helper change wanted: none. A helper `walk.hold_then_deliver(pattern)` for the stale-answer scripts would remove the copied `route.fetch()` code in `test_explore_wr_an_older_sidebar_answer_overwrites_a_newer_one.py`.
