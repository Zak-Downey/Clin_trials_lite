"""Re-checking watched trials.

Every test drives the real SQLite schema through the fetching seam, so nothing
here touches the network. A check is deliberately cheap: when the registry's own
last-updated stamp hasn't moved, nothing is re-stored and nothing is compared.
"""

from __future__ import annotations

import copy
import urllib.error

import pytest

import monitor
import storage


def bumped(record: dict, date: str = "2026-01-15") -> dict:
    """A copy of a record whose registry last-updated stamp has moved on."""
    moved = copy.deepcopy(record)
    moved["protocolSection"]["statusModule"]["lastUpdatePostDateStruct"]["date"] = date
    return moved


@pytest.fixture
def watched(conn, record, fetcher):
    """One trial already on the watchlist, baselined at a known time."""
    monitor.add(conn, "NCT03412565", fetch=fetcher, when="2026-01-01T00:00:00+00:00")
    return conn


# --- the cheap pre-check


def test_an_untouched_registry_record_reports_no_changes(watched, fetcher):
    result = monitor.check(watched, "NCT03412565", fetch=fetcher)

    assert result["outcome"] == "unchanged"
    assert result["nct_id"] == "NCT03412565"


def test_an_untouched_record_is_not_stored_again(watched, fetcher):
    monitor.check(watched, "NCT03412565", fetch=fetcher)
    monitor.check(watched, "NCT03412565", fetch=fetcher)

    assert storage.count_snapshots(watched, "NCT03412565") == 1


def test_a_moved_registry_stamp_stores_a_fresh_snapshot(watched, record, make_fetcher):
    fetch = make_fetcher({"NCT03412565": bumped(record)})

    result = monitor.check(watched, "NCT03412565", fetch=fetch)

    assert result["outcome"] == "updated"
    assert storage.count_snapshots(watched, "NCT03412565") == 2
    assert monitor.profile_of(watched, "NCT03412565")["lastUpdatePostDate"] == "2026-01-15"


# --- last checked


def test_last_checked_updates_when_nothing_changed(watched, fetcher):
    monitor.check(watched, "NCT03412565", fetch=fetcher, when="2026-02-02T09:00:00+00:00")

    trial = storage.get_trial(watched, "NCT03412565")
    assert trial["last_checked"] == "2026-02-02T09:00:00+00:00"


def test_last_checked_updates_when_the_record_moved(watched, record, make_fetcher):
    fetch = make_fetcher({"NCT03412565": bumped(record)})

    monitor.check(watched, "NCT03412565", fetch=fetch, when="2026-02-02T09:00:00+00:00")

    trial = storage.get_trial(watched, "NCT03412565")
    assert trial["last_checked"] == "2026-02-02T09:00:00+00:00"


def test_checking_a_trial_that_is_not_watched_is_refused(conn, fetcher):
    with pytest.raises(monitor.MonitorError, match="not on the watchlist"):
        monitor.check(conn, "NCT03412565", fetch=fetcher)

    assert fetcher.calls == []


# --- checking the whole watchlist


def test_every_watched_trial_is_checked(conn, fetcher):
    monitor.add(conn, "NCT03412565", fetch=fetcher, when="2026-01-01T00:00:00+00:00")
    monitor.add(conn, "NCT00000001", fetch=fetcher, when="2026-01-02T00:00:00+00:00")

    results = list(monitor.check_all(conn, fetch=fetcher, pause=0))

    assert [r["nct_id"] for r in results] == ["NCT03412565", "NCT00000001"]
    assert all(r["outcome"] == "unchanged" for r in results)


def test_one_trial_failing_does_not_abort_the_rest(conn, record, fetcher, make_fetcher):
    for offset, nct in enumerate(["NCT00000001", "NCT00000002", "NCT00000003"]):
        monitor.add(conn, nct, fetch=fetcher, when=f"2026-01-0{offset + 1}T00:00:00+00:00")
    fetch = make_fetcher(
        {"NCT00000001": record, "NCT00000003": record},
        failures={"NCT00000002": urllib.error.URLError("connection refused")},
    )

    first, failed, last = list(monitor.check_all(conn, fetch=fetch, pause=0))

    assert failed["nct_id"] == "NCT00000002"
    assert failed["outcome"] == "error"
    assert "Could not reach ClinicalTrials.gov" in failed["detail"]
    assert first["outcome"] == "unchanged"
    assert last["outcome"] == "unchanged"


def test_a_failed_check_leaves_the_trials_last_checked_alone(conn, fetcher, make_fetcher):
    monitor.add(conn, "NCT03412565", fetch=fetcher, when="2026-01-01T00:00:00+00:00")
    fetch = make_fetcher(failures={"NCT03412565": urllib.error.URLError("down")})

    list(monitor.check_all(conn, fetch=fetch, pause=0))

    trial = storage.get_trial(conn, "NCT03412565")
    assert trial["last_checked"] == "2026-01-01T00:00:00+00:00"


def test_trials_are_checked_one_at_a_time_with_a_pause_between(conn, fetcher, monkeypatch):
    monitor.add(conn, "NCT03412565", fetch=fetcher, when="2026-01-01T00:00:00+00:00")
    monitor.add(conn, "NCT00000001", fetch=fetcher, when="2026-01-02T00:00:00+00:00")
    pauses = []
    monkeypatch.setattr(monitor.time, "sleep", pauses.append)

    list(monitor.check_all(conn, fetch=fetcher))

    # Two trials, one gap between them -- and no pause before the first.
    assert pauses == [monitor.PAUSE]


def test_checking_an_empty_watchlist_yields_nothing(conn, fetcher):
    assert list(monitor.check_all(conn, fetch=fetcher, pause=0)) == []
    assert fetcher.calls == []


# --- what the analyst is told about a completed run


def test_a_clean_run_is_reported_as_no_changes():
    results = [{"nct_id": "NCT03412565", "outcome": "unchanged", "detail": "No changes."}]

    summary = monitor.summarise(results)

    assert summary["level"] == "success"
    assert summary["message"] == "Checked 1 trial — no changes."


def test_a_run_with_a_failure_is_never_reported_as_good_news():
    results = [
        {"nct_id": "NCT00000001", "outcome": "unchanged", "detail": "No changes."},
        {"nct_id": "NCT00000002", "outcome": "error", "detail": "Could not reach it."},
    ]

    summary = monitor.summarise(results)

    assert summary["level"] == "warning"
    assert "no changes" not in summary["message"]
    assert "1 could not be reached" in summary["message"]
    assert [r["nct_id"] for r in summary["failed"]] == ["NCT00000002"]


def test_a_revised_record_is_not_reported_by_its_last_updated_date(watched, record, make_fetcher):
    """The registry's own last-updated stamp moves whenever anything else does,
    so reporting it back would be a circular alert."""
    fetch = make_fetcher({"NCT03412565": bumped(record, "2026-03-03")})

    result = monitor.check(watched, "NCT03412565", fetch=fetch)

    assert "2026-03-03" not in result["detail"]
    assert monitor.summarise([result])["level"] == "warning"
