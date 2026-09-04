"""Formatting helpers used by the page."""

from __future__ import annotations

import pytest

import display


@pytest.mark.parametrize(
    "key, expected",
    [
        ("leadSponsor", "Lead sponsor"),
        ("primaryCompletionDate", "Primary completion date"),
        ("phases", "Phases"),
    ],
)
def test_keys_render_as_readable_labels(key, expected):
    assert display.label(key) == expected


def test_lists_render_comma_separated():
    assert display.show(["Daratumumab", "Bortezomib"]) == "Daratumumab, Bortezomib"


@pytest.mark.parametrize("value", [None, "", []])
def test_empty_values_render_explicitly_rather_than_blank(value):
    assert display.show(value) == display.EMPTY


@pytest.mark.parametrize("value, expected", [(0, "0"), (False, "False"), (265, "265")])
def test_falsy_but_real_values_are_not_mistaken_for_empty(value, expected):
    assert display.show(value) == expected
