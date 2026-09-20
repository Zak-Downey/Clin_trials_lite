"""Choosing a named list, shared by the two pages that have to do it.

Both pages stand in a list -- one to read it, one to add to it -- so the control,
and the two ways a selection goes stale behind it, are written once here.
"""

from __future__ import annotations

import sqlite3

import streamlit as st

import storage


def names(conn: sqlite3.Connection) -> dict[int, str]:
    """Every list, id to name, in the order the reader sees them."""
    return {row["id"]: row["name"] for row in storage.list_lists(conn)}


def _kept_at(key: str) -> str:
    """Where the picker keeps its own record of what was chosen.

    Deliberately not the widget's own key, because this is the thing that has
    to outlive it.
    """
    return f"{key}_kept"


def choose(column, conn: sqlite3.Connection, label: str, key: str, extra: str | None = None):
    """Draw a list picker and return what was chosen: a list id, or `extra`.

    `extra` is a sentinel offered alongside the real lists, for the page whose
    picker can also mean "a list that doesn't exist yet". It is remembered like
    any other choice: singling it out would be a special case earning nothing,
    since a reader halfway through naming a new list has the same claim to be
    left where they are as one reading an existing one.

    The choice is remembered twice over: once by Streamlit, under the widget's
    key, and once here. The second record is what makes the picker hold still.
    Streamlit works out whether the control on this run is the one from the last
    run partly from the words it is drawing, so renaming a list -- or creating
    one -- makes this picker look like a different picker, and the selection
    Streamlit was keeping for it is dropped. That is what used to put a reader
    back in the first list at the moment they renamed the one they were reading.
    Lists are chosen by id, and ids do not change when names do, so the record
    kept here survives it. It is handed to the control as its starting position,
    which Streamlit reads only when it has nothing of its own -- so on a version
    that keeps the selection itself, this changes nothing.

    Either record can name a list that has since been deleted, which Streamlit
    treats as a selection outside the options. Both are dropped when that
    happens, so the picker falls back to the first list rather than raising.
    """
    options = names(conn)
    offered = list(options) + ([extra] if extra else [])
    for where in (key, _kept_at(key)):
        if st.session_state.get(where) not in offered:
            st.session_state.pop(where, None)
    kept = st.session_state.get(_kept_at(key))
    chosen = column.selectbox(
        label,
        offered,
        index=offered.index(kept) if kept is not None else 0,
        format_func=lambda value: extra if value == extra else options[value],
        key=key,
    )
    st.session_state[_kept_at(key)] = chosen
    return chosen
