"""Ticket 08: adding several trials to a watchlist, and the details of a trial not monitored.

Uses the `api` fixture (stub fetcher serving the captured NCT03412565 record for any ID,
except those a test makes fail). Lacks: a registry that is slow, a list of more than a few IDs.
"""

from __future__ import annotations

import storage


def test_adding_several_trials_reports_which_were_added_which_were_already_there_and_which_failed(api):
    """test_adding_several_trials_reports_which_were_added_which_were_already_there_and_which_failed"""
    api.post("/api/watchlists/1/trials", {"nct_ids": ["NCT00000002"]})
    original = type(api).fetch  # the class attribute, unbound

    def fetch(nct):
        if nct == "NCT00000004":
            raise KeyError("boom")
        return original(nct)

    api.fetch_override(fetch)
    status, body = api.post("/api/watchlists/1/trials", {"nct_ids": ["NCT00000002", "NCT00000003", "NCT00000004", "nope"]})
    assert status == 200
    assert body["added"] == ["NCT00000003"]
    assert body["already"] == ["NCT00000002"]
    assert [f["nct_id"] for f in body["failed"]] == ["NCT00000004", "nope"]
    assert body["list"] == {"id": 1, "name": storage.list_lists(storage.connect(api.path))[0]["name"]}


def test_a_trial_added_for_the_first_time_has_a_baseline_and_no_changes(api):
    """test_a_trial_added_for_the_first_time_has_a_baseline_and_no_changes"""
    api.post("/api/watchlists/1/trials", {"nct_ids": ["NCT00000002"]})
    conn = storage.connect(api.path)
    assert storage.count_snapshots(conn, "NCT00000002") == 1
    assert storage.list_changes(conn, "NCT00000002") == []


def test_adding_to_a_watchlist_that_does_not_exist_is_refused(api):
    """test_adding_to_a_watchlist_that_does_not_exist_is_refused"""
    status, body = api.post("/api/watchlists/99/trials", {"nct_ids": ["NCT00000002"]})
    assert status == 404 and body["error"]["kind"] == "watchlist_not_found"


def test_adding_needs_a_list_of_ids(api):
    """test_adding_needs_a_list_of_ids"""
    status, body = api.post("/api/watchlists/1/trials", {"nct_ids": "NCT00000002"})
    assert status == 400 and body["error"]["kind"] == "invalid_request"


def test_details_of_a_trial_not_monitored_come_from_the_registry_and_store_nothing(api):
    """test_details_of_a_trial_not_monitored_come_from_the_registry_and_store_nothing"""
    status, body = api.get("/api/registry/trials/nct00000007")
    assert status == 200
    assert body["nct_id"] == "NCT00000007" and body["watchlists"] == []
    assert body["heading"] and body["sponsor"]
    assert [s["title"] for s in body["sections"]][0]
    assert body["glance"] and body["registry_url"].endswith("/NCT00000007")
    assert type(api).fetch.calls.count("NCT00000007") == 1
    assert storage.get_trial(storage.connect(api.path), "NCT00000007") is None


def test_details_of_a_trial_the_registry_does_not_know_say_so(api):
    """test_details_of_a_trial_the_registry_does_not_know_say_so"""
    import urllib.error

    def fetch(nct):
        raise urllib.error.HTTPError("u", 404, "nf", {}, None)

    api.fetch_override(fetch)
    status, body = api.get("/api/registry/trials/NCT00000007")
    assert status == 404 and body["error"]["kind"] == "not_found"
    assert "NCT00000007 was not found on ClinicalTrials.gov" in body["error"]["message"]


def test_details_when_the_registry_cannot_be_reached_are_a_bad_gateway_not_a_missing_trial(api):
    """test_details_when_the_registry_cannot_be_reached_are_a_bad_gateway_not_a_missing_trial"""
    import urllib.error

    def fetch(nct):
        raise urllib.error.URLError("offline")

    api.fetch_override(fetch)
    status, body = api.get("/api/registry/trials/NCT00000007")
    assert status == 502 and body["error"]["kind"] == "unreachable"
