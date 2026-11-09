# Exploration: summary and export
Scripts: `.scratch/html-front-end/explore/summary-and-export/test_summary_explore.py` (its `conftest.py` re-exports the shared walk fixtures). Run from the repo root:
`.venv/bin/python -m pytest .scratch/html-front-end/explore/summary-and-export/test_summary_explore.py -q`
Screenshots are under `.scratch/html-front-end/walks/` (git-ignored), named `test-<title>-<viewport>-NN-<step>.png`; names given below.
Tests that pass are kept in the file as coverage (marked in Tried); every red test is one defect.

## Tried
- Keyboard: Enter on "This month", "Copy summary", "Custom dates", Cancel, Apply (to an empty period): where focus lands each time. Defect 1.
- Copy summary with a trial expanded and with dates typed in the open Custom form. Defects 2, 3.
- Custom dates open: which period buttons read as pressed. Defect 5.
- Hand-edited / stale address `#/watchlists/1/summary?period=custom&from=abc&to=def`, then reload. Defect 4.
- Hostile data (temporary seed only): trial title `=HYPERLINK("http://evil.example","click")` through Export CSV. Defect 6.
- Hostile data: a 272-character unbroken title and acronym at both viewports (sideways-scroll guard): green.
- Week boundary (seeded changes at 23:59:50 and 00:00:10 either side of Sunday/Monday in the server zone, America/New_York, browser in Tokyo): only the two inside the week appear in the CSV, with the right offsets: green.
- Four hundred changes on one trial: heading count equals CSV rows: green.
- Two quick period clicks with the first response held back (month slow, week fast): ends on "This week": green.
- Server stopped mid-action (own process, by pid) then "This month": page stays, heading kept, notice shown. The walk guards trip on the refused request (see Odd).
- Clipboard write rejected: the notice appears; its advice is wrong. Defect 7.
- Empty period (existing walk covers it); not repeated except focus after reaching it.

## Defects
1. After every action on the Summary tab keyboard focus falls to the page body (the whole tab is redrawn), so a keyboard-only analyst has to Tab from the top of the page after choosing a period, opening or cancelling Custom dates, applying dates, or copying | focus the period button, Enter (same for Copy summary, Custom dates, Cancel, Apply) | red scripts: `test_keyboard_user_keeps_focus_on_the_period_button_they_pressed`, `test_focus_after_copy_summary_stays_on_the_button`, `test_opening_custom_dates_puts_the_keyboard_in_the_form`, `test_cancel_and_apply_leave_the_keyboard_somewhere_sensible`, `test_empty_period_offer_keeps_the_keyboard_on_the_page` | `test-keyboard-user-keeps-focus-on-the-period-button-they-pressed-1440x900-01-after-month.png`, `test-cancel-and-apply-leave-the-keyboard-somewhere-sensible-1440x900-01-after-cancel.png` | wrong but workable (Tab order is intact; it is the same class of defect ticket 15 fixed in the queue)
2. Copy summary collapses every trial the analyst had expanded ("View 2 changes" closes) | expand a trial, press Copy summary | red: `test_copy_summary_does_not_collapse_the_open_trial` | `test-copy-summary-does-not-collapse-the-open-trial-1440x900-01-after-copy.png` | wrong but workable
3. Copy summary wipes dates typed in the open Custom form, and resets them to the week | Custom dates, type a From date, press Copy summary | red: `test_copy_summary_does_not_wipe_dates_typed_in_the_open_form` | `test-copy-summary-does-not-wipe-dates-typed-in-the-open-form-1440x900-01-after-copy-with-form.png` | wrong but workable
4. A summary address with unusable custom dates (`period=custom&from=abc&to=def`, e.g. an old bookmark, or dates the server refuses) shows a bare "Choose both dates, as YYYY-MM-DD." message in place of the whole tab: no tabs, no period buttons. The sidebar still works | open that address | red: `test_a_hand_edited_address_with_bad_custom_dates_still_opens_the_summary` | `test-a-hand-edited-address-with-bad-custom-dates-still-opens-the-summary-1440x900-01-bad-hash.png` | wrong but workable (the client only checks the dates are present, not valid; fall back to this week as it already does when they are missing)
5. With Custom dates open both "This week" and "Custom dates" read as pressed (`aria-pressed="true"` on two buttons of one choice) | click Custom dates | red: `test_custom_dates_pressed_state_is_one_choice_not_two` | `test-custom-dates-pressed-state-is-one-choice-not-two-1440x900-01-custom-open.png` | cosmetic (a screen reader hears two selected periods)
6. The CSV writes a title that begins with `=` (also `+`, `-`, `@`) as is, so a spreadsheet opens it as a formula | seed a trial whose registry title is `=HYPERLINK("http://evil.example","click")`, Export CSV | red: `test_csv_cell_that_begins_with_equals_is_not_left_as_a_spreadsheet_formula` | `test-csv-cell-that-begins-with-equals-is-not-left-as-a-spreadsheet-formula-1440x900-01-formula-title.png` (the page) | wrong but workable (registry text is third-party; the file goes straight into a briefing spreadsheet). The same applies to Watchlist name and the values columns
7. When the browser refuses the clipboard, the notice says "Select it from the export instead", but there is nothing on the page to select and Export is a download | deny clipboard (script overrides `navigator.clipboard.writeText` to reject), press Copy summary | red: `test_copy_refused_by_the_browser_gives_a_way_forward` | `test-copy-refused-by-the-browser-gives-a-way-forward-1440x900-01-copy-refused.png` | wrong but workable (the analyst has no way to get the text; Export CSV is the only route)

## Odd, not wrong
- The week and month are the server machine's, not the browser's: with the browser in Tokyo and the server in New York the heading and "Dates use EST" follow the server. Spec 100a says "machine's local zone", which is the server here, so consistent.
- Pressing a period button waits for the reply before changing; with a slow reply nothing shows that anything is happening. The page ends in the right place when responses arrive out of order.
- "Show the whole month" on an empty week, then an empty month, offers "Pick other dates": fine.
- After the server stops, the guards trip on `ERR_CONNECTION_REFUSED` and the console error; `walk.expect` takes a status, so a walk cannot declare a refused connection. See Not checked.
- Every Summary redraw rebuilds the cards, so the trial heading links lose any hover/scroll position inside the list.

## Not checked
- A watchlist with no trials (spec 92 hides the tab; the shell walks cover it).
- A summary left open across a restart and a later change (the page does not refresh until a period is chosen; not judged against any box).
- Helper request: a way to declare an expected failed connection (server stopped on purpose) so a server-gone walk can be written green. I did not change the helper.
- WebKit, Safari clipboard permission prompts, real downloads folder behaviour.
- A watchlist name that makes an empty slug (non-ASCII only) falls back to `watchlist` in the filename (read in code, not driven).
