"""What the watchlist table is built from.

The table is one row per trial carrying the study's identity and what last
moved on it. Both are derived here, in monitor, so the page stays a thin view
and the derivation can be tested without running Streamlit.
"""

from __future__ import annotations

import copy

import pytest

import monitor
import storage


@pytest.fixture
def watched(conn, fetcher):
    """One watched trial, seeded through the fetching seam."""
    monitor.add(conn, "NCT03412565", fetch=fetcher)
    return conn


def moved(conn, nct_id, field, when, previous=None, current=None, synthetic=False):
    """Record one field as having moved, as a check would."""
    storage.add_change(
        conn,
        nct_id,
        {"field": field, "previous": previous, "current": current},
        when,
        synthetic=synthetic,
    )


# --- what moved the last time the trial changed


def test_a_trial_that_has_never_changed_reports_no_last_change(watched):
    assert monitor.last_change(watched, "NCT03412565") is None


def test_every_field_from_the_newest_detection_is_reported_not_only_one(watched):
    moved(watched, "NCT03412565", "enrollment", "2026-09-05T10:00:00+00:00")
    moved(watched, "NCT03412565", "completionDate", "2026-09-05T10:00:00+00:00")

    change = monitor.last_change(watched, "NCT03412565")

    assert set(change["fields"]) == {"enrollment", "completionDate"}
    assert change["at"] == "2026-09-05T10:00:00+00:00"


def test_an_unread_field_from_an_earlier_check_is_still_reported(watched):
    """The column is what an analyst scans, so it names everything outstanding.

    A completion date that slipped on Monday must not drop out of the column
    when a title typo is corrected on Wednesday.
    """
    moved(watched, "NCT03412565", "completionDate", "2026-08-01T10:00:00+00:00")
    moved(watched, "NCT03412565", "officialTitle", "2026-09-05T10:00:00+00:00")

    change = monitor.last_change(watched, "NCT03412565")

    assert set(change["fields"]) == {"completionDate", "officialTitle"}
    # The newest of the moves shown, so the column's date is not stale.
    assert change["at"] == "2026-09-05T10:00:00+00:00"


def test_a_field_read_earlier_drops_out_once_something_newer_is_outstanding(watched):
    moved(watched, "NCT03412565", "overallStatus", "2026-08-01T10:00:00+00:00")
    storage.mark_reviewed(watched, "NCT03412565")
    moved(watched, "NCT03412565", "enrollment", "2026-09-05T10:00:00+00:00")

    change = monitor.last_change(watched, "NCT03412565")

    assert change["fields"] == ["enrollment"]


def test_the_same_field_moving_twice_is_named_once(watched):
    moved(watched, "NCT03412565", "enrollment", "2026-08-01T10:00:00+00:00")
    moved(watched, "NCT03412565", "enrollment", "2026-09-05T10:00:00+00:00")

    assert monitor.last_change(watched, "NCT03412565")["fields"] == ["enrollment"]


def test_outstanding_fields_are_still_ordered_high_signal_first(watched):
    moved(watched, "NCT03412565", "acronym", "2026-08-01T10:00:00+00:00")
    moved(watched, "NCT03412565", "completionDate", "2026-09-05T10:00:00+00:00")

    change = monitor.last_change(watched, "NCT03412565")

    assert change["fields"][0] == "completionDate"


def test_high_signal_fields_are_listed_before_ordinary_ones(watched):
    at = "2026-09-05T10:00:00+00:00"
    moved(watched, "NCT03412565", "acronym", at)
    moved(watched, "NCT03412565", "officialTitle", at)
    moved(watched, "NCT03412565", "completionDate", at)

    change = monitor.last_change(watched, "NCT03412565")

    assert change["fields"][0] == "completionDate"


def test_a_reviewed_change_is_still_reported_as_what_last_moved(watched):
    moved(watched, "NCT03412565", "enrollment", "2026-09-05T10:00:00+00:00")
    storage.mark_reviewed(watched, "NCT03412565")

    change = monitor.last_change(watched, "NCT03412565")

    assert change["fields"] == ["enrollment"]


def test_once_everything_is_read_only_the_newest_check_is_reported(watched):
    """"What has changed on this trial" stays a fair question once the news is
    old, so a fully reviewed trial falls back to naming its last move."""
    moved(watched, "NCT03412565", "overallStatus", "2026-08-01T10:00:00+00:00")
    moved(watched, "NCT03412565", "enrollment", "2026-09-05T10:00:00+00:00")
    storage.mark_reviewed(watched, "NCT03412565")

    change = monitor.last_change(watched, "NCT03412565")

    assert change["fields"] == ["enrollment"]
    assert change["at"] == "2026-09-05T10:00:00+00:00"


def test_a_simulated_detection_is_reported_as_simulated(watched):
    at = "2026-09-05T10:00:00+00:00"
    moved(watched, "NCT03412565", "enrollment", at)
    moved(watched, "NCT03412565", "completionDate", at, synthetic=True)

    assert monitor.last_change(watched, "NCT03412565")["synthetic"] is True


def test_a_genuine_detection_is_not_reported_as_simulated(watched):
    moved(watched, "NCT03412565", "enrollment", "2026-09-05T10:00:00+00:00")

    assert monitor.last_change(watched, "NCT03412565")["synthetic"] is False


# --- the row behind each line of the table


def test_there_is_one_row_per_watched_trial_in_watchlist_order(conn, record, make_fetcher):
    other = copy.deepcopy(record)
    other["protocolSection"]["identificationModule"]["nctId"] = "NCT00000001"
    monitor.add(conn, "NCT03412565", fetch=make_fetcher(default=record))
    monitor.add(conn, "NCT00000001", fetch=make_fetcher(default=other))

    rows = monitor.watchlist(conn)

    assert [r["nct_id"] for r in rows] == [t["nct_id"] for t in storage.list_trials(conn)]


def test_a_row_carries_the_facts_that_identify_the_study(watched):
    row = monitor.watchlist(watched)[0]

    assert row["nct_id"] == "NCT03412565"
    assert row["sponsor"] == "Janssen Research & Development, LLC"
    assert row["title"]
    assert row["phases"]
    assert row["conditions"]
    assert row["interventions"]
    assert row["status"] == "COMPLETED"


def test_an_intervention_repeated_once_per_arm_appears_once(conn, record, make_fetcher):
    repeated = copy.deepcopy(record)
    interventions = repeated["protocolSection"]["armsInterventionsModule"]["interventions"]
    interventions.append(copy.deepcopy(interventions[0]))
    monitor.add(conn, "NCT03412565", fetch=make_fetcher(default=repeated))

    names = monitor.watchlist(conn)[0]["interventions"]

    assert len(names) == len(set(names))


def test_a_row_says_whether_anything_on_it_is_still_unread(watched):
    moved(watched, "NCT03412565", "enrollment", "2026-09-05T10:00:00+00:00")

    assert monitor.watchlist(watched)[0]["unreviewed"] == 1

    storage.mark_reviewed(watched, "NCT03412565")

    assert monitor.watchlist(watched)[0]["unreviewed"] == 0


def test_a_row_carries_what_last_moved_on_that_trial(watched):
    moved(watched, "NCT03412565", "enrollment", "2026-09-05T10:00:00+00:00")

    assert monitor.watchlist(watched)[0]["change"]["fields"] == ["enrollment"]


def test_a_row_for_a_trial_that_has_never_changed_carries_no_change(watched):
    assert monitor.watchlist(watched)[0]["change"] is None


def test_a_row_carries_the_registrys_own_revision_date(watched):
    """When the sponsor revised the record, which is not when we noticed."""
    assert monitor.watchlist(watched)[0]["registry_updated"] == "2025-04-29"
