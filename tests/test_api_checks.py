"""Checking a watchlist for updates through the API: a run on a server thread, one at a time,
failures per trial apart from the saved search, Retry failed.

Uses the captured record restyled into three trials of watchlist 1. Lacks: a run longer than a
few trials, and the registry's real error bodies.
"""

from __future__ import annotations

import copy
import threading
import time
import urllib.error

import pytest

import monitor
import storage

LIST_ID = 1
GATE = threading.Event()


@pytest.fixture(autouse=True)
def no_pause(monkeypatch):
    monkeypatch.setattr(monitor, "PAUSE", 0)


@pytest.fixture
def fetcher(record, restyled):
    """Overrides the suite's fetcher: NCT00000002 fails while FAIL has it, and every
    fetch waits for GATE when it is closed."""
    served = {n: restyled(record, n) for n in ("NCT00000001", "NCT00000002", "NCT00000003")}
    served["NCT03412565"] = record
    fail = set()

    def fetch(nct_id):
        GATE.wait(10)
        if nct_id in fail:
            raise urllib.error.URLError("connection refused")
        return served[nct_id]

    fetch.fail = fail
    fetch.served = served
    GATE.set()
    return fetch


@pytest.fixture
def watched(api, fetcher):
    conn = storage.connect(api.path)
    for nct in ("NCT00000001", "NCT00000002", "NCT00000003"):
        monitor.add(conn, nct, LIST_ID, fetch=fetcher, when="2026-11-01T08:00:00+00:00")
    conn.close()
    return api


def finished(api, route=f"/api/watchlists/{LIST_ID}/check"):
    for _ in range(100):
        status, body = api.get(route)
        assert status == 200
        if body["state"] not in ("running",):
            return body
        time.sleep(0.1)
    raise AssertionError("the check never finished")


def test_a_second_check_for_the_same_watchlist_is_refused_while_one_runs(watched, fetcher):
    """test_a_second_check_for_the_same_watchlist_is_refused_while_one_runs"""
    GATE.clear()
    status, body = watched.post(f"/api/watchlists/{LIST_ID}/check")
    assert status == 200 and body["state"] == "running" and body["total"] == 3
    status, body = watched.post(f"/api/watchlists/{LIST_ID}/check")
    assert (status, body["error"]["kind"]) == (409, "check_running")
    assert watched.post(f"/api/watchlists/{LIST_ID}/check/retry")[1]["error"]["kind"] == "check_running"
    GATE.set()
    assert finished(watched)["state"] == "complete"
    # Once finished, a new check is accepted.
    assert watched.post(f"/api/watchlists/{LIST_ID}/check")[0] == 200
    finished(watched)


def test_a_check_reports_progress_while_the_watchlist_stays_readable(watched):
    """test_a_check_reports_progress_while_the_watchlist_stays_readable"""
    GATE.clear()
    watched.post(f"/api/watchlists/{LIST_ID}/check")
    status, body = watched.get(f"/api/watchlists/{LIST_ID}/needs-review")
    assert status == 200  # the queue answers while a fetch is waiting
    progress = watched.get(f"/api/watchlists/{LIST_ID}/check")[1]
    assert (progress["state"], progress["processed"], progress["total"]) == ("running", 0, 3)
    assert progress["next"] == {"kind": "trial", "nct_id": "NCT00000001"}
    GATE.set()
    done = finished(watched)
    assert (done["state"], done["processed"], done["checked"], done["failed"]) == ("complete", 3, 3, 0)
    assert done["finished_at"] is not None


def test_a_failed_trial_makes_the_check_incomplete_and_keeps_the_search_apart(watched, fetcher):
    """test_a_failed_trial_makes_the_check_incomplete_and_keeps_the_search_apart"""
    conn = storage.connect(watched.path)
    monitor.remember_search(conn, LIST_ID, monitor.as_query(cond="myeloma"))
    conn.close()
    fetcher.fail.add("NCT00000002")
    watched.post(f"/api/watchlists/{LIST_ID}/check")
    done = finished(watched)
    assert done["state"] == "incomplete"
    assert (done["total"], done["checked"], done["failed"]) == (3, 2, 1)
    (bad,) = [t for t in done["trials"] if t["outcome"] == "error"]
    assert (bad["nct_id"], bad["error_kind"]) == ("NCT00000002", "unreachable")
    assert done["search"]["outcome"] == "nothing_found"  # the search's own result, not the trials'
    assert done["retryable"] == 1
    conn = storage.connect(watched.path)
    trial = storage.get_trial(conn, "NCT00000002")
    assert trial["check_error_kind"] == "unreachable"
    assert trial["last_checked"] == "2026-11-01T08:00:00+00:00"  # the baseline, never moved by the failure


def test_a_saved_search_failure_is_reported_apart_from_the_trials(watched, record):
    """test_a_saved_search_failure_is_reported_apart_from_the_trials"""
    conn = storage.connect(watched.path)
    monitor.remember_search(conn, LIST_ID, monitor.as_query(cond="myeloma"))
    conn.close()
    from webapp.server import make_server

    def broken(**_):
        raise urllib.error.URLError("search down")

    server = make_server(watched.path, fetch=lambda n: record, find=broken)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    import json
    import urllib.request

    req = urllib.request.Request(f"{base}/api/watchlists/{LIST_ID}/check", data=b"{}", method="POST",
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req).read()
    for _ in range(100):
        body = json.load(urllib.request.urlopen(f"{base}/api/watchlists/{LIST_ID}/check"))
        if body["state"] != "running":
            break
        time.sleep(0.1)
    server.shutdown()
    assert body["state"] == "incomplete" and body["failed"] == 0
    assert body["search"]["outcome"] == "error"


def test_retry_failed_rechecks_only_the_failed_trials(watched, fetcher):
    """test_retry_failed_rechecks_only_the_failed_trials"""
    fetcher.fail.add("NCT00000002")
    watched.post(f"/api/watchlists/{LIST_ID}/check")
    finished(watched)
    fetcher.fail.clear()

    status, body = watched.post(f"/api/watchlists/{LIST_ID}/check/retry")
    assert status == 200 and body["total"] == 1
    done = finished(watched)
    assert [t["nct_id"] for t in done["trials"]] == ["NCT00000002"]
    assert done["state"] == "complete" and done["retryable"] == 0
    conn = storage.connect(watched.path)
    assert storage.get_trial(conn, "NCT00000002")["check_failed_at"] is None
    assert watched.post(f"/api/watchlists/{LIST_ID}/check/retry")[1]["error"]["kind"] == "nothing_to_retry"


def test_a_check_with_nothing_new_says_how_many_still_need_review_from_earlier(watched):
    """test_a_check_with_nothing_new_says_how_many_still_need_review_from_earlier"""
    conn = storage.connect(watched.path)
    storage.add_change(conn, "NCT00000001", {"field": "enrollment", "previous": 1, "current": 2}, "2026-11-02T00:00:00+00:00")
    conn.close()
    watched.post(f"/api/watchlists/{LIST_ID}/check")
    done = finished(watched)
    assert (done["state"], done["changed"], done["still_need_review"]) == ("complete", 0, 1)
    assert watched.get(f"/api/watchlists/{LIST_ID}/needs-review")[1]["counts"]["trials"] == 1


def test_a_check_runs_the_saved_search_even_with_no_trials(api):
    """test_a_check_runs_the_saved_search_even_with_no_trials"""
    conn = storage.connect(api.path)
    monitor.remember_search(conn, LIST_ID, monitor.as_query(cond="myeloma"))
    conn.close()
    status, body = api.post(f"/api/watchlists/{LIST_ID}/check")
    assert status == 200 and body["total"] == 0 and body["has_search"] is True
    done = finished(api)
    assert done["search"]["outcome"] == "nothing_found" and len(api.finder.calls) == 1


def test_checking_an_unknown_watchlist_is_not_found(api):
    """test_checking_an_unknown_watchlist_is_not_found"""
    assert api.post("/api/watchlists/99/check")[1]["error"]["kind"] == "watchlist_not_found"
    assert api.get("/api/watchlists/99/check")[0] == 404


def test_still_need_review_from_earlier_checks_leaves_out_what_this_check_just_found(watched, fetcher):
    """test_still_need_review_from_earlier_checks_leaves_out_what_this_check_just_found"""
    conn = storage.connect(watched.path)
    storage.add_change(conn, "NCT00000002", {"field": "enrollment", "previous": 1, "current": 2}, "2026-11-02T00:00:00+00:00")
    conn.close()
    revised = copy.deepcopy(fetcher.served["NCT00000001"])
    revised["protocolSection"]["designModule"]["enrollmentInfo"]["count"] += 5
    revised["protocolSection"]["statusModule"]["lastUpdatePostDateStruct"]["date"] = "2026-12-01"
    fetcher.served["NCT00000001"] = revised
    watched.post(f"/api/watchlists/{LIST_ID}/check")
    done = finished(watched)
    assert (done["changed"], done["still_need_review"]) == (1, 1)
    assert watched.get(f"/api/watchlists/{LIST_ID}/needs-review")[1]["counts"]["trials"] == 2
