"""The Watchlist page: one named list at a time.

Which list is showing is chosen at the top, and the table, the profile that
opens under it, and the activity feed all narrow to it, so somebody covering two
therapy areas never reads half another indication's business. Naming the lists
lives here too, beside the control that chooses between them; filling them is
the Search page's job.
"""

from __future__ import annotations

import datetime

import pandas as pd
import streamlit as st

import briefing
import monitor
import storage
from display import (
    COLUMN_WIDTHS,
    DATE_FORMAT,
    SYNTHETIC,
    SYNTHETIC_MARK,
    UNREVIEWED,
    changed_fields,
    detected_on,
    group_fields,
    registry_updated,
    render_card,
    show,
    study_line,
)
from views.pickers import choose, names

# How wide the dossier is dealt. Three cards fit a laptop window without any of
# them growing so narrow that a drug list wraps to one word a line.
CARD_COLUMNS = 3

# How far back a custom range opens before the reader moves either end. A month
# is the window a briefing is usually written over.
CUSTOM_DAYS = 30

conn = storage.connect()

# --- which list is showing

picker, _ = st.columns([2, 3], vertical_alignment="bottom")
chosen = choose(picker, conn, "Watchlist", "chosen_list")
chosen_name = names(conn)[chosen]

with st.expander("Manage lists"):
    fresh = st.text_input("New list", placeholder="Myeloma — Janssen", key="new_list")
    if st.button("Create list", key="create_list"):
        try:
            monitor.create_list(conn, fresh)
            st.rerun()
        except monitor.MonitorError as exc:
            st.error(str(exc))

    renamed = st.text_input("Rename this list", value=chosen_name, key=f"rename_{chosen}")
    rename, delete = st.columns(2)
    if rename.button("Rename", key="rename_list", width="stretch"):
        try:
            monitor.rename_list(conn, chosen, renamed)
            st.rerun()
        except monitor.MonitorError as exc:
            st.error(str(exc))
    # Deleting the list stops monitoring whatever no other list still holds, so
    # it is said out loud rather than left to be discovered.
    delete.caption("Deleting a list stops monitoring any trial no other list holds.")
    if delete.button("Delete this list", key="delete_list", width="stretch"):
        monitor.delete_list(conn, chosen)
        st.rerun()

# --- check for changes

trials = storage.list_trials(conn, chosen)

if trials:
    check_column, force_column, _ = st.columns([1, 2, 2], vertical_alignment="center")
    pressed = check_column.button(
        "Check all", key="check_all", type="primary", width="stretch"
    )
    # The registry's own stamp normally makes a check cheap by ending it early.
    # That is right for registry edits and wrong after the monitored profile
    # itself changes, so the way past it is offered rather than hidden.
    force = force_column.checkbox(
        "Compare every field",
        key="force_check",
        help="Ignore the registry's last-updated date and compare every "
        "monitored field. Slower; use it after what the tool monitors changes.",
    )
    if pressed:
        total = len(trials)
        progress = st.progress(0.0, text="Checking…")
        results = []
        for done, result in enumerate(monitor.check_all(conn, chosen, force=force), start=1):
            progress.progress(
                done / total, text=f"Checked {result['nct_id']} ({done} of {total})"
            )
            results.append(result)
        progress.empty()

        summary = monitor.summarise(results)
        {"success": st.success, "info": st.info, "warning": st.warning}[summary["level"]](
            summary["message"]
        )
        for result in summary["updated"]:
            badge = f" · {SYNTHETIC}" if storage.is_synthetic(conn, result["nct_id"]) else ""
            st.markdown(f"**{result['nct_id']}** — {result['detail']}{badge}")
        for result in summary["failed"]:
            st.error(f"{result['nct_id']} — {result['detail']}")

# --- watchlist
#
# One line per trial, so the whole list is read without opening anything: what
# identifies the study, then what moved on it and when. Selecting a line opens
# that trial's profile underneath.

rows = monitor.watchlist(conn, chosen)

st.subheader(f"{chosen_name} ({len(rows)})")

if not rows:
    st.info("Nothing in this list yet. Add a trial from the Search page.")
else:
    table = pd.DataFrame(
        [
            {
                # The columns the search results share, then what moved on top
                # of them. A simulated trial is marked in the ID column, which
                # is the one narrow enough to need the mark alone.
                **study_line(r),
                "NCT ID": f"{SYNTHETIC_MARK} {r['nct_id']}" if r["synthetic"] else r["nct_id"],
                "What changed": changed_fields(r),
                "Registry updated": registry_updated(r),
                "Detected": detected_on(r),
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
            **{
                name: st.column_config.TextColumn(width=width)
                for name, width in COLUMN_WIDTHS.items()
            },
            "What changed": st.column_config.TextColumn(
                width="large",
                help="Every field still awaiting review, highest-signal first, "
                f"however many checks those moves are spread across. {UNREVIEWED} "
                f"means nobody has reviewed it yet; {SYNTHETIC_MARK} marks a "
                "simulated change. Select the row for the values.",
            ),
            "Registry updated": st.column_config.DateColumn(
                width="medium",
                format=DATE_FORMAT,
                help="The date the sponsor revised the registry record.",
            ),
            "Detected": st.column_config.DateColumn(
                width="medium",
                format=DATE_FORMAT,
                help="The date this tool noticed, which is the day somebody "
                "pressed Check.",
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
        # Which other lists hold it, because taking it out of this one leaves
        # those alone and the reader should know that before pressing remove.
        elsewhere = [
            row["name"] for row in storage.lists_holding(conn, nct) if row["id"] != chosen
        ]
        if elsewhere:
            st.caption(f"Also in {', '.join(elsewhere)}.")

        review, drop, _ = st.columns([1, 1, 3])
        if marked["unreviewed"] and review.button(
            "Mark as reviewed", key=f"review_{nct}", width="stretch"
        ):
            monitor.review(conn, nct)
            st.rerun()
        if drop.button("Remove from this list", key=f"remove_{nct}", width="stretch"):
            monitor.remove(conn, nct, chosen)
            st.rerun()
        # The profile as a dossier: titled cards dealt across the page, each
        # one card-sized markdown block, so the whole study reads without
        # scrolling. Which fields belong to which card lives in display.py.
        columns = st.columns(CARD_COLUMNS, gap="medium")
        for index, (title, card) in enumerate(group_fields(marked["rows"])):
            with columns[index % CARD_COLUMNS], st.container(border=True):
                st.markdown(render_card(title, card, nct))

# --- the briefing
#
# The last mile out of this tool. Everything a line of an email needs is already
# stored, so it leaves as text to paste and as a file to open rather than being
# retyped off the table above. What the summary says lives in briefing.py; this
# is only the range control and the two ways out.

st.subheader("Change summary")
st.caption(
    "Everything the list moved by in a chosen window, reviewed or not, "
    "highest-signal fields first. Copy it into a briefing, or take the file."
)

period = st.radio(
    "Period",
    briefing.PRESETS,
    horizontal=True,
    key="briefing_period",
    label_visibility="collapsed",
)

span = briefing.preset_range(period)
if span is None:
    today = datetime.date.today()
    picked = st.date_input(
        "Dates",
        value=(today - datetime.timedelta(days=CUSTOM_DAYS), today),
        key="briefing_dates",
        label_visibility="collapsed",
    )
    # Streamlit hands back one date while the reader is still choosing the
    # second, which is a half-picked range rather than a one-day one.
    span = tuple(picked) if len(picked) == 2 else None

if span is None:
    st.caption("Pick the day the range ends.")
else:
    reported = briefing.summarise(conn, chosen, *span)
    # st.code carries its own copy button, which is the whole point of this
    # form: the text has to reach an email without being reformatted on the way.
    st.code(briefing.as_text(reported), language=None)

    spreadsheet = briefing.as_csv(reported)
    if spreadsheet:
        st.download_button(
            "Download CSV",
            spreadsheet,
            file_name=briefing.filename(reported),
            mime="text/csv",
            key="briefing_csv",
        )

# --- feed

st.subheader("Activity")

events = monitor.feed(conn, chosen)
if not events:
    st.caption("No activity yet.")
for event in events:
    badge = f" · {SYNTHETIC}" if event["synthetic"] else ""
    state = "" if event["reviewed"] else f" · {UNREVIEWED} unreviewed"
    st.markdown(f"`{event['at']}` — **{event['nct_id']}** — {event['kind']}{state}{badge}")
