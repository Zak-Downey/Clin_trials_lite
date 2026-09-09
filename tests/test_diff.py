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

    def build(
        field, previous, current, at="2026-01-03T00:00:00+00:00",
        synthetic=False, reviewed=False,
    ):
        return {
            "nct_id": "NCT03412565",
            "field": field,
            "previous": previous,
            "current": current,
            "detected_at": at,
            "synthetic": synthetic,
            "reviewed": reviewed,
        }

    return build


def test_the_whole_profile_is_marked_up_not_only_what_moved(profile, change):
    rows = diff.annotate(profile, [change("enrollment", 350, 265)])

    # Every field but a qualifier, which is folded into the value it qualifies
    # rather than standing as a row of its own.
    shown = [f for f in profile if f not in diff.QUALIFIES]
    assert [r["field"] for r in rows] == shown
    assert [r["value"] for r in rows] == [profile[f] for f in shown]


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

# --- clearing what has already been reviewed


def test_a_change_already_reviewed_is_no_longer_marked(profile, change):
    """Highlighting means "new since you last looked", not "moved at some point"."""
    rows = {
        r["field"]: r
        for r in diff.annotate(profile, [change("enrollment", 350, 265, reviewed=True)])
    }

    assert rows["enrollment"]["changed"] is False
    assert rows["enrollment"]["previous"] is None


def test_a_field_that_moved_again_after_a_review_shows_the_newer_move(profile, change):
    rows = {
        r["field"]: r
        for r in diff.annotate(
            profile,
            [
                change("enrollment", 300, 265, at="2026-02-01T00:00:00+00:00"),
                change("enrollment", 350, 300, at="2026-01-01T00:00:00+00:00", reviewed=True),
            ],
        )
    }

    assert rows["enrollment"]["changed"] is True
    assert rows["enrollment"]["previous"] == 300


def test_reviewing_one_field_leaves_another_field_marked(profile, change):
    rows = {
        r["field"]: r
        for r in diff.annotate(
            profile,
            [
                change("enrollment", 350, 265, reviewed=True),
                change("overallStatus", "ACTIVE", "COMPLETED"),
            ],
        )
    }

    assert rows["enrollment"]["changed"] is False
    assert rows["overallStatus"]["changed"] is True


# --- eligibility criteria
#
# The inclusion and exclusion list defines who can enter the study, so an
# amendment widening or narrowing a competitor's target population is exactly
# the kind of move this tool exists to catch.


def test_an_amended_eligibility_criteria_is_reported(profile):
    previous, current = changed(
        profile, eligibilityCriteria="Inclusion Criteria:\n* Aged 18 or over"
    )

    [change] = diff.compare(previous, current)
    assert change["field"] == "eligibilityCriteria"
    assert change["previous"] == profile["eligibilityCriteria"]


# --- what counts as high signal


@pytest.mark.parametrize(
    "field", ["primaryOutcomes", "phases", "eligibilityCriteria"]
)
def test_the_promoted_fields_carry_the_prominence_of_a_slipped_date(profile, field):
    """A moved endpoint, phase or eligible population can matter more to
    competitor monitoring than an edit to the intervention wording."""
    rows = {r["field"]: r for r in diff.annotate(profile, [])}

    assert rows[field]["high_signal"] is True


def test_a_promoted_field_outranks_an_ordinary_one_in_the_order(profile):
    """The overflow of the watchlist's change column drops the last names, so
    a moved endpoint must never be the one dropped for a title typo."""
    ordered = diff.by_signal(["officialTitle", "eligibilityCriteria", "acronym", "phases"])

    assert ordered[:2] == ["eligibilityCriteria", "phases"]


# --- a value and whether it is estimated or actual
#
# A primary completion date going from estimated to actual is one event, and
# the single most informative thing that can happen to that field. Reported as
# a date move and an unrelated type move, it reads as neither.


def test_a_qualifier_gets_no_row_of_its_own(profile):
    fields = [r["field"] for r in diff.annotate(profile, [])]

    assert "primaryCompletionDateType" not in fields
    assert "primaryCompletionDate" in fields


def test_a_date_is_marked_up_beside_whether_it_is_estimated_or_actual(profile):
    rows = {r["field"]: r for r in diff.annotate(profile, [])}

    assert rows["primaryCompletionDate"]["qualifier"] == profile["primaryCompletionDateType"]


def test_a_date_becoming_actual_marks_the_date_itself_as_moved(profile, change):
    """The type moved and the date did not, yet the news is about the date."""
    rows = {
        r["field"]: r
        for r in diff.annotate(
            profile, [change("primaryCompletionDateType", "ESTIMATED", "ACTUAL")]
        )
    }
    row = rows["primaryCompletionDate"]

    assert row["changed"] is True
    # The value it moved from is the value it still holds: only its type moved.
    assert row["previous"] == profile["primaryCompletionDate"]
    assert row["previous_qualifier"] == "ESTIMATED"


def test_a_date_and_its_type_moving_together_are_one_marked_row(profile, change):
    rows = [
        r
        for r in diff.annotate(
            profile,
            [
                change("completionDate", "2024-04-18", "2024-09-30"),
                change("completionDateType", "ESTIMATED", "ACTUAL"),
            ],
        )
        if r["changed"]
    ]

    assert [r["field"] for r in rows] == ["completionDate"]
    assert rows[0]["previous"] == "2024-04-18"
    assert rows[0]["previous_qualifier"] == "ESTIMATED"


def test_an_enrolment_figure_carries_its_type_the_same_way(profile, change):
    rows = {
        r["field"]: r
        for r in diff.annotate(profile, [change("enrollmentType", "ESTIMATED", "ACTUAL")])
    }

    assert rows["enrollment"]["changed"] is True
    assert rows["enrollment"]["previous_qualifier"] == "ESTIMATED"
    assert "enrollmentType" not in rows


def test_a_simulated_type_move_stays_flagged_on_the_row_it_folds_into(profile, change):
    rows = {
        r["field"]: r
        for r in diff.annotate(
            profile,
            [change("completionDateType", "ESTIMATED", "ACTUAL", synthetic=True)],
        )
    }

    assert rows["completionDate"]["synthetic"] is True


def test_a_reviewed_type_move_leaves_the_row_it_folds_into_plain(profile, change):
    rows = {
        r["field"]: r
        for r in diff.annotate(
            profile,
            [change("completionDateType", "ESTIMATED", "ACTUAL", reviewed=True)],
        )
    }

    assert rows["completionDate"]["changed"] is False


def test_a_type_named_alongside_its_value_is_folded_into_one_name():
    assert diff.fold_qualifiers(["completionDate", "completionDateType"]) == ["completionDate"]


def test_a_type_named_on_its_own_is_named_as_its_value():
    assert diff.fold_qualifiers(["enrollmentType"]) == ["enrollment"]


def test_folding_leaves_an_unqualified_field_alone():
    assert diff.fold_qualifiers(["overallStatus", "acronym"]) == ["overallStatus", "acronym"]


# --- the same folding, for a caller holding changes rather than a profile


def test_a_value_and_its_qualifier_moving_together_fold_into_one_move(change, profile):
    folded = diff.fold_moves(
        [
            change("completionDate", "2024-04-18", "2025-04-18"),
            change("completionDateType", "ESTIMATED", "ACTUAL"),
        ],
        profile,
    )

    assert [m["field"] for m in folded] == ["completionDate"]
    assert folded[0]["previous_qualifier"] == "ESTIMATED"
    assert folded[0]["qualifier"] == "ACTUAL"


def test_a_qualifier_that_moved_alone_is_reported_under_its_value(change, profile):
    folded = diff.fold_moves([change("completionDateType", "ESTIMATED", "ACTUAL")], profile)

    assert [m["field"] for m in folded] == ["completionDate"]
    # The value did not move, and stands as the context for the word about it.
    assert folded[0]["previous"] == folded[0]["current"] == profile["completionDate"]


def test_an_unqualified_field_folds_into_itself(change, profile):
    folded = diff.fold_moves([change("overallStatus", "RECRUITING", "TERMINATED")], profile)

    assert [m["field"] for m in folded] == ["overallStatus"]
    assert (folded[0]["previous"], folded[0]["current"]) == ("RECRUITING", "TERMINATED")


def test_a_folded_move_carries_the_change_it_came_from(change, profile):
    recorded = change("overallStatus", "RECRUITING", "TERMINATED", synthetic=True)

    assert diff.fold_moves([recorded], profile)[0]["change"] is recorded
