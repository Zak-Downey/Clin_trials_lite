"""Ticket 09: looking a trial up without adding it, and creating a watchlist.

Uses the `api` fixture (stub fetcher serving the captured NCT03412565 record for any ID).
Lacks: a slow registry, a registry answering a record with no title.
"""

from __future__ import annotations

import urllib.error

import monitor
import storage


def lookup(api, nct, list_id=1):
    return api.get(f"/api/watchlists/{list_id}/lookup?nct_id={nct}")


def test_looking_up_a_trial_returns_its_facts_and_adds_nothing(api):
    """test_looking_up_a_trial_returns_its_facts_and_adds_nothing"""
    status, body = lookup(api, "nct00000005")
    assert status == 200
    assert body["nct_id"] == "NCT00000005"
    assert body["heading"] and body["official_title"] and body["sponsor"] and body["status"]
    conn = storage.connect(api.path)
    assert storage.get_trial(conn, "NCT00000005") is None
    assert storage.list_trials(conn, 1) == []


def test_the_four_lookup_failures_are_distinct_error_kinds(api):
    """test_the_four_lookup_failures_are_distinct_error_kinds"""
    assert lookup(api, "NCT123")[1]["error"]["kind"] == "invalid_format"
    assert lookup(api, "")[1]["error"]["kind"] == "invalid_format"
    api.post("/api/watchlists/1/trials", {"nct_ids": ["NCT00000002"]})
    status, body = lookup(api, "NCT00000002")
    assert (status, body["error"]["kind"]) == (409, "already_in_list")

    def fetch(nct):
        if nct == "NCT00000008":
            raise urllib.error.HTTPError("u", 404, "nf", {}, None)
        raise urllib.error.URLError("down")

    api.fetch_override(fetch)
    status, body = lookup(api, "NCT00000008")
    assert (status, body["error"]["kind"]) == (404, "not_found")
    status, body = lookup(api, "NCT00000009")
    assert (status, body["error"]["kind"]) == (502, "registry_unavailable")


def test_the_invalid_format_message_explains_nct_followed_by_eight_digits(api):
    """test_the_invalid_format_message_explains_nct_followed_by_eight_digits"""
    assert "NCT followed by 8 digits" in lookup(api, "abc")[1]["error"]["message"]


def test_lookup_in_a_watchlist_that_does_not_exist_is_refused(api):
    """test_lookup_in_a_watchlist_that_does_not_exist_is_refused"""
    status, body = lookup(api, "NCT00000005", list_id=99)
    assert (status, body["error"]["kind"]) == (404, "watchlist_not_found")


def test_creating_a_watchlist_returns_it_and_the_updated_list(api):
    """test_creating_a_watchlist_returns_it_and_the_updated_list"""
    status, body = api.post("/api/watchlists", {"name": "  Lung  "})
    assert status == 200
    assert body["watchlist"]["name"] == "Lung"
    assert body["watchlist"]["trial_count"] == 0
    assert [w["name"] for w in body["watchlists"]][-1] == "Lung"


def test_an_empty_or_duplicate_watchlist_name_is_refused_with_its_own_kind(api):
    """test_an_empty_or_duplicate_watchlist_name_is_refused_with_its_own_kind"""
    status, body = api.post("/api/watchlists", {"name": "   "})
    assert (status, body["error"]["kind"]) == (400, "name_empty")
    first = api.get("/api/watchlists")[1]["watchlists"][0]["name"]
    status, body = api.post("/api/watchlists", {"name": first.upper()})
    assert (status, body["error"]["kind"]) == (409, "name_taken")
    assert "watchlist" in body["error"]["message"]
    assert api.post("/api/watchlists", {})[1]["error"]["kind"] == "name_empty"


def test_monitor_lookup_names_the_failure_kinds(conn, fetcher):
    """test_monitor_lookup_names_the_failure_kinds"""
    import pytest

    with pytest.raises(monitor.MonitorError) as err:
        monitor.lookup(conn, "x", 1, fetch=fetcher)
    assert err.value.kind == "invalid_format"
