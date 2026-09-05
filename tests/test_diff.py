"""Comparing two monitored profiles.

The comparison is pure, so it is tested directly rather than through the
monitor. Profiles are built from the captured NCT03412565 record so the field
names under test are the real ones.
"""

from __future__ import annotations

import pytest

import diff
import medical_affairs


@pytest.fixture
def profile(record) -> dict:
    return medical_affairs.profile(record)


def changed(previous: dict, **moved) -> tuple[dict, dict]:
    """A pair of profiles differing only in the named fields."""
    return previous, {**previous, **moved}


def test_two_identical_profiles_report_nothing(profile):
    assert diff.compare(profile, profile) == []


def test_a_scalar_change_reports_both_values(profile):
    previous, current = changed(profile, enrollment=180)

    assert diff.compare(previous, current) == [
        {"field": "enrollment", "previous": 265, "current": 180}
    ]


def test_a_field_gaining_a_value_reports_the_absence_as_the_previous_value(profile):
    previous, current = changed(profile, whyStopped="Slow accrual")

    assert diff.compare(previous, current) == [
        {"field": "whyStopped", "previous": None, "current": "Slow accrual"}
    ]


def test_several_moved_fields_are_all_reported(profile):
    previous, current = changed(profile, enrollment=180, overallStatus="TERMINATED")

    assert {c["field"] for c in diff.compare(previous, current)} == {
        "enrollment",
        "overallStatus",
    }


def test_a_list_gaining_a_member_is_reported(profile):
    previous, current = changed(
        profile, interventions=profile["interventions"] + ["Pomalidomide"]
    )

    [change] = diff.compare(previous, current)
    assert change["field"] == "interventions"
    assert "Pomalidomide" in change["current"]
    assert "Pomalidomide" not in change["previous"]


def test_a_list_losing_a_member_is_reported(profile):
    previous, current = changed(profile, interventions=profile["interventions"][:-1])

    assert [c["field"] for c in diff.compare(previous, current)] == ["interventions"]


def test_a_reordered_list_is_not_a_change(profile):
    """The registry's ordering carries no meaning, so order alone is not news."""
    previous, current = changed(
        profile, interventions=list(reversed(profile["interventions"]))
    )

    assert diff.compare(previous, current) == []


def test_the_registry_last_updated_date_is_never_reported(profile):
    """It moves by definition whenever anything else does: a circular alert."""
    previous, current = changed(profile, lastUpdatePostDate="2026-01-15")

    assert diff.compare(previous, current) == []


def test_the_results_link_is_never_reported(profile):
    """It is derived from hasResults, so reporting it would duplicate that."""
    previous, current = changed(profile, resultsUrl="https://example.test/other")

    assert diff.compare(previous, current) == []


def test_an_excluded_field_moving_alongside_a_real_change_hides_neither(profile):
    previous, current = changed(
        profile, lastUpdatePostDate="2026-01-15", enrollment=180
    )

    assert [c["field"] for c in diff.compare(previous, current)] == ["enrollment"]


def test_changes_are_reported_in_profile_order(profile):
    """Stable ordering keeps stored rows and rendered rows in step."""
    previous, current = changed(profile, overallStatus="TERMINATED", enrollment=180)
    order = list(profile)

    fields = [c["field"] for c in diff.compare(previous, current)]
    assert fields == sorted(fields, key=order.index)
