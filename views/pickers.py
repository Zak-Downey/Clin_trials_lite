"""Choosing a named list, shared by the two pages that have to do it.

Both pages stand in a list -- one to read it, one to add to it -- so the control
and the stale-selection problem behind it are written once here.
"""

from __future__ import annotations

import sqlite3

import streamlit as st

import storage


def names(conn: sqlite3.Connection) -> dict[int, str]:
    """Every list, id to name, in the order the reader sees them."""
    return {row["id"]: row["name"] for row in storage.list_lists(conn)}


def choose(column, conn: sqlite3.Connection, label: str, key: str, extra: str | None = None):
    """Draw a list picker and return what was chosen: a list id, or `extra`.

    `extra` is a sentinel offered alongside the real lists, for the page whose
    picker can also mean "a list that doesn't exist yet".

    A list can be deleted while its id is still sitting in the session, which
    Streamlit treats as a selection outside the options; the stale id is dropped
    so the picker falls back to the first list rather than raising.
    """
    options = names(conn)
    offered = list(options) + ([extra] if extra else [])
    if st.session_state.get(key) not in offered:
        st.session_state.pop(key, None)
    return column.selectbox(
        label,
        offered,
        format_func=lambda value: extra if value == extra else options[value],
        key=key,
    )
