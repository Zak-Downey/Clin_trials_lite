"""Trial Change Monitor -- a single-page Streamlit app.

Run it with:  streamlit run app.py

The view layer only. All decisions about what changed and what is stored live in
monitor.py and storage.py, so a later move off Streamlit replaces this file alone.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

import monitor
import simulate
import storage
from display import (
    DATE_FORMAT,
    SYNTHETIC,
    SYNTHETIC_MARK,
    UNREVIEWED,
    changed_fields,
    changed_on,
    group_fields,
    phase_label,
    render_card,
    show,
    status_label,
)

st.set_page_config(page_title="Trial Change Monitor", layout="wide")

# How wide the dossier is dealt. Three cards fit a laptop window without any of
# them growing so narrow that a drug list wraps to one word a line.
CARD_COLUMNS = 3

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
#
# One line per trial, so the whole watchlist is read without opening anything:
# what identifies the study, then what moved on it and when. Selecting a line
# opens that trial's profile underneath.

rows = monitor.watchlist(conn)

st.subheader(f"Watchlist ({len(rows)})")

if not rows:
    st.info("Nothing monitored yet. Paste an NCT ID above to begin.")
else:
    table = pd.DataFrame(
        [
            {
                # Identity first, then the study, then what moved. Two senses
                # of "status" end up near each other, so both are named for
                # what they are.
                "NCT ID": f"{SYNTHETIC_MARK} {r['nct_id']}" if r["synthetic"] else r["nct_id"],
                "Sponsor": show(r["sponsor"]),
                "Official title": show(r["title"]),
                "Phase": phase_label(r["phases"]),
                "Conditions": show(r["conditions"]),
                "Interventions": show(r["interventions"]),
                "Trial status": status_label(r["status"]),
                "What changed": changed_fields(r),
                "Changed on": changed_on(r),
            }
            for r in rows
        ]
    )
    event = st.dataframe(
        table,
        key="watchlist",
        hide_index=True,
        width="stretch",
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "NCT ID": st.column_config.TextColumn(width="small"),
            "Official title": st.column_config.TextColumn(width="large"),
            "Phase": st.column_config.TextColumn(width="small"),
            # The two reference columns are the ones given up when the table
            # runs out of room: a drug list rarely moves and is one click away,
            # whereas a cut-off "What changed" is the column the page exists
            # for. So the news gets the width and these truncate first.
            "Conditions": st.column_config.TextColumn(width="small"),
            "Interventions": st.column_config.TextColumn(width="small"),
            "Trial status": st.column_config.TextColumn(width="small"),
            "What changed": st.column_config.TextColumn(
                width="large",
                help="The fields that moved the last time this trial changed, "
                f"highest-signal first. {UNREVIEWED} means nobody has reviewed it "
                f"yet; {SYNTHETIC_MARK} marks a simulated change. Select the row "
                "for the values.",
            ),
            "Changed on": st.column_config.DateColumn(
                width="medium",
                format=DATE_FORMAT,
                help="The date that change was detected.",
            ),
        },
    )
    st.caption("Select a row to open its profile. Click a header to sort.")

    picked = event.selection.rows
    if picked:
        trial = rows[picked[0]]
        nct = trial["nct_id"]
        marked = monitor.marked_profile(conn, nct)

        st.divider()
        badge = f"{SYNTHETIC} · " if trial["synthetic"] else ""
        st.markdown(f"### {badge}{nct} — {show(trial['title'])}")
        st.caption(
            f"Last checked {show(trial['last_checked'])} · "
            f"last reviewed {show(trial['last_reviewed'])}"
        )
        if marked["unreviewed"] and st.button("Mark as reviewed", key=f"review_{nct}"):
            monitor.review(conn, nct)
            st.rerun()
        # The profile as a dossier: titled cards dealt across the page, each
        # one card-sized markdown block, so the whole study reads without
        # scrolling. Which fields belong to which card lives in display.py.
        columns = st.columns(CARD_COLUMNS, gap="medium")
        for index, (title, card) in enumerate(group_fields(marked["rows"])):
            with columns[index % CARD_COLUMNS], st.container(border=True):
                st.markdown(render_card(title, card))

# --- feed

st.subheader("Activity")

events = monitor.feed(conn)
if not events:
    st.caption("No activity yet.")
for event in events:
    badge = f" · {SYNTHETIC}" if event["synthetic"] else ""
    state = "" if event["reviewed"] else f" · {UNREVIEWED} unreviewed"
    st.markdown(f"`{event['at']}` — **{event['nct_id']}** — {event['kind']}{state}{badge}")
