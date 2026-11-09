"""New matches: the saved search's results not yet monitored; add, dismiss, undo, restore.

Uses the suite's stub finder serving the captured record restyled as three studies, two
watchlists (1 and one made by the test). Lacks: a search matching thousands (only the cap
of 100 is exercised) and a registry failure while adding.
"""

from __future__ import annotations

import time

import monitor
import storage

IDS = ["NCT00000011", "NCT00000012", "NCT00000013"]


def checked(api, studies, list_id=1):
    """Run a check whose search finds `studies`."""
    conn = storage.connect(api.path)
    monitor.remember_search(conn, list_id, monitor.as_query(cond="myeloma"))
    monitor.find_new(conn, list_id, find=lambda **_: studies)
    conn.close()


def test_new_matches_lists_the_unmonitored_results_of_the_saved_search(api, record, restyled):
    """test_new_matches_lists_the_unmonitored_results_of_the_saved_search"""
    checked(api, [restyled(record, n) for n in IDS])
    status, body = api.get("/api/watchlists/1/new-matches")
    assert status == 200
    assert [t["nct_id"] for t in body["trials"]] == IDS
    assert body["counts"]["trials"] == 3 and body["capped"] is False
    assert {"heading", "phase", "sponsor", "status"} <= set(body["trials"][0])
    (only,) = api.get("/api/watchlists")[1]["watchlists"]
    assert only["new_match_count"] == 3


def test_adding_new_matches_takes_baselines_and_removes_them_from_the_offer(api, record, restyled):
    """test_adding_new_matches_takes_baselines_and_removes_them_from_the_offer"""
    checked(api, [restyled(record, n) for n in IDS])
    api.fetch_override(lambda n: restyled(record, n))
    status, done = api.post("/api/watchlists/1/trials", {"nct_ids": IDS[:2]})
    assert status == 200 and done["added"] == IDS[:2]
    body = api.get("/api/watchlists/1/new-matches")[1]
    assert [t["nct_id"] for t in body["trials"]] == IDS[2:]
    conn = storage.connect(api.path)
    assert storage.latest_snapshot(conn, IDS[0]) is not None


def test_a_dismissed_match_is_not_offered_again_by_later_checks_and_nothing_else_changes(api, record, restyled):
    """test_a_dismissed_match_is_not_offered_again_by_later_checks_and_nothing_else_changes"""
    other = api.post("/api/watchlists", {"name": "Other"})[1]["watchlist"]["id"]
    studies = [restyled(record, n) for n in IDS]
    checked(api, studies)
    checked(api, studies, list_id=other)
    status, body = api.post("/api/watchlists/1/new-matches/dismiss", {"nct_ids": IDS[:1]})
    assert status == 200 and body["dismissed"] == IDS[:1] and body["undo_token"]
    checked(api, studies)  # a later check finds the same studies
    assert [t["nct_id"] for t in api.get("/api/watchlists/1/new-matches")[1]["trials"]] == IDS[1:]
    assert [t["nct_id"] for t in api.get(f"/api/watchlists/{other}/new-matches")[1]["trials"]] == IDS
    dismissed = api.get("/api/watchlists/1/new-matches/dismissed")[1]
    assert [t["nct_id"] for t in dismissed["trials"]] == IDS[:1]


def test_restoring_a_dismissed_match_offers_it_again_and_undo_restores_the_same_ones(api, record, restyled):
    """test_restoring_a_dismissed_match_offers_it_again_and_undo_restores_the_same_ones"""
    checked(api, [restyled(record, n) for n in IDS])
    token = api.post("/api/watchlists/1/new-matches/dismiss", {"nct_ids": IDS[:2]})[1]["undo_token"]
    status, body = api.post("/api/watchlists/1/new-matches/restore", {"nct_ids": IDS[:1]})
    assert status == 200 and body["restored"] == IDS[:1]
    assert [t["nct_id"] for t in api.get("/api/watchlists/1/new-matches")[1]["trials"]] == [IDS[0], IDS[2]]
    status, body = api.post("/api/watchlists/1/new-matches/undo", {"token": token})
    assert status == 200 and body["restored"] == IDS[1:2]  # the first was restored already
    assert len(api.get("/api/watchlists/1/new-matches")[1]["trials"]) == 3
    assert api.get("/api/watchlists/1/new-matches/dismissed")[1]["trials"] == []


def test_a_search_matching_more_than_a_hundred_offers_a_hundred_and_says_the_cap_applied(api, record, restyled):
    """test_a_search_matching_more_than_a_hundred_offers_a_hundred_and_says_the_cap_applied"""
    studies = [restyled(record, f"NCT{20000000 + i:08d}") for i in range(101)]
    conn = storage.connect(api.path)
    monitor.remember_search(conn, 1, monitor.as_query(cond="myeloma"))
    result = monitor.find_new(conn, 1, find=lambda **_: studies)
    conn.close()
    assert len(result["found"]) == 100 and "more than 100" in result["detail"]
    body = api.get("/api/watchlists/1/new-matches")[1]
    assert body["counts"]["trials"] == 100 and body["capped"] is True and body["cap"] == 100


def test_replacing_or_turning_off_the_saved_search_clears_the_cap_note(api, record, restyled):
    """test_replacing_or_turning_off_the_saved_search_clears_the_cap_note"""
    studies = [restyled(record, f"NCT{20000000 + i:08d}") for i in range(101)]
    conn = storage.connect(api.path)
    monitor.remember_search(conn, 1, monitor.as_query(cond="myeloma"))
    monitor.find_new(conn, 1, find=lambda **_: studies)
    conn.close()
    api.post("/api/watchlists/1/saved-search/off")
    assert api.get("/api/watchlists/1/new-matches")[1]["capped"] is False


def test_new_match_routes_answer_not_found_for_an_unknown_watchlist_and_bad_bodies(api):
    """test_new_match_routes_answer_not_found_for_an_unknown_watchlist_and_bad_bodies"""
    assert api.get("/api/watchlists/99/new-matches")[0] == 404
    assert api.get("/api/watchlists/99/new-matches/dismissed")[0] == 404
    assert api.post("/api/watchlists/99/new-matches/dismiss", {"nct_ids": []})[0] == 404
    status, body = api.post("/api/watchlists/1/new-matches/dismiss", {"nct_ids": "NCT00000011"})
    assert status == 400 and body["error"]["kind"] == "invalid_request"
    assert api.post("/api/watchlists/1/new-matches/undo", {})[1]["error"]["kind"] == "invalid_request"
