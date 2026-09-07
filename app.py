"""Trial Change Monitor -- the app's entry point.

Run it with:  streamlit run app.py

Two pages, because adding a trial and reading what moved were competing for one
screen: the Watchlist reads one named list at a time, and the Search page is
where trials are found and filed into a list.

What is shared between them lives here -- the title, and the developer-only
simulator in the sidebar -- and each page module is the view for its own screen.
All decisions about what changed and what is stored live in monitor.py and
storage.py, so a later move off Streamlit replaces these view files alone.
"""

from __future__ import annotations

import streamlit as st

import monitor
import simulate
import storage

st.set_page_config(page_title="Trial Change Monitor", layout="wide")

conn = storage.connect()

st.title("Trial Change Monitor")
st.caption("Watch competitors' ClinicalTrials.gov records and see what moves.")

# --- developer tools
#
# In the sidebar and on every page, so a simulation is available from wherever
# the reader happens to be standing. Executed before the chosen page renders,
# so a simulation or a deletion shows up on that page in the same run.

with st.sidebar.expander("🧪 Developer tools — synthetic data", expanded=True):
    st.caption(
        "Simulating a change rewinds a trial's *stored* history so the next check "
        "finds a real difference against the live registry — the same code path a "
        "genuine sponsor edit travels. Everything written here is flagged in the "
        "database and can be removed below."
    )

    watched = storage.list_trials(conn)
    if watched:
        target = st.selectbox("Trial", [t["nct_id"] for t in watched], key="simulate_target")
        if st.button("Simulate a change", key="simulate"):
            try:
                st.warning(f"{simulate.rewind(conn, target)['detail']} Now press “Check all”.")
            except monitor.MonitorError as exc:
                st.error(str(exc))
    else:
        st.caption("Add a trial before simulating a change on it.")

    if st.button("Delete all synthetic data", key="delete_synthetic"):
        removed = storage.delete_synthetic(conn)
        st.success(f"Deleted {removed} synthetic row{'' if removed == 1 else 's'}.")

# The watchlist is what the reader comes back to, so it is where they land.
st.navigation(
    [
        st.Page("views/watchlist.py", title="Watchlist", icon="📋", default=True),
        st.Page("views/search.py", title="Search", icon="🔍"),
    ]
).run()
