"""The trial page's API: a trial's unreviewed changes, review by change ID, undo.

Uses the captured NCT03412565 record and a restyled copy, both in watchlist 1
and the copy also in a second watchlist "Other". Lacks: a trial with no
changes at all, and more than two checks.
"""

from __future__ import annotations

import monitor
import storage

FIRST = "2026-11-06T09:00:00+00:00"
SECOND = "2026-11-08T16:45:00+00:00"


def _setup(api, record, restyled):
    conn = storage.connect(api.path)
    other = monitor.create_list(conn, "Other", when="2026-11-01T08:00:00+00:00")
    copy = restyled(record, "NCT00000002")
    for nct, rec in (("NCT03412565", record), ("NCT00000002", copy)):
        monitor.add(conn, nct, 1, fetch=lambda _n, rec=rec: rec, when="2026-11-01T08:00:00+00:00")
    monitor.add(conn, "NCT03412565", other, fetch=lambda _n: record, when="2026-11-01T08:00:00+00:00")
    storage.add_change(conn, "NCT03412565", {"field": "enrollment", "previous": 10, "current": 20}, FIRST)
    storage.add_change(conn, "NCT03412565", {"field": "enrollment", "previous": 20, "current": 30}, SECOND)
    storage.add_change(conn, "NCT03412565", {"field": "overallStatus", "previous": "RECRUITING", "current": "COMPLETED"}, SECOND)
    storage.add_change(conn, "NCT00000002", {"field": "enrollment", "previous": 1, "current": 2}, SECOND, synthetic=True)
    conn.close()
    return other


def _ids(body):
    return [i for g in body["groups"] for c in g["changes"] for i in c["ids"]]


def test_the_trial_page_groups_unreviewed_changes_by_check_and_names_every_watchlist(api, record, restyled):
    """test_the_trial_page_groups_unreviewed_changes_by_check_and_names_every_watchlist"""
    _setup(api, record, restyled)
    status, body = api.get("/api/trials/NCT03412565")
    assert status == 200
    assert [g["check"] for g in body["groups"]] == [SECOND, FIRST]
    assert [len(g["changes"]) for g in body["groups"]] == [2, 1]
    # A field that moved in two checks shows both transitions.
    moves = [(c["label"], c["previous"], c["current"]) for g in body["groups"] for c in g["changes"] if c["field"] == "enrollment"]
    assert moves == [("Enrollment", "20", "30"), ("Enrollment", "10", "20")]
    assert body["groups"][0]["changes"][0]["qualifier"] in (None, "Actual", "Estimated")
    assert body["change_count"] == 3
    assert [w["name"] for w in body["watchlists"]] == [storage.DEFAULT_LIST, "Other"]
    assert body["groups"][0]["registry_updated"] and body["registry_url"].endswith("/NCT03412565")
    assert body["simulated"] is False
    assert api.get("/api/trials/NCT00000002")[1]["simulated"] is True


def test_marking_reviewed_marks_exactly_the_ids_sent_and_a_later_change_stays_unreviewed(api, record, restyled):
    """test_marking_reviewed_marks_exactly_the_ids_sent_and_a_later_change_stays_unreviewed"""
    _setup(api, record, restyled)
    shown = _ids(api.get("/api/trials/NCT03412565")[1])
    conn = storage.connect(api.path)  # a check finishes while the analyst reads
    storage.add_change(conn, "NCT03412565", {"field": "briefTitle", "previous": "a", "current": "b"}, "2026-11-09T09:00:00+00:00")
    conn.close()
    status, body = api.post("/api/trials/NCT03412565/review", {"ids": shown})
    assert status == 200
    assert sorted(body["marked"]) == sorted(shown) and body["unreviewed_count"] == 1
    left = api.get("/api/trials/NCT03412565")[1]
    assert [c["field"] for g in left["groups"] for c in g["changes"]] == ["briefTitle"]
    # Another trial's change is never touched by naming its ID.
    other_id = _ids(api.get("/api/trials/NCT00000002")[1])
    _, again = api.post("/api/trials/NCT03412565/review", {"ids": other_id})
    assert again["marked"] == [] and again["event"] is None
    assert api.get("/api/trials/NCT00000002")[1]["change_count"] == 1


def test_a_review_applies_in_every_watchlist_records_its_time_and_ids_and_undo_returns_exactly_those(api, record, restyled):
    """test_a_review_applies_in_every_watchlist_records_its_time_and_ids_and_undo_returns_exactly_those"""
    other = _setup(api, record, restyled)
    shown = _ids(api.get("/api/trials/NCT03412565")[1])
    keep = shown[0]
    _, body = api.post("/api/trials/NCT03412565/review", {"ids": shown[1:]})
    event = body["event"]
    assert sorted(event["change_ids"]) == sorted(shown[1:]) and event["reviewed_at"]["iso"]
    for list_id in (1, other):
        queue = api.get(f"/api/watchlists/{list_id}/needs-review")[1]["trials"]
        entry = [t for t in queue if t["nct_id"] == "NCT03412565"]
        assert len(entry) == 1 and entry[0]["change_count"] == 1
    conn = storage.connect(api.path)
    assert storage.get_review_event(conn, event["id"])["change_ids"] == event["change_ids"]
    conn.close()
    status, undone = api.post(f"/api/reviews/{event['id']}/undo")
    assert status == 200 and sorted(undone["restored"]) == sorted(shown[1:])
    assert undone["event"]["undone_at"]["iso"] and undone["unreviewed_count"] == len(shown)
    assert sorted(_ids(api.get("/api/trials/NCT03412565")[1])) == sorted(shown) and keep in shown
    status, again = api.post(f"/api/reviews/{event['id']}/undo")
    assert status == 409 and again["error"]["kind"] == "already_undone"
    assert api.post("/api/reviews/999/undo")[0] == 404


def test_a_review_request_without_a_list_of_ids_or_for_an_unknown_trial_is_refused(api, record, restyled):
    """test_a_review_request_without_a_list_of_ids_or_for_an_unknown_trial_is_refused"""
    _setup(api, record, restyled)
    status, body = api.post("/api/trials/NCT03412565/review", {"ids": "all"})
    assert status == 400 and body["error"]["kind"] == "invalid_request"
    assert api.post("/api/trials/NCT03412565/review", {})[0] == 400
    assert api.post("/api/trials/NCT09999999/review", {"ids": []})[1]["error"]["kind"] == "trial_not_found"
    assert api.get("/api/trials/NCT09999999")[1]["error"]["kind"] == "trial_not_found"
