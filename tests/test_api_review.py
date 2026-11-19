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
    conn = storage.connect(api.path)
    storage.add_change(conn, "NCT03412565", {"field": "briefTitle", "previous": "a", "current": "b"}, "2026-11-09T09:00:00+00:00")
    conn.close()
    status, body = api.post("/api/trials/NCT03412565/review", {"ids": shown})
    assert status == 200
    assert sorted(body["marked"]) == sorted(shown) and body["unreviewed_count"] == 1
    left = api.get("/api/trials/NCT03412565")[1]
    assert [c["field"] for g in left["groups"] for c in g["changes"]] == ["briefTitle"]
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


def test_a_saved_interventions_change_that_adds_and_removes_nothing_is_on_no_surface(api, record):
    """A change saved before repeats stopped counting (only how often a name repeats
    moved) is not news: no surface sends the analyst to a change that names nothing."""
    conn = storage.connect(api.path)
    monitor.add(conn, "NCT03412565", 1, fetch=lambda _n: record, when="2026-11-01T08:00:00+00:00")
    names = monitor.profile_of(conn, "NCT03412565")["interventions"]
    storage.add_change(
        conn, "NCT03412565",
        {"field": "interventions", "previous": names + [names[0]], "current": names + [names[1], names[1]]},
        FIRST,
    )
    conn.close()

    trial = api.get("/api/trials/NCT03412565")[1]
    assert trial["groups"] == [] and trial["change_count"] == 0
    assert api.get("/api/watchlists/1/needs-review")[1]["trials"] == []
    [row] = api.get("/api/watchlists/1/all-trials")[1]["trials"]
    assert row["review"]["state"] == "none" and row["latest_change"] is None
    [overview] = api.get("/api/watchlists")[1]["watchlists"]
    assert overview["needs_review_count"] == 0
    assert api.get("/api/trials/NCT03412565/changes")[1]["changes"] == []
    assert [e["kind"] for e in api.get("/api/trials/NCT03412565/history")[1]["entries"]] == ["start"]
    summary = api.get("/api/watchlists/1/summary?period=custom&from=2026-11-01&to=2026-11-30")[1]
    assert summary["counts"]["field_changes"] == 0


def test_a_saved_interventions_change_that_removes_a_name_is_still_shown(api, record):
    conn = storage.connect(api.path)
    monitor.add(conn, "NCT03412565", 1, fetch=lambda _n: record, when="2026-11-01T08:00:00+00:00")
    names = monitor.profile_of(conn, "NCT03412565")["interventions"]
    storage.add_change(
        conn, "NCT03412565",
        {"field": "interventions", "previous": names + [names[0]], "current": names[:-1]},
        FIRST,
    )
    conn.close()

    trial = api.get("/api/trials/NCT03412565")[1]
    assert [c["field"] for g in trial["groups"] for c in g["changes"]] == ["interventions"]
    assert [t["change_count"] for t in api.get("/api/watchlists/1/needs-review")[1]["trials"]] == [1]


def test_an_interventions_change_carries_what_was_removed_added_and_unchanged(api, record):
    """A simulated removal of Carfilzomib (the stand-in registry's "one intervention
    fewer" record) serves the split; an enrolment change beside it carries none, and
    every change keeps its previous and current text."""
    conn = storage.connect(api.path)
    monitor.add(conn, "NCT03412565", 1, fetch=lambda _n: record, when="2026-11-01T08:00:00+00:00")
    storage.add_change(
        conn, "NCT03412565",
        {"field": "interventions",
         "previous": ["Daratumumab", "Bortezomib", "Lenalidomide", "Dexamethasone", "Melphalan", "Prednisone", "Carfilzomib"],
         "current": ["Daratumumab", "Bortezomib", "Lenalidomide", "Dexamethasone", "Melphalan", "Prednisone"]},
        SECOND, synthetic=True,
    )
    storage.add_change(conn, "NCT03412565", {"field": "enrollment", "previous": 248, "current": 265}, SECOND)
    conn.close()

    trial = api.get("/api/trials/NCT03412565")[1]
    changes = {c["field"]: c for g in trial["groups"] for c in g["changes"]}
    moved = changes["interventions"]
    assert moved["removed"] == ["Carfilzomib"]
    assert moved["added"] == []
    assert moved["unchanged"] == ["Daratumumab", "Bortezomib", "Lenalidomide", "Dexamethasone", "Melphalan", "Prednisone"]
    assert moved["previous"].endswith("Prednisone, Carfilzomib") and moved["current"].endswith("Prednisone")
    assert moved["simulated"] is True and trial["simulated"] is True
    other = changes["enrollment"]
    assert not {"added", "removed", "unchanged"} & set(other)
    assert (other["previous"], other["current"]) == ("248", "265")


def test_a_renamed_or_newly_filled_interventions_list_reads_as_removals_and_additions(api, record):
    conn = storage.connect(api.path)
    monitor.add(conn, "NCT03412565", 1, fetch=lambda _n: record, when="2026-11-01T08:00:00+00:00")
    storage.add_change(conn, "NCT03412565", {"field": "interventions", "previous": ["Carfilzomib", "Dexamethasone"],
                                             "current": ["carfilzomib (Kyprolis)", "Dexamethasone"]}, FIRST)
    storage.add_change(conn, "NCT03412565", {"field": "interventions", "previous": [], "current": ["B", "A"]}, SECOND)
    conn.close()

    groups = api.get("/api/trials/NCT03412565")[1]["groups"]
    [filled], [renamed] = (g["changes"] for g in groups)
    assert (filled["removed"], filled["added"], filled["unchanged"]) == ([], ["B", "A"], [])
    assert (renamed["removed"], renamed["added"], renamed["unchanged"]) == (
        ["Carfilzomib"], ["carfilzomib (Kyprolis)"], ["Dexamethasone"])


def test_a_review_that_covered_only_a_hidden_interventions_change_is_not_in_the_history(api, record):
    """A review saved before repeats stopped counting, of a change that only moved
    how often a name repeats, reviewed nothing still shown: History leaves it and
    its undo out rather than reading "Marked 0 changes from 0 checks". A review
    that also covered a change still shown keeps its entry, counting that one."""
    conn = storage.connect(api.path)
    monitor.add(conn, "NCT03412565", 1, fetch=lambda _n: record, when="2026-11-01T08:00:00+00:00")
    names = monitor.profile_of(conn, "NCT03412565")["interventions"]
    repeats = {"field": "interventions", "previous": names + [names[0]], "current": names + [names[1]]}
    storage.add_change(conn, "NCT03412565", repeats, FIRST)
    storage.add_change(conn, "NCT03412565", repeats, SECOND)
    storage.add_change(conn, "NCT03412565", {"field": "enrollment", "previous": 10, "current": 20}, SECOND)
    hidden_first, hidden_second, shown = [
        r["id"] for r in conn.execute("SELECT id FROM changes ORDER BY id")]
    alone = storage.review_changes(conn, "NCT03412565", [hidden_first], when="2026-11-07T10:00:00+00:00")
    storage.undo_review(conn, alone["id"], when="2026-11-07T11:00:00+00:00")
    storage.review_changes(conn, "NCT03412565", [hidden_second, shown], when="2026-11-09T10:00:00+00:00")
    conn.close()

    entries = api.get("/api/trials/NCT03412565/history")[1]["entries"]
    assert [e["kind"] for e in entries] == ["review", "detection", "start"]
    assert entries[0]["count"] == 1

    assert api.get("/api/watchlists/1/needs-review")[1]["trials"] == []
    status, body = api.post(f"/api/reviews/{alone['id'] + 1}/undo", {})
    assert status == 200 and body["unreviewed_count"] == 1
    [queued] = api.get("/api/watchlists/1/needs-review")[1]["trials"]
    assert queued["change_count"] == 1
    kinds = [e["kind"] for e in api.get("/api/trials/NCT03412565/history")[1]["entries"]]
    assert kinds == ["undo", "review", "detection", "start"]
