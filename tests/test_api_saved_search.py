"""The saved search of a watchlist: read, save or replace, turn off.

Uses the suite's stub server over an empty database (one default watchlist, no trials)
and a second watchlist made by the test. Lacks: a saved search whose query holds the
registry's own odd characters, and a search run after saving (tickets 10's checks cover
only the saved query; running it is ticket 07's).
"""

from __future__ import annotations

import storage

QUERY = {"cond": "myeloma", "intr": "", "spons": "Janssen", "phase": ["PHASE3"],
         "sponsor_type": ["INDUSTRY"], "status": ["RECRUITING", "ACTIVE_NOT_RECRUITING"],
         "started_from": "", "started_to": ""}


def test_a_watchlist_with_no_saved_search_reads_as_none(api):
    """test_a_watchlist_with_no_saved_search_reads_as_none"""
    status, body = api.get("/api/watchlists/1/saved-search")
    assert status == 200 and body["saved_search"] is None


def test_saving_a_search_stores_it_and_adds_no_trials(api):
    """test_saving_a_search_stores_it_and_adds_no_trials"""
    status, body = api.post("/api/watchlists/1/saved-search", {"query": QUERY})
    assert status == 200
    assert body["replaced"] is False and body["previous"] is None
    assert body["watchlist"]["id"] == 1
    assert body["saved_search"] == QUERY
    assert api.get("/api/watchlists/1/saved-search")[1]["saved_search"] == QUERY
    (only,) = api.get("/api/watchlists")[1]["watchlists"]
    assert only["saved_search"] is True and only["trial_count"] == 0


def test_saving_again_replaces_and_reports_the_old_query(api):
    """test_saving_again_replaces_and_reports_the_old_query"""
    api.post("/api/watchlists/1/saved-search", {"query": QUERY})
    newer = {**QUERY, "cond": "lymphoma", "phase": []}
    _, body = api.post("/api/watchlists/1/saved-search", {"query": newer})
    assert body["replaced"] is True and body["previous"] == QUERY
    assert api.get("/api/watchlists/1/saved-search")[1]["saved_search"] == newer


def test_a_query_that_names_nothing_is_refused_and_the_old_one_stays(api):
    """test_a_query_that_names_nothing_is_refused_and_the_old_one_stays"""
    api.post("/api/watchlists/1/saved-search", {"query": QUERY})
    status, body = api.post("/api/watchlists/1/saved-search", {"query": {"status": ["RECRUITING"]}})
    assert status == 400 and body["error"]["kind"] == "nothing_asked"
    assert api.get("/api/watchlists/1/saved-search")[1]["saved_search"] == QUERY


def test_an_inverted_date_range_is_refused_as_bad_dates(api):
    """test_an_inverted_date_range_is_refused_as_bad_dates"""
    status, body = api.post("/api/watchlists/1/saved-search",
                            {"query": {"cond": "x", "started_from": "2022-01", "started_to": "2020-01"}})
    assert status == 400 and body["error"]["kind"] == "bad_dates"


def test_a_missing_or_malformed_query_is_refused(api):
    """test_a_missing_or_malformed_query_is_refused"""
    assert api.post("/api/watchlists/1/saved-search", {})[1]["error"]["kind"] == "invalid_request"
    status, body = api.post("/api/watchlists/1/saved-search", {"query": {"cond": ["x"]}})
    assert status == 400 and body["error"]["kind"] == "invalid_request"


def test_an_unknown_watchlist_answers_not_found_on_every_saved_search_route(api):
    """test_an_unknown_watchlist_answers_not_found_on_every_saved_search_route"""
    assert api.get("/api/watchlists/99/saved-search")[1]["error"]["kind"] == "watchlist_not_found"
    assert api.post("/api/watchlists/99/saved-search", {"query": QUERY})[0] == 404
    assert api.post("/api/watchlists/99/saved-search/off")[0] == 404


def test_turning_off_removes_the_search_and_keeps_the_trials(api, record):
    """test_turning_off_removes_the_search_and_keeps_the_trials"""
    import monitor

    conn = storage.connect(api.path)
    monitor.add(conn, "NCT03412565", 1, fetch=lambda _n: record, when="2026-11-01T08:00:00+00:00")
    conn.close()
    api.post("/api/watchlists/1/saved-search", {"query": QUERY})
    status, body = api.post("/api/watchlists/1/saved-search/off")
    assert status == 200
    (only,) = body["watchlists"]
    assert only["saved_search"] is False and only["trial_count"] == 1
    assert api.get("/api/watchlists/1/saved-search")[1]["saved_search"] is None


def test_a_saved_search_belongs_to_one_watchlist(api):
    """test_a_saved_search_belongs_to_one_watchlist"""
    _, made = api.post("/api/watchlists", {"name": "Second"})
    other = made["watchlist"]["id"]
    api.post("/api/watchlists/1/saved-search", {"query": QUERY})
    assert api.get(f"/api/watchlists/{other}/saved-search")[1]["saved_search"] is None
