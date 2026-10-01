# 16: Switching to a shorter list must not open a row it does not have

**What to fix:** On the published site, selecting a row in one list and then moving the picker to a list with fewer rows raises `IndexError: list index out of range` at the row lookup under the table, and the page stays broken until a row of the new list is clicked. Removing the last row of a list while it is selected does the same.

The cause is a stale selection. The watchlist table is keyed `watchlist`, and Streamlit 1.62, which the pinned stlite 1.9.1 carries, identifies a keyed dataframe by its key alone, so the row number selected in one list is reported again under the next. Streamlit 1.50, which a Python 3.9 checkout runs, folded the table's data into its identity, so changing lists silently gave a fresh table and the local checks never saw it. Streamlit's own source at that call site notes that selections "can become orphaned when the data changes, e.g. when rows get removed" and leaves it to the app.

Two defences, both in the Watchlist page:

1. The table's selection goes with the list it was made in. When the chosen list changes, the selection is dropped before the table is drawn, the way the Search page drops its results table's selection when a new search runs. A row selected in Lung must not open row *n* of Myeloma unasked, which is a different trial.
2. A row number past the end of the list reads as no selection, so a selection left behind by a removal never reaches the lookup.

**Blocked by:** 08

**Status:** done

- [x] Moving the picker to a shorter list with a low row selected renders the new list with nothing open, and no exception
- [x] A selection carried into a list from a longer one does not open a different trial
- [x] A row number beyond the end of the list is treated as no selection
- [x] Tests cover both: the list switch and the stale index

## Comments

**2026-10-01.** Found on the live site: a two-trial list opened after a longer one showed the traceback under the table. The failing line dates from ticket 08; the exposure dates from the stlite move in ticket 09, which brought Streamlit 1.62's key-only widget identity. Local Streamlit 1.50 cannot reproduce it, so the fix was checked against a local `build_site.py` build driven in headless Chromium as well as under the test harness.
