"""The Search page: where a trial is found and filed into a named list.

For now the only way in is the NCT ID, moved off the watchlist page so adding
and reading stop competing for one screen. The registry query that fills a list
in one sitting is the next ticket; the destination control it needs is already
here, because which list a trial joins is a choice made every time.
"""

from __future__ import annotations

import streamlit as st

import monitor
import storage
from views.pickers import choose, names

NEW = "+ New list…"

conn = storage.connect()

st.subheader("Add a trial")

# The destination sits outside the form: choosing "new list" has to reveal the
# name box straight away rather than waiting for a submission.
destination, naming = st.columns([2, 2], vertical_alignment="bottom")
picked = choose(destination, conn, "Add to", "destination_list", extra=NEW)
fresh = (
    naming.text_input("New list name", placeholder="Myeloma — Janssen", key="new_list_name")
    if picked == NEW
    else ""
)

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
                if picked == NEW:
                    added, target = monitor.add_to_new_list(conn, pasted, fresh)
                else:
                    target = picked
                    added = monitor.add(conn, pasted, target)
            st.success(f"Now monitoring {added} in “{names(conn)[target]}”.")
        except monitor.MonitorError as exc:
            st.error(str(exc))
