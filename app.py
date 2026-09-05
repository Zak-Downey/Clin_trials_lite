"""Trial Change Monitor -- a single-page Streamlit app.

Run it with:  streamlit run app.py

The view layer only. All decisions about what changed and what is stored live in
monitor.py and storage.py, so a later move off Streamlit replaces this file alone.
"""

from __future__ import annotations

import streamlit as st

import monitor
import simulate
import storage
from display import SYNTHETIC, label, show

st.set_page_config(page_title="Trial Change Monitor", layout="wide")

conn = storage.connect()

st.title("Trial Change Monitor")
st.caption("Watch competitors' ClinicalTrials.gov records and see what moves.")

# --- add a trial

with st.form("add", clear_on_submit=True):
    col_input, col_button = st.columns([4, 1])
    pasted = col_input.text_input(
        "NCT ID", placeholder="NCT03412565", label_visibility="collapsed"
    )
    submitted = col_button.form_submit_button("Start monitoring", width="stretch")

if submitted:
    if not pasted.strip():
        st.error("Paste an NCT ID first.")
    else:
        with st.spinner(f"Fetching {pasted.strip()} from ClinicalTrials.gov…"):
            try:
                added = monitor.add(conn, pasted)
                st.success(f"Now monitoring {added}.")
            except monitor.MonitorError as exc:
                st.error(str(exc))

# --- check for changes

trials = storage.list_trials(conn)

if trials:
    if st.button("Check all", key="check_all", type="primary"):
        total = len(trials)
        progress = st.progress(0.0, text="Checking…")
        results = []
        for done, result in enumerate(monitor.check_all(conn), start=1):
            progress.progress(
                done / total, text=f"Checked {result['nct_id']} ({done} of {total})"
            )
            results.append(result)
        progress.empty()

        summary = monitor.summarise(results)
        if summary["level"] == "success":
            st.success(summary["message"])
        else:
            st.warning(summary["message"])
        for result in summary["updated"]:
            badge = f" · {SYNTHETIC}" if storage.is_synthetic(conn, result["nct_id"]) else ""
            st.markdown(f"**{result['nct_id']}** — {result['detail']}{badge}")
        for result in summary["failed"]:
            st.error(f"{result['nct_id']} — {result['detail']}")

        # Re-read so the rows below show the "last checked" times just written.
        trials = storage.list_trials(conn)

# --- developer tools
#
# In the sidebar, and executed before the watchlist and feed render, so a
# simulation or a deletion is reflected on the page in the same run.

with st.sidebar.expander("🧪 Developer tools — synthetic data", expanded=True):
    st.caption(
        "Simulating a change rewinds a trial's *stored* history so the next check "
        "finds a real difference against the live registry — the same code path a "
        "genuine sponsor edit travels. Everything written here is flagged in the "
        "database and can be removed below."
    )

    if trials:
        target = st.selectbox("Trial", [t["nct_id"] for t in trials], key="simulate_target")
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

# --- watchlist

st.subheader(f"Watchlist ({len(trials)})")

if not trials:
    st.info("Nothing monitored yet. Paste an NCT ID above to begin.")

for trial in trials:
    nct = trial["nct_id"]
    profile = monitor.profile_of(conn, nct) or {}
    badge = f"{SYNTHETIC} · " if storage.is_synthetic(conn, nct) else ""
    header = (
        f"{badge}**{nct}** · {show(profile.get('leadSponsor'))} · "
        f"{show(profile.get('overallStatus'))} — {show(profile.get('briefTitle'))}"
    )
    with st.expander(header):
        st.caption(f"Last checked {show(trial['last_checked'])}")
        for key, value in profile.items():
            if key == "resultsUrl" and value:
                st.markdown(f"**{label(key)}**  \n[View results on ClinicalTrials.gov]({value})")
            else:
                st.markdown(f"**{label(key)}**  \n{show(value)}")

# --- feed

st.subheader("Activity")

events = monitor.feed(conn)
if not events:
    st.caption("No activity yet.")
for event in events:
    badge = f" · {SYNTHETIC}" if event["synthetic"] else ""
    st.markdown(f"`{event['at']}` — **{event['nct_id']}** — {event['kind']}{badge}")
