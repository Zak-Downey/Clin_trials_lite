"""Adding a trial to the watchlist, driven through the fetching seam."""

from __future__ import annotations

import urllib.error

import pytest

import monitor
import storage


def test_adding_a_trial_puts_it_on_the_watchlist(conn, fetcher):
    monitor.add(conn, "NCT03412565", fetch=fetcher)

    assert [t["nct_id"] for t in storage.list_trials(conn)] == ["NCT03412565"]


def test_adding_a_trial_records_a_baseline_and_no_changes(conn, fetcher):
    monitor.add(conn, "NCT03412565", fetch=fetcher)

    assert storage.count_snapshots(conn, "NCT03412565") == 1
    assert storage.list_changes(conn) == []


def test_the_baseline_keeps_the_raw_record_not_just_the_profile(conn, fetcher):
    monitor.add(conn, "NCT03412565", fetch=fetcher)

    stored = storage.latest_snapshot(conn, "NCT03412565")["record"]
    # A raw registry field the monitored profile discards entirely.
    assert stored["protocolSection"]["contactsLocationsModule"]["locations"]


def test_the_baseline_drops_the_results_section(conn, fetcher, record):
    record["resultsSection"] = {"big": "payload"}

    monitor.add(conn, "NCT03412565", fetch=fetcher)

    assert "resultsSection" not in storage.latest_snapshot(conn, "NCT03412565")["record"]


def test_a_watched_trial_exposes_its_monitored_profile(conn, fetcher):
    monitor.add(conn, "NCT03412565", fetch=fetcher)

    profile = monitor.profile_of(conn, "NCT03412565")
    assert profile["leadSponsor"] == "Janssen Research & Development, LLC"
    assert profile["overallStatus"] == "COMPLETED"


def test_adding_a_trial_appears_in_the_feed(conn, fetcher):
    monitor.add(conn, "NCT03412565", fetch=fetcher)

    (event,) = monitor.feed(conn)
    assert event["nct_id"] == "NCT03412565"
    assert event["kind"] == "started monitoring"
    assert event["at"]


def test_a_lowercase_id_is_accepted_and_normalised(conn, fetcher):
    assert monitor.add(conn, " nct03412565 ", fetch=fetcher) == "NCT03412565"


def test_adding_the_same_trial_twice_does_not_duplicate_it(conn, fetcher):
    monitor.add(conn, "NCT03412565", fetch=fetcher)

    with pytest.raises(monitor.MonitorError, match="already on the watchlist"):
        monitor.add(conn, "NCT03412565", fetch=fetcher)

    assert len(storage.list_trials(conn)) == 1
    assert storage.count_snapshots(conn, "NCT03412565") == 1


def test_a_malformed_id_is_rejected_without_fetching(conn, fetcher):
    with pytest.raises(monitor.MonitorError, match="not an NCT ID"):
        monitor.add(conn, "banana", fetch=fetcher)

    assert fetcher.calls == []
    assert storage.list_trials(conn) == []


def test_an_unknown_id_leaves_stored_state_untouched(conn):
    def not_found(nct_id):
        raise urllib.error.HTTPError(
            url="https://clinicaltrials.gov", code=404, msg="Not Found", hdrs=None, fp=None
        )

    with pytest.raises(monitor.MonitorError, match="not found"):
        monitor.add(conn, "NCT99999999", fetch=not_found)

    assert storage.list_trials(conn) == []
    assert storage.count_snapshots(conn, "NCT99999999") == 0


def test_an_unreachable_api_leaves_stored_state_untouched(conn):
    def unreachable(nct_id):
        raise urllib.error.URLError("connection refused")

    with pytest.raises(monitor.MonitorError, match="Could not reach"):
        monitor.add(conn, "NCT03412565", fetch=unreachable)

    assert storage.list_trials(conn) == []


def test_an_unexpected_fetch_failure_is_reported_not_raised_raw(conn):
    def broken(nct_id):
        raise TimeoutError("timed out")

    with pytest.raises(monitor.MonitorError, match="Could not fetch"):
        monitor.add(conn, "NCT03412565", fetch=broken)

    assert storage.list_trials(conn) == []


def test_a_record_without_a_protocol_section_is_rejected(conn):
    with pytest.raises(monitor.MonitorError, match="no usable record"):
        monitor.add(conn, "NCT03412565", fetch=lambda nct_id: {})

    assert storage.list_trials(conn) == []


def test_a_failed_add_does_not_disturb_trials_already_watched(conn, fetcher):
    monitor.add(conn, "NCT03412565", fetch=fetcher)

    def unreachable(nct_id):
        raise urllib.error.URLError("connection refused")

    with pytest.raises(monitor.MonitorError):
        monitor.add(conn, "NCT00000000", fetch=unreachable)

    assert [t["nct_id"] for t in storage.list_trials(conn)] == ["NCT03412565"]
