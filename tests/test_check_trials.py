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

    assert result["outcome"] == "no_monitored_change"
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


# --- a revision that moved nothing monitored


def test_a_revision_outside_what_is_monitored_is_not_reported_as_untouched(
    watched, record, make_fetcher
):
    """Two different facts, told apart: nobody edited the record, and somebody
    edited a part of it this tool has chosen not to watch."""
    fetch = make_fetcher({"NCT03412565": bumped(record)})

    result = monitor.check(watched, "NCT03412565", fetch=fetch)

    assert result["outcome"] == "no_monitored_change"
    assert result["changes"] == 0
    assert "no monitored field moved" in result["detail"]


def test_a_record_stating_no_revision_date_is_not_called_revised(conn, record, make_fetcher):
    """An absent stamp is evidence of nothing. Saying "the sponsor revised
    this" on the strength of a missing date would be an invented fact."""
    silent = copy.deepcopy(record)
    del silent["protocolSection"]["statusModule"]["lastUpdatePostDateStruct"]
    fetch = make_fetcher(default=silent)
    monitor.add(conn, "NCT03412565", fetch=fetch, when="2026-01-01T00:00:00+00:00")

    result = monitor.check(conn, "NCT03412565", fetch=fetch)

    assert result["outcome"] == "unchanged"
    assert result["detail"] == "No changes."


# --- forcing a full comparison


def test_a_forced_check_compares_every_field_despite_an_untouched_stamp(
    watched, record, make_fetcher
):
    """After the monitored profile's extraction changes, every stored profile
    is stale and the registry's stamp will never say so."""
    edited = copy.deepcopy(record)
    edited["protocolSection"]["designModule"]["enrollmentInfo"]["count"] = 999

    result = monitor.check(watched, "NCT03412565", fetch=make_fetcher(default=edited), force=True)

    assert result["outcome"] == "updated"
    assert result["changes"] == 1
    assert [c["field"] for c in storage.list_changes(watched, "NCT03412565")] == ["enrollment"]


def test_an_unforced_check_of_the_same_record_finds_nothing(watched, record, make_fetcher):
    edited = copy.deepcopy(record)
    edited["protocolSection"]["designModule"]["enrollmentInfo"]["count"] = 999

    result = monitor.check(watched, "NCT03412565", fetch=make_fetcher(default=edited))

    assert result["outcome"] == "unchanged"
    assert storage.list_changes(watched, "NCT03412565") == []


def test_a_forced_check_that_finds_nothing_says_the_registry_was_untouched(watched, fetcher):
    result = monitor.check(watched, "NCT03412565", fetch=fetcher, force=True)

    assert result["outcome"] == "unchanged"
    assert result["detail"] == "No changes."


def test_a_forced_run_forces_every_trial_in_it(conn, record, fetcher, make_fetcher):
    monitor.add(conn, "NCT03412565", fetch=fetcher, when="2026-01-01T00:00:00+00:00")
    monitor.add(conn, "NCT00000001", fetch=fetcher, when="2026-01-02T00:00:00+00:00")
    edited = copy.deepcopy(record)
    edited["protocolSection"]["designModule"]["enrollmentInfo"]["count"] = 999

    results = list(
        monitor.check_all(conn, fetch=make_fetcher(default=edited), pause=0, force=True)
    )

    assert [r["outcome"] for r in results] == ["updated", "updated"]


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


def test_a_revision_outside_what_is_monitored_reaches_the_end_of_run_summary():
    results = [
        {"nct_id": "NCT00000001", "outcome": "unchanged", "detail": "No changes."},
        {
            "nct_id": "NCT00000002",
            "outcome": "no_monitored_change",
            "detail": "The registry record has been revised, but no monitored field moved.",
        },
    ]

    summary = monitor.summarise(results)

    assert summary["level"] == "info"
    assert "no monitored field moved" in summary["message"]
    assert [r["nct_id"] for r in summary["unmonitored"]] == ["NCT00000002"]


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
    # Still reported -- just not as a monitored field having moved.
    assert result["outcome"] == "no_monitored_change"
    assert "no changes" not in monitor.summarise([result])["message"]


# --- the marked-up profile the page reads


def revised(record: dict, count: int, date: str) -> dict:
    """A record whose enrolment has moved, and whose registry stamp says so."""
    moved = bumped(record, date)
    moved["protocolSection"]["designModule"]["enrollmentInfo"]["count"] = count
    return moved


def test_a_trial_with_no_changes_is_marked_up_with_nothing_highlighted(watched):
    marked = monitor.marked_profile(watched, "NCT03412565")

    assert marked["profile"]["enrollment"]
    assert not any(row["changed"] for row in marked["rows"])


def test_a_changed_field_is_marked_up_with_the_value_it_moved_from(
    watched, record, make_fetcher
):
    monitor.check(
        watched,
        "NCT03412565",
        fetch=make_fetcher(default=revised(record, 180, "2026-01-15")),
        when="2026-01-15T00:00:00+00:00",
    )

    rows = {r["field"]: r for r in monitor.marked_profile(watched, "NCT03412565")["rows"]}
    assert rows["enrollment"]["changed"] is True
    assert rows["enrollment"]["value"] == 180
    assert rows["enrollment"]["previous"] == 265  # the registry's own figure
    assert rows["briefTitle"]["changed"] is False


def test_a_field_that_moved_twice_is_marked_up_from_the_most_recent_move(
    watched, record, make_fetcher
):
    """Two unreviewed moves each write a row; the page shows the later one."""
    monitor.check(
        watched,
        "NCT03412565",
        fetch=make_fetcher(default=revised(record, 300, "2026-01-15")),
        when="2026-01-15T00:00:00+00:00",
    )
    monitor.check(
        watched,
        "NCT03412565",
        fetch=make_fetcher(default=revised(record, 180, "2026-02-15")),
        when="2026-02-15T00:00:00+00:00",
    )

    assert len(storage.list_changes(watched, "NCT03412565")) == 2
    rows = {r["field"]: r for r in monitor.marked_profile(watched, "NCT03412565")["rows"]}
    assert rows["enrollment"]["previous"] == 300
    assert rows["enrollment"]["value"] == 180


# --- marking a trial reviewed


@pytest.fixture
def changed_trial(watched, record, make_fetcher):
    """A watched trial carrying one detected, unreviewed change."""
    monitor.check(
        watched,
        "NCT03412565",
        fetch=make_fetcher(default=revised(record, 180, "2026-01-15")),
        when="2026-01-15T00:00:00+00:00",
    )
    return watched


def marked(conn, nct_id="NCT03412565") -> dict:
    return {r["field"]: r for r in monitor.marked_profile(conn, nct_id)["rows"]}


def test_reviewing_a_trial_clears_its_highlighting(changed_trial):
    monitor.review(changed_trial, "NCT03412565", when="2026-01-16T00:00:00+00:00")

    assert not any(
        row["changed"] for row in monitor.marked_profile(changed_trial, "NCT03412565")["rows"]
    )


def test_reviewing_a_trial_keeps_every_change_record(changed_trial):
    """History is retained so a per-field view can be built from it later.

    Reviewing flags the rows as read; what they record is untouched.
    """
    kept = ("field", "previous", "current", "detected_at")
    before = [
        {k: c[k] for k in kept} for c in storage.list_changes(changed_trial, "NCT03412565")
    ]

    monitor.review(changed_trial, "NCT03412565", when="2026-01-16T00:00:00+00:00")

    after = storage.list_changes(changed_trial, "NCT03412565")
    assert [{k: c[k] for k in kept} for c in after] == before
    assert all(c["reviewed"] for c in after)


def test_a_change_detected_after_a_review_highlights_the_trial_again(
    changed_trial, record, make_fetcher
):
    monitor.review(changed_trial, "NCT03412565", when="2026-01-16T00:00:00+00:00")

    monitor.check(
        changed_trial,
        "NCT03412565",
        fetch=make_fetcher(default=revised(record, 90, "2026-02-15")),
        when="2026-02-15T00:00:00+00:00",
    )

    rows = marked(changed_trial)
    assert rows["enrollment"]["changed"] is True
    assert rows["enrollment"]["previous"] == 180
    assert rows["enrollment"]["value"] == 90


def test_reviewing_one_trial_leaves_another_trial_highlighted(
    watched, record, make_fetcher
):
    monitor.add(watched, "NCT00000001", fetch=make_fetcher(default=record))
    fetch = make_fetcher(default=revised(record, 180, "2026-01-15"))
    monitor.check(watched, "NCT03412565", fetch=fetch, when="2026-01-15T00:00:00+00:00")
    monitor.check(watched, "NCT00000001", fetch=fetch, when="2026-01-15T00:00:00+00:00")

    monitor.review(watched, "NCT03412565", when="2026-01-16T00:00:00+00:00")

    assert marked(watched)["enrollment"]["changed"] is False
    assert marked(watched, "NCT00000001")["enrollment"]["changed"] is True


def test_reviewing_an_unwatched_trial_is_refused(conn):
    with pytest.raises(monitor.MonitorError, match="not on the watchlist"):
        monitor.review(conn, "NCT03412565")


def test_the_marked_up_profile_counts_what_is_still_unreviewed(changed_trial):
    assert monitor.marked_profile(changed_trial, "NCT03412565")["unreviewed"] == 1

    monitor.review(changed_trial, "NCT03412565", when="2026-01-16T00:00:00+00:00")

    assert monitor.marked_profile(changed_trial, "NCT03412565")["unreviewed"] == 0


def test_the_feed_distinguishes_unreviewed_changes_from_reviewed_ones(changed_trial):
    [entry] = [e for e in monitor.feed(changed_trial) if "changed" in e["kind"]]
    assert entry["reviewed"] is False

    monitor.review(changed_trial, "NCT03412565", when="2026-01-16T00:00:00+00:00")

    [entry] = [e for e in monitor.feed(changed_trial) if "changed" in e["kind"]]
    assert entry["reviewed"] is True


def test_a_change_recorded_against_a_field_no_longer_monitored_stays_clearable(
    changed_trial,
):
    """The monitored set has been revised before and may be again. A record left
    behind by a dropped field has nothing to highlight, but must not leave the
    trial permanently flagged."""
    storage.add_change(
        changed_trial,
        "NCT03412565",
        {"field": "retiredField", "previous": "a", "current": "b"},
        when="2026-01-15T00:00:00+00:00",
    )

    marked = monitor.marked_profile(changed_trial, "NCT03412565")
    assert marked["unreviewed"] == 2
    assert "retiredField" not in {row["field"] for row in marked["rows"]}

    monitor.review(changed_trial, "NCT03412565", when="2026-01-16T00:00:00+00:00")

    assert monitor.marked_profile(changed_trial, "NCT03412565")["unreviewed"] == 0
