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
    assert all(isinstance(i, int) for i in newest["ids"])
    assert len({i for c in changes for i in c["ids"]}) == 3
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
    assert only["last_checked"] is None  # no check for updates has finished yet

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
    assert set(first["changed_fields"]) == {"Overall status", "Primary completion date", "Enrollment"}
    assert first["status"] == "Completed"
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
    status, body = api.post("/api/watchlists/1/needs-review")
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


def test_a_watchlists_last_checked_is_when_its_most_recent_check_for_updates_finished(seeded):
    """test_a_watchlists_last_checked_is_when_its_most_recent_check_for_updates_finished"""
    conn = storage.connect(seeded.path)
    # A trial checked later than the run finished (or by another route) does not move it.
    storage.mark_checked(conn, "NCT00000002", "2026-11-09T10:00:00+00:00")
    assert seeded.get("/api/watchlists")[1]["watchlists"][0]["last_checked"] is None
    storage.finish_check_run(conn, LIST_ID, [], "2026-11-03T10:00:00+00:00")
    storage.finish_check_run(conn, LIST_ID, [], "2026-11-05T10:00:00+00:00")
    conn.close()
    (only,) = seeded.get("/api/watchlists")[1]["watchlists"]
    assert only["last_checked"]["iso"].startswith("2026-11-05")


def _raw(api, method, route, headers=None, body=None):
    import http.client
    import json as _json

    host, port = api.base.split("//")[1].split(":")
    connection = http.client.HTTPConnection(host, int(port), timeout=10)
    connection.putrequest(method, route, skip_host=True)
    for name, value in (headers or {}).items():
        connection.putheader(name, value)
    connection.putheader("Content-Length", str(len(body or "")))
    connection.endheaders(body.encode() if body else None)
    response = connection.getresponse()
    return response.status, _json.loads(response.read())


def test_a_foreign_host_header_is_refused(seeded):
    """test_a_foreign_host_header_is_refused"""
    port = seeded.base.rsplit(":", 1)[1]
    status, body = _raw(seeded, "GET", "/api/watchlists", {"Host": f"evil.example:{port}"})
    assert status == 403 and body["error"]["kind"] == "forbidden_host"
    status, _ = _raw(seeded, "GET", "/api/watchlists", {"Host": f"localhost:{port}"})
    assert status == 200
    status, _ = _raw(seeded, "GET", "/api/watchlists", {})
    assert status == 403


def test_a_write_from_a_foreign_origin_or_without_json_is_refused(seeded):
    """test_a_write_from_a_foreign_origin_or_without_json_is_refused"""
    from webapp import routes

    routes.COMPILED.append(("POST", __import__("re").compile(r"/api/_probe\Z"), lambda ctx, **_: {"ok": True}))
    try:
        port = seeded.base.rsplit(":", 1)[1]
        host = f"127.0.0.1:{port}"
        json_type = "application/json"
        assert _raw(seeded, "POST", "/api/_probe", {"Host": host, "Content-Type": json_type}, "{}")[0] == 200
        status, body = _raw(seeded, "POST", "/api/_probe",
                            {"Host": host, "Content-Type": json_type, "Origin": "http://evil.example"}, "{}")
        assert status == 403 and body["error"]["kind"] == "forbidden_origin"
        assert _raw(seeded, "POST", "/api/_probe",
                    {"Host": host, "Content-Type": json_type, "Origin": f"http://{host}"}, "{}")[0] == 200
        status, body = _raw(seeded, "POST", "/api/_probe", {"Host": host, "Content-Type": "text/plain"}, "{}")
        assert status == 415 and body["error"]["kind"] == "unsupported_content_type"
    finally:
        routes.COMPILED.pop()


def test_a_value_and_its_qualifier_moving_together_are_one_change_with_both_ids(seeded):
    """test_a_value_and_its_qualifier_moving_together_are_one_change_with_both_ids"""
    conn = storage.connect(seeded.path)
    check = "2026-11-09T09:00:00+00:00"
    storage.add_change(conn, "NCT00000002", {"field": "primaryCompletionDate", "previous": "2026-01", "current": "2026-06"}, check)
    storage.add_change(conn, "NCT00000002", {"field": "primaryCompletionDateType", "previous": "ESTIMATED", "current": "ACTUAL"}, check)
    conn.close()
    changes = seeded.get("/api/trials/NCT00000002/changes")[1]["changes"]
    moved = [c for c in changes if c["field"] == "primaryCompletionDate"]
    assert len(moved) == 1 and len(moved[0]["ids"]) == 2
    assert (moved[0]["previous_qualifier"], moved[0]["qualifier"]) == ("ESTIMATED", "ACTUAL")
    entry = [t for t in seeded.get(f"/api/watchlists/{LIST_ID}/needs-review")[1]["trials"] if t["nct_id"] == "NCT00000002"][0]
    queue_move = [m for m in entry["moves"] if m["field"] == "primaryCompletionDate"]
    assert [m["ids"] for m in queue_move] == [moved[0]["ids"]]
    unreviewed = [c for c in changes if not c["reviewed"]]
    assert entry["change_count"] == len(unreviewed) == len(entry["moves"])


def test_all_trials_lists_every_trial_with_review_state_freshness_and_failure(seeded):
    """test_all_trials_lists_every_trial_with_review_state_freshness_and_failure"""
    conn = storage.connect(seeded.path)
    storage.mark_checked(conn, "NCT00000003", SECOND_CHECK)
    storage.mark_check_failed(conn, "NCT00000003", "unreachable", "2026-11-08T17:00:00+00:00")
    conn.close()
    status, body = seeded.get(f"/api/watchlists/{LIST_ID}/all-trials")
    assert status == 200
    by_id = {t["nct_id"]: t for t in body["trials"]}
    assert set(by_id) == {"NCT03412565", "NCT00000002", "NCT00000003"}
    first, acro, read = by_id["NCT03412565"], by_id["NCT00000002"], by_id["NCT00000003"]
    assert first["review"] == {"state": "unreviewed", "label": "3 changes"}
    assert acro["review"] == {"state": "unreviewed", "label": "1 change"}
    assert read["review"] == {"state": "reviewed", "label": "Reviewed"}
    assert first["heading"].startswith("A Study to Evaluate") and acro["heading"] == "ACRO"
    assert first["status"] == "Completed"  # the registry status, apart from the review state
    assert first["latest_change"]["iso"].startswith("2026-11-08")
    assert read["last_checked"]["iso"].startswith("2026-11-08")
    assert read["check_failed"]["kind"] == "unreachable"
    assert first["check_failed"] is None


def test_a_trial_with_no_changes_reads_no_changes_and_an_unknown_list_is_not_found(seeded, record, restyled):
    """test_a_trial_with_no_changes_reads_no_changes_and_an_unknown_list_is_not_found"""
    conn = storage.connect(seeded.path)
    quiet = restyled(record, "NCT00000004")
    monitor.add(conn, "NCT00000004", LIST_ID, fetch=lambda _n: quiet, when="2026-11-01T08:00:00+00:00")
    conn.close()
    trials = seeded.get(f"/api/watchlists/{LIST_ID}/all-trials")[1]["trials"]
    quiet_row = next(t for t in trials if t["nct_id"] == "NCT00000004")
    assert quiet_row["review"] == {"state": "none", "label": "No changes"}
    assert quiet_row["latest_change"] is None
    status, body = seeded.get("/api/watchlists/999/all-trials")
    assert status == 404 and body["error"]["kind"] == "watchlist_not_found"
