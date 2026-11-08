"""Ticket 05: retention, the five detail sections, the history timeline, the API.

Uses the captured NCT03412565 record (no acronym, no collaborators, no stop reason)
in one or two watchlists. Lacks: a trial with several removals in a row.
"""

from __future__ import annotations

import json

import display
import medical_affairs
import monitor
import storage

T0 = "2026-11-01T08:00:00+00:00"
T1 = "2026-11-08T14:20:00+00:00"
T2 = "2026-11-08T16:45:00+00:00"
NCT = "NCT03412565"


def _add(conn, record, list_id=1):
    monitor.add(conn, NCT, list_id, fetch=lambda _n: record, when=T0)


def test_removing_a_trial_from_its_last_watchlist_keeps_it_and_no_check_fetches_it_and_adding_it_back_resumes(conn, record):
    """test_removing_a_trial_from_its_last_watchlist_keeps_it_and_no_check_fetches_it_and_adding_it_back_resumes"""
    _add(conn, record)
    storage.add_change(conn, NCT, {"field": "enrollment", "previous": 1, "current": 2}, T1)
    monitor.remove(conn, NCT, 1)
    assert storage.get_trial(conn, NCT) is not None
    assert storage.count_snapshots(conn, NCT) == 1 and len(storage.list_changes(conn, NCT)) == 1
    fetched = []
    results = list(monitor.check_all(conn, None, fetch=lambda n: fetched.append(n) or record, pause=0))
    assert results == [] and fetched == []
    assert storage.list_trials(conn) == []
    # Adding it back: no fetch, no new baseline; the next check reports what moved meanwhile.
    monitor.add(conn, NCT, 1, fetch=lambda n: fetched.append(n) or record, when=T1)
    assert fetched == [] and storage.count_snapshots(conn, NCT) == 1
    later = json.loads(json.dumps(record))
    later["protocolSection"]["designModule"]["enrollmentInfo"]["count"] = 999
    later["protocolSection"]["statusModule"]["lastUpdatePostDateStruct"]["date"] = "2030-01-01"
    result = monitor.check(conn, NCT, fetch=lambda _n: later, when=T2)
    assert result["outcome"] == "updated"


def test_deleting_a_watchlist_keeps_the_trial_and_its_history(conn, record):
    """test_deleting_a_watchlist_keeps_the_trial_and_its_history"""
    _add(conn, record)
    monitor.delete_list(conn, 1)
    assert storage.get_trial(conn, NCT) is not None and storage.count_snapshots(conn, NCT) == 1
    assert [e["kind"] for e in storage.monitoring_events(conn, NCT)] == ["stopped"]


def test_the_timeline_is_newest_first_with_checks_reviews_undos_start_and_the_unmonitored_gap(conn, record):
    """test_the_timeline_is_newest_first_with_checks_reviews_undos_start_and_the_unmonitored_gap"""
    _add(conn, record)
    storage.add_change(conn, NCT, {"field": "enrollment", "previous": 1, "current": 2}, T1)
    storage.add_change(conn, NCT, {"field": "overallStatus", "previous": "RECRUITING", "current": "COMPLETED"}, T2)
    storage.add_change(conn, NCT, {"field": "enrollment", "previous": 2, "current": 3}, T2)
    ids = [m["ids"][0] for m in monitor.history(conn, NCT) if m["check"] == T2]
    event = storage.review_changes(conn, NCT, ids, "2026-11-08T17:02:00+00:00")
    storage.undo_review(conn, event["id"], "2026-11-08T17:05:00+00:00")
    storage.remove_member(conn, 1, NCT)
    conn.execute("UPDATE monitoring_events SET at = ?", ("2026-11-09T01:00:00+00:00",))
    storage.add_member(conn, 1, NCT, "2026-11-09T02:00:00+00:00")
    entries = monitor.timeline(conn, NCT)
    assert [e["kind"] for e in entries] == ["resumed", "stopped", "undo", "review", "detection", "detection", "start"]
    review = entries[3]
    assert review["count"] == 2 and review["from_checks"] == [T2]
    detection = entries[4]
    assert detection["at"] == T2 and detection["count"] == 2 and len(detection["moves"]) == 2
    assert all(m["reviewed"] is False for m in detection["moves"])  # undone
    assert entries[5]["at"] == T1


def test_every_field_of_the_eight_groups_lands_in_exactly_one_section_or_at_a_glance():
    """test_every_field_of_the_eight_groups_lands_in_exactly_one_section_or_at_a_glance"""
    placed = [f for _, fields in display.DETAIL_SECTIONS for f in fields] + list(display.GLANCE_FIELDS)
    wanted = [f for _, fields in display.CARDS for f in fields]
    assert sorted(placed) == sorted(wanted)
    assert [t for t, _ in display.DETAIL_SECTIONS] == [
        "Identity & study design", "Conditions & eligibility", "Interventions & arms", "Endpoints", "Dates & results"]


def test_detail_sections_show_not_reported_for_a_missing_value_and_never_collapse_an_unreviewed_field(record):
    """test_detail_sections_show_not_reported_for_a_missing_value_and_never_collapse_an_unreviewed_field"""
    profile = medical_affairs.profile(record)
    body = display.detail_sections(profile, {"enrollment", "conditions"})
    by = {s["title"]: s for s in body["sections"]}
    ident = {f["field"]: f for f in by["Identity & study design"]["fields"]}
    assert ident["acronym"]["value"] == "Not reported" and ident["acronym"]["reported"] is False
    assert ident["officialTitle"]["value"] == profile["officialTitle"]
    assert [f["value"] for f in body["glance"] if f["field"] == "enrollment"] == ["265 · Actual"]
    assert by["Conditions & eligibility"]["locked_open"] is True and by["Endpoints"]["locked_open"] is False
    assert by["Conditions & eligibility"]["unreviewed"] == 1
    assert next(f for f in by["Dates & results"]["fields"] if f["field"] == "startDate")["value"] == "2018-04-26 · Actual"
    assert next(f for f in by["Dates & results"]["fields"] if f["field"] == "whyStopped")["value"] == "Not reported"


def test_the_api_serves_details_history_and_removal_with_undo(api, record, restyled):
    """test_the_api_serves_details_history_and_removal_with_undo"""
    conn = storage.connect(api.path)
    other = monitor.create_list(conn, "Other", when=T0)
    monitor.add(conn, NCT, 1, fetch=lambda _n: record, when=T0)
    monitor.add(conn, NCT, other, fetch=lambda _n: record, when=T0)
    storage.mark_check_failed(conn, NCT, "unavailable", T2)
    conn.close()
    status, head = api.get(f"/api/trials/{NCT}")
    assert status == 200 and head["last_checked"]["iso"] and head["check_failed"]["kind"] == "unavailable"
    assert head["monitoring_began"] == "1 November 2026"
    status, details = api.get(f"/api/trials/{NCT}/details")
    assert status == 200 and len(details["sections"]) == 5 and details["glance"]
    status, hist = api.get(f"/api/trials/{NCT}/history")
    assert status == 200 and hist["entries"][-1]["kind"] == "start"
    status, gone = api.post(f"/api/watchlists/1/trials/{NCT}/remove")
    assert status == 200 and [w["name"] for w in gone["watchlists"]] == ["Other"]
    status, _ = api.post(f"/api/watchlists/1/trials/{NCT}/remove")
    assert status == 404
    status, back = api.post("/api/removals/undo", {"token": gone["undo"]})
    assert status == 200 and [w["name"] for w in back["watchlists"]] == [storage.DEFAULT_LIST, "Other"]
    status, hist = api.get(f"/api/trials/{NCT}/history")
    assert [e["kind"] for e in hist["entries"]] == ["start"]
