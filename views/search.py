"""The Search page: where trials are found and filed into a named list.

Two ways in, in the order they are reached for. A query on the four axes
somebody actually describes a competitor's programme by -- condition,
intervention, sponsor, phase -- fills a list in one sitting; the NCT ID box
below it is for the study whose number is already in hand.

The destination is chosen *after* the results are selected, not before. That is
the point of the layout rather than an accident of it: it is what lets one
search be split across two lists, which is what happens the moment a search for
a drug turns up studies in two indications.

Searching and filing are monitor's business and the columns are display's, so
this file only draws.
"""

from __future__ import annotations

import streamlit as st

import monitor
import storage
from display import COLUMN_WIDTHS, phase_label, search_line, study_line
from views.pickers import choose, names

NEW = "+ New list…"

# Where the last result set lives between runs. Selecting a row is a rerun, and
# re-running the query on every click would hit the registry for something the
# reader has already been shown.
FOUND = "search_results"

# The query those results came from, kept beside them so a search saved to a
# list is the one that produced the rows on screen -- not whatever has since
# been typed into the boxes without pressing Search.
QUERY = "search_query"

# The results table, whose selection Streamlit keeps under the same key.
RESULTS = "results"

conn = storage.connect()


def destination(key: str, label: str = "Add to"):
    """The list a trial is being filed into: an existing one, or a new name.

    Returns what to hand monitor: the chosen list id, or the new name to make.
    """
    picking, naming = st.columns([2, 2], vertical_alignment="bottom")
    picked = choose(picking, conn, label, key, extra=NEW)
    if picked != NEW:
        return picked, ""
    fresh = naming.text_input(
        "New list name", placeholder="Myeloma — Janssen", key=f"{key}_name"
    )
    return NEW, fresh


def file_away(nct_ids: list[str], picked, fresh: str):
    """Put trials in the chosen list, making it first if it is a new name."""
    if picked == NEW:
        return monitor.add_to_new_list(conn, nct_ids, fresh)
    return monitor.add_many(conn, nct_ids, picked), picked


def report(outcome: dict, target: int) -> None:
    """Say what landed and what did not, in monitor's words rather than mine."""
    summary = monitor.summarise_adds(outcome, names(conn)[target])
    (st.success if summary["level"] == "success" else st.warning)(summary["message"])
    for failure in summary["failed"]:
        st.error(f"{failure['nct_id']} — {failure['detail']}")


def remember_for(list_id: int) -> None:
    """Point a list at the search that produced the rows on screen."""
    query = monitor.remember_search(conn, list_id, st.session_state[QUERY])
    st.info(
        f"“{names(conn)[list_id]}” is now watching for new trials matching "
        f"{search_line(query)}."
    )


# --- the query

st.subheader("Search ClinicalTrials.gov")

with st.form("search"):
    cond_col, intr_col, spons_col, phase_col, go_col = st.columns(
        [2, 2, 2, 2, 1], vertical_alignment="bottom"
    )
    cond = cond_col.text_input("Condition", placeholder="multiple myeloma", key="cond")
    intr = intr_col.text_input("Intervention", placeholder="daratumumab", key="intr")
    spons = spons_col.text_input("Sponsor", placeholder="Janssen", key="spons")
    phases = phase_col.multiselect(
        "Phase", monitor.PHASES, format_func=lambda code: phase_label([code]), key="phases"
    )
    searched = go_col.form_submit_button("Search", type="primary", width="stretch")

if searched:
    # Cleared first, so a failed search never leaves the previous result set on
    # screen looking like the answer to the query just typed.
    st.session_state.pop(FOUND, None)
    # The selection goes with the results it belonged to. It is a set of row
    # numbers, so against a different result set those numbers mean a different
    # study -- or, after a narrower search, no study at all.
    st.session_state.pop(RESULTS, None)
    try:
        with st.spinner("Searching ClinicalTrials.gov…"):
            st.session_state[FOUND] = monitor.search(cond, intr, spons, phases)
            st.session_state[QUERY] = monitor.as_query(cond, intr, spons, phases)
    except monitor.MonitorError as exc:
        st.error(str(exc))

found = st.session_state.get(FOUND)

if found is not None and not found["rows"]:
    st.warning(monitor.summarise_search(found))
elif found is not None:
    rows = found["rows"]
    st.caption(f"{monitor.summarise_search(found)} Tick the rows you want.")

    results = st.dataframe(
        [study_line(r) for r in rows],
        key=RESULTS,
        hide_index=True,
        width="stretch",
        on_select="rerun",
        selection_mode="multi-row",
        # The same columns, at the same widths, the watchlist gives them:
        # this table is read as the list it feeds.
        column_config={
            name: st.column_config.TextColumn(width=width)
            for name, width in COLUMN_WIDTHS.items()
        },
    )

    selected = [rows[i]["nct_id"] for i in results.selection.rows]
    picked, fresh = destination("results_list")
    # A list is a therapy area, not a bag of trial numbers, so the query that
    # filled it can stay with it: every later check re-runs the search and
    # offers back whatever has appeared since. Both ways of doing that are
    # offered here, beside the rows the query matched, because this is the
    # moment the reader can see it is the right query.
    #
    # The tick-box is for the list being filled right now, including one being
    # named on the spot, which has no id to point at until the add has made it.
    # The button beside it is for a list that already exists -- which is how a
    # remembered search is *changed*, without having to add a trial to do it.
    remember = st.checkbox(
        f"Save this as the list's {monitor.REMEMBERED_SEARCH}",
        key="remember_search",
        help="The list re-runs this search whenever it is checked, and offers "
        "back anything matching it that the list does not already hold. "
        "Nothing joins the list until you adopt it.",
    )
    st.caption(f"{len(selected)} selected.")
    adding, saving, _ = st.columns([1, 1, 3], vertical_alignment="bottom")
    if adding.button(
        "Add selected",
        key="add_selected",
        type="primary",
        width="stretch",
        disabled=not selected or (picked == NEW and not fresh.strip()),
    ):
        with st.spinner(f"Fetching {len(selected)} trials from ClinicalTrials.gov…"):
            try:
                outcome, target = file_away(selected, picked, fresh)
            except monitor.MonitorError as exc:
                st.error(str(exc))
            else:
                report(outcome, target)
                if remember:
                    remember_for(target)
    if saving.button(
        f"Save the {monitor.REMEMBERED_SEARCH} only",
        key="save_search",
        width="stretch",
        # A list that does not exist yet cannot be pointed at anything; naming
        # one is what the add is for.
        disabled=picked == NEW,
        help="Point this list at the search above without adding anything, "
        "replacing whatever it was watching for before.",
    ):
        remember_for(picked)

# --- one at a time

st.divider()
st.subheader("Add by NCT ID")

picked, fresh = destination("destination_list")

with st.form("add", clear_on_submit=True):
    col_input, col_button = st.columns([4, 1], vertical_alignment="bottom")
    pasted = col_input.text_input(
        "NCT ID", placeholder="NCT03412565", label_visibility="collapsed", key="nct_id"
    )
    submitted = col_button.form_submit_button("Start monitoring", width="stretch")

if submitted:
    if not pasted.strip():
        st.error("Paste an NCT ID first.")
    else:
        try:
            with st.spinner(f"Fetching {pasted.strip()} from ClinicalTrials.gov…"):
                outcome, target = file_away([pasted], picked, fresh)
        except monitor.MonitorError as exc:
            st.error(str(exc))
        else:
            report(outcome, target)
