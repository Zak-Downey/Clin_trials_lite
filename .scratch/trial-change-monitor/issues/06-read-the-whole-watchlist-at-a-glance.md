# 06: Read the whole watchlist at a glance

**What to build:** Today the watchlist is a stack of collapsed expanders. Reading one trial means opening it; comparing two means opening both; and the only thing a closed row says about what moved is a count. That is workable for two trials and useless for thirty, which is the size a real medical affairs watchlist reaches.

Replace it with a status table: one line per trial, the whole watchlist on screen at once. Each line carries what identifies the study — NCT ID, lead sponsor, official title, phase, conditions, interventions, recruitment status — followed by what moved and when. An analyst opening the app should be able to answer "what has changed across everything I monitor, and when" without clicking anything. Clicking a row still opens the full profile underneath, with the existing highlighting untouched.

Two columns carry the news:

- **What changed** — the names of the fields that moved the last time this trial changed. Names only: the from-and-to values make one row informative but a column of them unreadable, and they are one click away in the profile below. A single check can move several fields at once, so "the last change" means every field sharing that newest detection time, not just the most recent one. Changes stay listed after they are reviewed — a change does not stop having happened once somebody has read it — so review state is carried by a 🔔 prefix meaning "nobody has read this yet". A simulated change is marked 🧪. The list is capped, with a "+n more" overflow, which is why the names are ordered high-signal first: a slipped completion date must never be the one hidden under the fold.
- **Changed on** — the date that change was detected, with the month spelled out (`05 September 2026`). An all-numeric date has to be decoded before it can be read, and a spelled month cannot be misread as a day. Date only, not time: the stored timestamps record when somebody pressed Check, not when the sponsor edited the record, so a time would be false precision. The cell must still sort chronologically rather than alphabetically.

**Prototype:** branch `prototype/watchlist-table`, file `prototype_watchlist.py`. Four layouts were built against the real database and compared on screen; **variant A (dense grid) won**, and the column set, column order and the two rules above are the decisions that came out of it. The branch is the primary source for why the losing three lost. Do not promote its code: it was written under prototype rules — no tests, no error handling, table construction inline in the page. The derivation of "what changed" and "when" belongs behind the existing seams, so `app.py` stays a thin view.

**Blocked by:** 05

**Status:** ready-for-human

- [x] The watchlist renders as one table with one line per trial, replacing the per-trial expanders
- [x] Each line shows NCT ID, lead sponsor, official title, phase, conditions, interventions and recruitment status, in that order
- [x] Interventions repeated once per arm by the registry appear once
- [x] A "What changed" column lists the field names that moved at the trial's most recent detection time, high-signal fields first, capped with a "+n more" overflow
- [x] Field names remain visible after the trial is marked reviewed; only the unreviewed marker clears
- [x] A trial carrying unreviewed changes is distinguishable from one whose changes have all been reviewed
- [x] A change made by the simulator is marked as synthetic on the row
- [x] A trial that has never changed is unambiguous rather than blank-looking
- [x] A "Changed on" column shows the detection date with the month spelled out, and sorts chronologically
- [x] Sorting by any column, including the two change columns, works from the table header
- [x] Selecting a row opens that trial's full profile below the table, with existing highlighting and the "Mark as reviewed" action intact
- [x] Marking a trial reviewed from the opened profile still clears its highlighting in the same interaction
- [x] "What changed" shows its full cap of field names without truncation at a normal window width; a long interventions list truncates before it does
- [x] The walkable loop still runs end to end: add a trial, check, simulate a change, check, read what moved from the table alone, open the row, review it
- [x] Tests cover the two new derived columns without running Streamlit: field selection and ordering, the overflow cap, the reviewed and synthetic markers, the never-changed case, and the date format
