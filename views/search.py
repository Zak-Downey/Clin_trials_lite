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
from display import COLUMN_WIDTHS, phase_label, study_line
from views.pickers import choose, names

NEW = "+ New list…"

# Where the last result set lives between runs. Selecting a row is a rerun, and
# re-running the query on every click would hit the registry for something the
# reader has already been shown.
FOUND = "search_results"

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
    st.caption(f"{len(selected)} selected.")
    if st.button(
        "Add selected",
        key="add_selected",
        type="primary",
        disabled=not selected or (picked == NEW and not fresh.strip()),
    ):
        with st.spinner(f"Fetching {len(selected)} trials from ClinicalTrials.gov…"):
            try:
                outcome, target = file_away(selected, picked, fresh)
            except monitor.MonitorError as exc:
                st.error(str(exc))
            else:
                report(outcome, target)

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
