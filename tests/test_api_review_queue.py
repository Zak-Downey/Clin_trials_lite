"""The local server's API: watchlists, the Needs review queue and a trial's changes.

Uses the captured NCT03412565 record, restyled into three trials in one
watchlist: one with two unreviewed checks, one with an acronym and a simulated
change, one fully reviewed. Lacks: an empty database, a watchlist with a saved
search, and more than a handful of trials.
"""

from __future__ import annotations

import copy
import time

import pytest

import monitor
import storage

LIST_ID = 1
FIRST_CHECK = "2026-11-06T09:00:00+00:00"
SECOND_CHECK = "2026-11-08T16:45:00+00:00"


def _revised(record, updated):
    copied = copy.deepcopy(record)
    copied["protocolSection"]["statusModule"]["lastUpdatePostDateStruct"]["date"] = updated
    return copied


@pytest.fixture
def seeded(api, record, restyled):
    """Three watched trials with changes, written through a second connection."""
    conn = storage.connect(api.path)
    acronym_record = restyled(record, "NCT00000002")
    acronym_record["protocolSection"]["identificationModule"]["acronym"] = "ACRO"
    reviewed_record = restyled(record, "NCT00000003")

    for nct, rec in (
        ("NCT03412565", record),
        ("NCT00000002", acronym_record),
        ("NCT00000003", reviewed_record),
    ):
        monitor.add(conn, nct, LIST_ID, fetch=lambda _n, rec=rec: rec, when="2026-11-01T08:00:00+00:00")

    # Trial 1: two checks. The first moved two fields, the second one.
    storage.add_snapshot(conn, "NCT03412565", _revised(record, "2026-11-05"), FIRST_CHECK)
    storage.add_change(conn, "NCT03412565", {"field": "enrollment", "previous": 10, "current": 20}, FIRST_CHECK)
    storage.add_change(conn, "NCT03412565", {"field": "primaryCompletionDate", "previous": "2026-01", "current": "2026-06"}, FIRST_CHECK)
    storage.add_snapshot(conn, "NCT03412565", _revised(record, "2026-11-07"), SECOND_CHECK)
    storage.add_change(conn, "NCT03412565", {"field": "overallStatus", "previous": "RECRUITING", "current": "COMPLETED"}, SECOND_CHECK)

    # Trial 2: one simulated change, detected before trial 1's newest.
    storage.add_change(conn, "NCT00000002", {"field": "enrollment", "previous": 1, "current": 2}, FIRST_CHECK, synthetic=True)

    # Trial 3: a change that was already read.
    storage.add_change(conn, "NCT00000003", {"field": "enrollment", "previous": 1, "current": 2}, FIRST_CHECK)
    storage.mark_reviewed(conn, "NCT00000003", SECOND_CHECK)
    conn.close()
    return api


def test_an_unknown_address_answers_with_a_stable_kind_and_a_message(api):
    """test_an_unknown_address_answers_with_a_stable_kind_and_a_message"""
    status, body = api.get("/api/nowhere")
    assert status == 404
    assert body["error"]["kind"] == "not_found"
    assert body["error"]["message"]


def test_an_unknown_watchlist_answers_with_its_own_kind(api):
    """test_an_unknown_watchlist_answers_with_its_own_kind"""
    status, body = api.get("/api/watchlists/999/needs-review")
    assert status == 404
    assert body["error"]["kind"] == "watchlist_not_found"
    assert "999" in body["error"]["message"]


def test_listing_a_trials_changes_carries_ids_check_and_review_state(seeded):
    """test_listing_a_trials_changes_carries_ids_check_and_review_state"""
    status, body = seeded.get("/api/trials/NCT03412565/changes")
    assert status == 200
    changes = body["changes"]
    assert [c["field"] for c in changes] == ["overallStatus", "primaryCompletionDate", "enrollment"]
    newest = changes[0]
    assert isinstance(newest["id"], int)
    assert len({c["id"] for c in changes}) == 3
    assert newest["check"] == newest["detected_at"]["iso"]
    assert changes[1]["check"] == changes[2]["check"] != newest["check"]
    assert (newest["previous"], newest["current"]) == ("RECRUITING", "COMPLETED")
    assert newest["reviewed"] is False and newest["synthetic"] is False
    # The sponsor's revision date as of that check, not as of today.
    assert newest["registry_updated"] == "2026-11-07"
    assert changes[2]["registry_updated"] == "2026-11-05"


def test_changes_of_a_trial_not_watched_answer_not_found(seeded):
    """test_changes_of_a_trial_not_watched_answer_not_found"""
    status, body = seeded.get("/api/trials/NCT09999999/changes")
    assert status == 404
    assert body["error"]["kind"] == "trial_not_found"


def test_watchlists_carry_counts_last_checked_and_saved_search_flag(seeded):
    """test_watchlists_carry_counts_last_checked_and_saved_search_flag"""
    status, body = seeded.get("/api/watchlists")
    assert status == 200
    (only,) = body["watchlists"]
    assert only["id"] == LIST_ID and only["name"] == storage.DEFAULT_LIST
    assert only["trial_count"] == 3
    assert only["needs_review_count"] == 2
    assert only["saved_search"] is False
    assert only["last_checked"]["iso"].startswith("2026-11-01")

    conn = storage.connect(seeded.path)
    storage.set_list_search(conn, LIST_ID, {"cond": "myeloma"})
    conn.close()
    assert seeded.get("/api/watchlists")[1]["watchlists"][0]["saved_search"] is True


def test_needs_review_holds_only_unreviewed_trials_newest_detection_first(seeded):
    """test_needs_review_holds_only_unreviewed_trials_newest_detection_first"""
    status, body = seeded.get(f"/api/watchlists/{LIST_ID}/needs-review")
    assert status == 200
    assert [t["nct_id"] for t in body["trials"]] == ["NCT03412565", "NCT00000002"]
    # Trials and field changes are separate numbers: 2 trials, 4 fields.
    assert body["counts"] == {"trials": 2, "field_changes": 3 + 1}


def test_a_queue_entry_carries_what_the_row_shows(seeded):
    """test_a_queue_entry_carries_what_the_row_shows"""
    first, second = seeded.get(f"/api/watchlists/{LIST_ID}/needs-review")[1]["trials"]
    assert first["heading"].startswith("A Study to Evaluate Subcutaneous")
    assert second["heading"] == "ACRO"
    assert first["phase"] and first["sponsor"] and first["status"]
    assert set(first["changed_fields"]) == {"overallStatus", "primaryCompletionDate", "enrollment"}
    assert first["detected_at"]["iso"].startswith("2026-11-08")
    assert first["change_count"] == 3
    assert first["simulated"] is False and second["simulated"] is True


def test_times_are_in_the_machines_zone_with_the_zone_named(seeded, monkeypatch):
    """test_times_are_in_the_machines_zone_with_the_zone_named"""
    monkeypatch.setenv("TZ", "America/New_York")
    time.tzset()
    try:
        entry = seeded.get(f"/api/watchlists/{LIST_ID}/needs-review")[1]["trials"][0]
        assert entry["detected_at"] == {"iso": "2026-11-08T11:45:00-05:00", "zone": "EST"}
    finally:
        monkeypatch.undo()
        time.tzset()


def test_a_known_address_with_the_wrong_method_says_so(api):
    """test_a_known_address_with_the_wrong_method_says_so"""
    status, body = api.post("/api/watchlists")
    assert status == 405
    assert body["error"]["kind"] == "method_not_allowed"


def test_a_stamp_without_an_offset_is_read_as_utc(monkeypatch):
    """test_a_stamp_without_an_offset_is_read_as_utc"""
    from webapp.times import local

    monkeypatch.setenv("TZ", "America/New_York")
    time.tzset()
    try:
        assert local("2026-11-08T16:45:00") == {"iso": "2026-11-08T11:45:00-05:00", "zone": "EST"}
        assert local("not a time") is None and local(None) is None
    finally:
        monkeypatch.undo()
        time.tzset()
