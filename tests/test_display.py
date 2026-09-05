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


# --- marking changed fields in a rendered profile


@pytest.fixture
def row():
    """One marked-up profile row, shaped as the comparison hands it over."""

    def build(field="enrollment", value=265, changed=False, previous=None,
              high_signal=False, synthetic=False):
        return {
            "field": field,
            "value": value,
            "changed": changed,
            "previous": previous,
            "high_signal": high_signal,
            "synthetic": synthetic,
        }

    return build


def test_an_unchanged_field_renders_plainly(row):
    rendered = display.render_field(row(field="officialTitle", value="A study of things"))

    assert "Official title" in rendered
    assert "A study of things" in rendered
    assert display.HIGHLIGHT not in rendered
    assert display.HIGHLIGHT_HIGH_SIGNAL not in rendered


def test_an_unchanged_high_signal_field_is_not_highlighted(row):
    rendered = display.render_field(row(high_signal=True))

    assert display.HIGHLIGHT_HIGH_SIGNAL not in rendered


def test_a_changed_field_is_highlighted_and_shows_both_values(row):
    rendered = display.render_field(row(changed=True, previous=350))

    assert display.HIGHLIGHT in rendered
    assert "265" in rendered
    assert "350" in rendered


def test_a_changed_high_signal_field_is_more_prominent_than_an_ordinary_one(row):
    ordinary = display.render_field(row(field="acronym", value="X", changed=True, previous="Y"))
    high = display.render_field(row(changed=True, previous=350, high_signal=True))

    assert display.HIGHLIGHT_HIGH_SIGNAL in high
    assert display.HIGHLIGHT_HIGH_SIGNAL not in ordinary
    assert high.startswith("#")
    assert not ordinary.startswith("#")


def test_a_previously_empty_field_shows_its_emptiness_explicitly(row):
    rendered = display.render_field(
        row(field="whyStopped", value="Slow accrual", changed=True, previous=None)
    )

    assert display.EMPTY in rendered
    assert "Slow accrual" in rendered


def test_a_synthetic_change_is_badged_on_the_field(row):
    rendered = display.render_field(row(changed=True, previous=350, synthetic=True))

    assert display.SYNTHETIC in rendered


def test_a_results_url_renders_as_a_link(row):
    rendered = display.render_field(
        row(field="resultsUrl", value="https://clinicaltrials.gov/study/NCT1?tab=results")
    )

    assert "](https://clinicaltrials.gov/study/NCT1?tab=results)" in rendered


def test_no_elapsed_time_is_calculated_for_a_date_change(row):
    rendered = display.render_field(
        row(field="completionDate", value="2024-04-18", changed=True,
            previous="2023-04-18", high_signal=True)
    )

    assert "2024-04-18" in rendered
    assert "2023-04-18" in rendered
    for word in ("days", "months", "years", "later", "earlier", "ago"):
        assert word not in rendered.lower()
