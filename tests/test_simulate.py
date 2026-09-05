"""Simulating a change on a trial that will never really change again.

The first test case is completed, so the alerting path can only be demonstrated
by altering what we *stored* and letting the ordinary check find the difference
against the live record. These tests hold that line: the simulator writes
history, never a fake API response, and everything it writes is marked
synthetic so it can be removed with certainty.
"""

from __future__ import annotations

import copy
import json

import pytest

import medical_affairs
import monitor
import simulate
import storage


@pytest.fixture
def watched(conn, record, fetcher):
    """One trial already on the watchlist, baselined at a known time."""
    monitor.add(conn, "NCT03412565", fetch=fetcher, when="2026-01-01T00:00:00+00:00")
    return conn


@pytest.fixture
def simulated(watched):
    """A trial whose stored history has been altered, ready to be checked."""
    simulate.rewind(watched, "NCT03412565", when="2026-01-02T00:00:00+00:00")
    return watched


# --- what the simulator does to stored history


def test_simulating_reports_the_fields_it_moved(watched):
    result = simulate.rewind(watched, "NCT03412565")

    assert "enrollment" in result["fields"]
    assert "enrollment" in result["detail"]
    assert "lastUpdatePostDate" not in result["fields"]


def test_simulating_rewrites_the_stored_profile(watched):
    before = monitor.profile_of(watched, "NCT03412565")

    simulate.rewind(watched, "NCT03412565")

    after = monitor.profile_of(watched, "NCT03412565")
    assert after["enrollment"] != before["enrollment"]
    assert after["completionDate"] != before["completionDate"]
    assert after["interventions"] != before["interventions"]


def test_simulating_leaves_the_earlier_history_in_place(watched):
    """It adds a new stored state rather than editing the baseline away."""
    simulate.rewind(watched, "NCT03412565")

    assert storage.count_snapshots(watched, "NCT03412565") == 2


def test_simulating_an_unwatched_trial_is_refused(conn):
    with pytest.raises(monitor.MonitorError, match="not on the watchlist"):
        simulate.rewind(conn, "NCT03412565")


# --- detection through the ordinary check


def test_the_next_check_detects_the_simulated_difference(simulated, fetcher):
    result = monitor.check(simulated, "NCT03412565", fetch=fetcher)

    assert result["outcome"] == "updated"
    assert result["changes"] >= 3


def test_each_moved_field_is_recorded_with_both_values_and_a_time(simulated, fetcher, record):
    live = medical_affairs.profile(record)

    monitor.check(simulated, "NCT03412565", fetch=fetcher, when="2026-01-03T00:00:00+00:00")

    changes = {c["field"]: c for c in storage.list_changes(simulated)}
    assert changes["enrollment"]["current"] == live["enrollment"]
    assert changes["enrollment"]["previous"] != live["enrollment"]
    assert changes["enrollment"]["detected_at"] == "2026-01-03T00:00:00+00:00"


def test_the_registry_last_updated_date_is_not_recorded_as_a_change(simulated, fetcher):
    monitor.check(simulated, "NCT03412565", fetch=fetcher)

    fields = [c["field"] for c in storage.list_changes(simulated)]
    assert "lastUpdatePostDate" not in fields
    assert "resultsUrl" not in fields


def test_checking_twice_does_not_record_the_same_change_again(simulated, fetcher):
    monitor.check(simulated, "NCT03412565", fetch=fetcher)
    before = len(storage.list_changes(simulated))

    monitor.check(simulated, "NCT03412565", fetch=fetcher)

    assert len(storage.list_changes(simulated)) == before


# --- the feed


def test_a_changed_trial_produces_one_feed_entry_naming_the_field_count(simulated, fetcher):
    """A sponsor revising fifteen fields at once is one entry, not fifteen."""
    monitor.check(simulated, "NCT03412565", fetch=fetcher, when="2026-01-03T00:00:00+00:00")

    entries = [e for e in monitor.feed(simulated) if "changed" in e["kind"]]
    assert len(entries) == 1
    assert entries[0]["nct_id"] == "NCT03412565"
    assert entries[0]["kind"] == "3 fields changed"
    assert entries[0]["at"] == "2026-01-03T00:00:00+00:00"


def test_the_feed_is_most_recent_first(simulated, fetcher):
    monitor.check(simulated, "NCT03412565", fetch=fetcher, when="2026-01-03T00:00:00+00:00")

    stamps = [e["at"] for e in monitor.feed(simulated)]
    assert stamps == sorted(stamps, reverse=True)


# --- synthetic marking and cleanup


def test_the_snapshot_the_simulator_writes_is_marked_synthetic(simulated):
    rows = simulated.execute("SELECT synthetic FROM snapshots ORDER BY id").fetchall()
    assert [r["synthetic"] for r in rows] == [0, 1]


def test_changes_detected_against_simulated_history_are_marked_synthetic(simulated, fetcher):
    monitor.check(simulated, "NCT03412565", fetch=fetcher)

    changes = storage.list_changes(simulated)
    assert changes
    assert all(c["synthetic"] for c in changes)


def test_a_feed_entry_for_simulated_changes_is_flagged(simulated, fetcher):
    monitor.check(simulated, "NCT03412565", fetch=fetcher)

    entries = [e for e in monitor.feed(simulated) if "changed" in e["kind"]]
    assert entries[0]["synthetic"] is True


def test_stored_values_carry_no_synthetic_marker_text(simulated, fetcher):
    """The flag is a column. Marker text inside a value would corrupt the
    baseline a later genuine change is compared against."""
    monitor.check(simulated, "NCT03412565", fetch=fetcher)

    # The flag itself is a column, so only the values are examined here.
    records = [r["record"] for r in simulated.execute("SELECT record FROM snapshots")]
    values = [[c["previous"], c["current"]] for c in storage.list_changes(simulated)]
    stored = json.dumps(records + values).lower()
    assert "synthetic" not in stored
    assert "simulated" not in stored


def test_all_synthetic_data_is_removed_in_one_operation(simulated, fetcher):
    monitor.check(simulated, "NCT03412565", fetch=fetcher)

    removed = storage.delete_synthetic(simulated)

    assert removed
    assert storage.list_changes(simulated) == []
    left = simulated.execute("SELECT synthetic FROM snapshots").fetchall()
    assert [r["synthetic"] for r in left] == [0, 0]


def test_deleting_synthetic_data_leaves_real_data_intact(simulated, fetcher, record):
    monitor.check(simulated, "NCT03412565", fetch=fetcher)

    storage.delete_synthetic(simulated)

    assert storage.get_trial(simulated, "NCT03412565") is not None
    baseline = monitor.profile_of(simulated, "NCT03412565")
    assert baseline["enrollment"] == medical_affairs.profile(record)["enrollment"]


def test_deleting_synthetic_data_when_there_is_none_changes_nothing(watched, fetcher):
    monitor.check(watched, "NCT03412565", fetch=fetcher)

    assert storage.delete_synthetic(watched) == 0
    assert storage.count_snapshots(watched, "NCT03412565") == 1


def test_a_trial_is_flagged_while_it_is_showing_simulated_data(simulated, fetcher):
    assert storage.is_synthetic(simulated, "NCT03412565") is True

    monitor.check(simulated, "NCT03412565", fetch=fetcher)
    assert storage.is_synthetic(simulated, "NCT03412565") is True

    storage.delete_synthetic(simulated)
    assert storage.is_synthetic(simulated, "NCT03412565") is False


def test_a_trial_that_was_never_simulated_is_not_flagged(watched):
    assert storage.is_synthetic(watched, "NCT03412565") is False


def test_a_real_change_after_a_simulated_one_is_recorded_as_real(
    simulated, fetcher, record, make_fetcher
):
    """The flag follows the baseline a change was found against, so a genuine
    revision arriving later is not tarred by an earlier simulation -- and
    survives the cleanup that removes the simulated ones."""
    monitor.check(simulated, "NCT03412565", fetch=fetcher)

    revised = copy.deepcopy(record)
    revised["protocolSection"]["statusModule"]["lastUpdatePostDateStruct"]["date"] = "2026-06-01"
    revised["protocolSection"]["designModule"]["enrollmentInfo"]["count"] = 999
    monitor.check(simulated, "NCT03412565", fetch=make_fetcher({"NCT03412565": revised}))

    real = [c for c in storage.list_changes(simulated) if not c["synthetic"]]
    assert [c["field"] for c in real] == ["enrollment"]
    assert real[0]["current"] == 999

    # Still flagged, because the simulated rows are still there to be seen.
    assert storage.is_synthetic(simulated, "NCT03412565") is True

    storage.delete_synthetic(simulated)

    assert storage.is_synthetic(simulated, "NCT03412565") is False
    assert [c["field"] for c in storage.list_changes(simulated)] == ["enrollment"]
