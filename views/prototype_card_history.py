"""PROTOTYPE -- throwaway. Four ways to keep reviewed changes visible on the dossier.

Four variants of the opened trial's dossier on the existing Watchlist page,
switchable via ?variant=A..D, the bar at the bottom, or the arrow keys:

  A  Trace       each field keeps a quiet grey note of its last change
  B  Card log    each card carries its own full history, folded away
  C  Lens        one control re-highlights the dossier over a chosen window
  D  Timeline    clean cards, with every check listed down a rail beside them

Launch with `python prototype_card_history.py`. Nothing here ships: the
published site mounts only the files web/index.html names.
"""

from __future__ import annotations

import datetime

import streamlit as st
import streamlit.components.v1 as components

import diff
import storage
from display import (
    AMENDED,
    CARDS,
    CRITERIA,
    OTHER,
    SYNTHETIC_MARK,
    UNREVIEWED,
    field_line,
    group_fields,
    humanise,
    label,
    long_date,
    render_card,
    show,
)

VARIANTS = {"A": "Trace", "B": "Card log", "C": "Lens", "D": "Timeline"}
CARD_COLUMNS = 3
REVIEWED_MARK = "✓"


# --- shared data: every change record, folded onto the row it shows under


def _card_of(field: str) -> str:
    for title, fields in CARDS:
        if field in fields:
            return title
    return OTHER


def _short(value, limit: int = 48) -> str:
    text = show(value)
    if isinstance(value, str) and value.isupper():
        text = humanise(value)
    return text if len(text) <= limit else text[:limit].rstrip(" ,") + "…"


def _move(change: dict) -> str:
    """A change as "was → now", or the amended note for the criteria."""
    if change["field"] == CRITERIA:
        return AMENDED
    return f"{_short(change['previous'])} → {_short(change['current'])}"


def history(conn, nct: str) -> list[dict]:
    """Every change, newest first, each named by the row and card it shows in."""
    out = []
    for change in storage.list_changes(conn, nct):
        row = diff.QUALIFIES.get(change["field"], change["field"])
        out.append(
            {
                **change,
                "row": row,
                "card": _card_of(row),
                # A qualifier move reads under its value: "Enrollment: Estimated → Actual".
                "what": label(row)
                + (" (type)" if change["field"] in diff.QUALIFIES else ""),
                "day": change["detected_at"][:10],
            }
        )
    return out


def _state(change: dict) -> str:
    return REVIEWED_MARK if change["reviewed"] else UNREVIEWED


# --- A: trace


def variant_a(conn, nct, marked):
    """The field's last move stays on its line, in grey, after review."""
    st.caption(
        "Reviewed fields stay plain but keep a grey note of their last move. "
        "Unread moves are highlighted as today."
    )
    # The newest check that touched each row, value and qualifier together.
    last: dict[str, list[dict]] = {}
    for change in history(conn, nct):
        moves = last.setdefault(change["row"], [])
        if not moves or moves[0]["day"] == change["day"]:
            moves.append(change)

    columns = st.columns(CARD_COLUMNS, gap="medium")
    for index, (title, rows) in enumerate(group_fields(marked["rows"])):
        lines = []
        for row in rows:
            line = field_line(row, nct)
            trace = last.get(row["field"])
            if not row["changed"] and trace:
                trace.sort(key=lambda c: c["field"] in diff.QUALIFIES)
                was = " · ".join(_short(c["previous"]) for c in trace)
                line += (
                    f"  \n&nbsp;&nbsp;&nbsp;&nbsp;:gray[_{REVIEWED_MARK} "
                    f"{long_date(trace[0]['day'])} · was {was}_]"
                )
            lines.append(line)
        unread = sum(1 for r in rows if r["changed"])
        bell = f" {UNREVIEWED}{unread}" if unread else ""
        with columns[index % CARD_COLUMNS], st.container(border=True):
            st.markdown("  \n".join([f"**{title.upper()}**{bell}"] + lines))


# --- B: card log


def variant_b(conn, nct, marked):
    """Each card folds its own history away underneath it."""
    st.caption(
        "Cards read clean once reviewed; each one carries its own history, "
        "folded, with the count on the fold."
    )
    by_card: dict[str, list[dict]] = {}
    for change in history(conn, nct):
        by_card.setdefault(change["card"], []).append(change)

    columns = st.columns(CARD_COLUMNS, gap="medium")
    for index, (title, rows) in enumerate(group_fields(marked["rows"])):
        log = by_card.get(title, [])
        with columns[index % CARD_COLUMNS], st.container(border=True):
            st.markdown(render_card(title, rows, nct))
            if not log:
                st.caption("No changes since monitoring began.")
                continue
            newest = long_date(log[0]["day"])
            with st.expander(f"History · {len(log)} · last {newest}"):
                lines = []
                for day in dict.fromkeys(c["day"] for c in log):
                    lines.append(f"**{long_date(day)}**")
                    for c in (c for c in log if c["day"] == day):
                        fake = f" {SYNTHETIC_MARK}" if c["synthetic"] else ""
                        lines.append(
                            f"{_state(c)} {c['what']}{fake}  \n"
                            f"&nbsp;&nbsp;&nbsp;&nbsp;:gray[{_move(c)}]"
                        )
                st.markdown("  \n".join(lines))


# --- C: lens

LENSES = {
    "Unread": None,
    "7 days": 7,
    "30 days": 30,
    "90 days": 90,
    "All": 100_000,
}


def variant_c(conn, nct, marked):
    """One control widens what the dossier highlights, reviewed or not."""
    lens = st.segmented_control(
        "Highlight changes", list(LENSES), default="Unread", key="proto_lens"
    ) or "Unread"
    days = LENSES[lens]
    changes = storage.list_changes(conn, nct)

    if days is None:
        rows = marked["rows"]
        seen = set()
        st.caption("Highlighting only what is unread — today's behaviour.")
    else:
        since = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
        window = [c for c in changes if c["detected_at"][:10] >= since]
        # Re-mark the window as unread so the ordinary highlighting shows it,
        # remembering which of them had in fact been read.
        rows = diff.annotate(marked["profile"], [{**c, "reviewed": False} for c in window])
        unread = {r["field"] for r in marked["rows"] if r["changed"]}
        seen = {r["field"] for r in rows if r["changed"]} - unread
        st.caption(
            f"{len(window)} changes in the window. :orange-background[Orange/red] "
            f"is unread; :blue-background[blue {REVIEWED_MARK}] was already reviewed."
        )

    columns = st.columns(CARD_COLUMNS, gap="medium")
    for index, (title, card) in enumerate(group_fields(rows)):
        lines = []
        for row in card:
            line = field_line(row, nct)
            if row["field"] in seen:
                line = (
                    line.replace(":red-background[", ":blue-background[")
                    .replace(":orange-background[", ":blue-background[")
                    .replace("]", f"] {REVIEWED_MARK}", 1)
                )
            lines.append(line)
        count = sum(1 for r in card if r["changed"])
        bell = f" · {count} in view" if count else ""
        with columns[index % CARD_COLUMNS], st.container(border=True):
            st.markdown("  \n".join([f"**{title.upper()}**{bell}"] + lines))


# --- D: timeline


def variant_d(conn, nct, marked):
    """Clean cards on the left; every check down a rail on the right."""
    cards_side, rail = st.columns([3, 1], gap="large")
    log = history(conn, nct)

    with cards_side:
        columns = st.columns(2, gap="medium")
        counts = {}
        for c in log:
            counts[c["card"]] = counts.get(c["card"], 0) + 1
        for index, (title, rows) in enumerate(group_fields(marked["rows"])):
            with columns[index % 2], st.container(border=True):
                block = render_card(title, rows, nct)
                if counts.get(title):
                    block += f"  \n:gray[🕘 {counts[title]} past changes — see rail]"
                st.markdown(block)

    with rail, st.container(border=True):
        st.markdown("**CHANGE HISTORY**")
        cards = sorted({c["card"] for c in log})
        only = st.multiselect(
            "Cards", cards, key="proto_rail_cards", placeholder="All cards",
            label_visibility="collapsed",
        )
        shown = [c for c in log if not only or c["card"] in only]
        if not shown:
            st.caption("Nothing recorded.")
        lines = []
        for day in dict.fromkeys(c["day"] for c in shown):
            batch = [c for c in shown if c["day"] == day]
            unread = sum(1 for c in batch if not c["reviewed"])
            tag = f" {UNREVIEWED}{unread}" if unread else f" :gray[{REVIEWED_MARK}]"
            lines.append(f"**{long_date(day)}**{tag}")
            for c in batch:
                lines.append(
                    f":gray[{c['card']} ›] {c['what']}  \n"
                    f"&nbsp;&nbsp;&nbsp;&nbsp;:gray[{_move(c)}]"
                )
            lines.append("")
        st.markdown("  \n".join(lines))


# --- switcher


def current() -> str:
    key = st.query_params.get("variant", "A").upper()
    return key if key in VARIANTS else "A"


def _go(step: int) -> None:
    keys = list(VARIANTS)
    st.query_params["variant"] = keys[(keys.index(current()) + step) % len(keys)]


def switcher() -> None:
    """A fixed pill at the bottom centre. Buttons, not links, so the selected
    row survives a switch; a full reload would drop it."""
    st.html(
        """<style>
        .st-key-proto_switcher {
            position: fixed; bottom: 18px; left: 50%; transform: translateX(-50%);
            z-index: 999999; width: auto !important; background: #111; color: #fff;
            padding: 6px 10px; border-radius: 999px; box-shadow: 0 6px 24px rgba(0,0,0,.35);
        }
        .st-key-proto_switcher p { color: #fff; margin: 0; white-space: nowrap; }
        .st-key-proto_switcher button { background: #333; color: #fff; border: 0; }
        </style>"""
    )
    with st.container(key="proto_switcher", horizontal=True, vertical_alignment="center"):
        st.button("◀", key="proto_prev", on_click=_go, args=(-1,))
        key = current()
        st.markdown(f"**PROTOTYPE** · {key} ({VARIANTS[key]})")
        st.button("▶", key="proto_next", on_click=_go, args=(1,))
    # Arrow keys press the buttons, unless the reader is typing somewhere.
    components.html(
        """<script>
        const doc = window.parent.document;
        if (!doc.__protoKeys) {
          doc.__protoKeys = true;
          doc.addEventListener('keydown', (e) => {
            const t = e.target;
            if (t.closest && t.closest('input, textarea, [contenteditable]')) return;
            const which = {ArrowLeft: 'proto_prev', ArrowRight: 'proto_next'}[e.key];
            if (!which) return;
            const b = doc.querySelector('.st-key-' + which + ' button');
            if (b) { e.preventDefault(); b.click(); }
          });
        }
        </script>""",
        height=0,
    )


def render(conn, nct, marked) -> None:
    {"A": variant_a, "B": variant_b, "C": variant_c, "D": variant_d}[current()](
        conn, nct, marked
    )
