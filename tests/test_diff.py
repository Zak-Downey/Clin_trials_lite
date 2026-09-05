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


# --- marking a profile up for review


@pytest.fixture
def change():
    """One recorded change, shaped as storage returns it."""

    def build(field, previous, current, at="2026-01-03T00:00:00+00:00", synthetic=False):
        return {
            "nct_id": "NCT03412565",
            "field": field,
            "previous": previous,
            "current": current,
            "detected_at": at,
            "synthetic": synthetic,
        }

    return build


def test_the_whole_profile_is_marked_up_not_only_what_moved(profile, change):
    rows = diff.annotate(profile, [change("enrollment", 350, 265)])

    assert [r["field"] for r in rows] == list(profile)
    assert [r["value"] for r in rows] == list(profile.values())


def test_a_field_that_did_not_move_is_not_marked_changed(profile, change):
    rows = {r["field"]: r for r in diff.annotate(profile, [change("enrollment", 350, 265)])}

    assert rows["briefTitle"]["changed"] is False
    assert rows["briefTitle"]["previous"] is None


def test_a_field_that_moved_carries_the_value_it_moved_from(profile, change):
    rows = {r["field"]: r for r in diff.annotate(profile, [change("enrollment", 350, 265)])}

    assert rows["enrollment"]["changed"] is True
    assert rows["enrollment"]["previous"] == 350
    assert rows["enrollment"]["value"] == profile["enrollment"]


def test_a_field_that_moved_twice_shows_the_immediately_preceding_value(profile, change):
    """Not the value at the start of the chain: history is a later feature."""
    rows = {
        r["field"]: r
        for r in diff.annotate(
            profile,
            [
                change("enrollment", 300, 265, at="2026-02-01T00:00:00+00:00"),
                change("enrollment", 350, 300, at="2026-01-01T00:00:00+00:00"),
            ],
        )
    }

    assert rows["enrollment"]["previous"] == 300


def test_a_previously_empty_field_is_marked_changed_with_an_empty_previous(profile, change):
    rows = {
        r["field"]: r
        for r in diff.annotate(profile, [change("whyStopped", None, "Slow accrual")])
    }

    assert rows["whyStopped"]["changed"] is True
    assert rows["whyStopped"]["previous"] is None


def test_high_signal_fields_are_designated_as_such(profile, change):
    rows = {r["field"]: r for r in diff.annotate(profile, [])}

    assert rows["enrollment"]["high_signal"] is True
    assert rows["overallStatus"]["high_signal"] is True
    assert rows["completionDate"]["high_signal"] is True
    assert rows["officialTitle"]["high_signal"] is False


def test_every_high_signal_field_is_a_real_profile_field(profile):
    assert set(diff.HIGH_SIGNAL) <= set(profile)


def test_a_field_never_reported_as_changed_is_never_marked_changed(profile, change):
    rows = {
        r["field"]: r
        for r in diff.annotate(profile, [change("lastUpdatePostDate", "2025-01-01", "2025-04-29")])
    }

    assert rows["lastUpdatePostDate"]["changed"] is False


def test_a_synthetic_change_stays_flagged_on_the_marked_up_row(profile, change):
    rows = {
        r["field"]: r
        for r in diff.annotate(profile, [change("enrollment", 350, 265, synthetic=True)])
    }

    assert rows["enrollment"]["synthetic"] is True


def test_a_trial_with_no_changes_is_marked_up_with_nothing_highlighted(profile):
    rows = diff.annotate(profile, [])

    assert not any(r["changed"] for r in rows)


def test_two_moves_recorded_in_the_same_second_resolve_to_the_newer(profile, change):
    """Detection times are only second-precise, so the order storage returns
    them in -- newest first -- decides which of a tie is shown."""
    rows = {
        r["field"]: r
        for r in diff.annotate(
            profile,
            [
                change("enrollment", 300, 265, at="2026-02-01T00:00:00+00:00"),
                change("enrollment", 350, 300, at="2026-02-01T00:00:00+00:00"),
            ],
        )
    }

    assert rows["enrollment"]["previous"] == 300
