"""Trial Change Monitor -- the app's entry point.

Run it with:  streamlit run app.py

Two pages, because adding a trial and reading what moved were competing for one
screen: the Watchlist reads one named list at a time, and the Search page is
where trials are found and filed into a list.

What is shared between them lives here -- the title and the navigation -- and
each page module is the view for its own screen. All decisions about what
changed and what is stored live in monitor.py and storage.py, so a later move
off Streamlit replaces these view files alone.
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Trial Change Monitor", layout="wide")

st.title("Trial Change Monitor")
st.caption("Watch competitors' ClinicalTrials.gov records and see what moves.")

# Along the top, the way a browser puts its tabs: there are two pages and they
# are read left to right, so a full-height sidebar rail spends a lot of the
# window on a choice between two things.
#
# The watchlist is what the reader comes back to, so it is where they land.
st.navigation(
    [
        st.Page("views/watchlist.py", title="Watchlist", icon="📋", default=True),
        st.Page("views/search.py", title="Search", icon="🔍"),
    ],
    position="top",
).run()
