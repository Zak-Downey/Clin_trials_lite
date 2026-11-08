"""The stand-in registry, driven over HTTP and through the app's own registry client.

No browser. Uses the captured NCT03412565 record and copies of it. Lacks: any
second real study, and filtering by the search's terms.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

import ctgov
import monitor
import storage
from walks import helper, standin_registry


def _get(registry, path):
    try:
        with urllib.request.urlopen(registry.url + path, timeout=10) as reply:
            return reply.status, json.load(reply)
    except urllib.error.HTTPError as err:
        return err.code, json.load(err)


@pytest.fixture
def through_ctgov(registry, monkeypatch):
    monkeypatch.setattr(ctgov, "BASE", registry.url + "/api/v2")
    return registry


def test_standin_serves_one_study_by_nct_id_from_the_captured_fixture(registry):
    """test_standin_serves_one_study_by_nct_id_from_the_captured_fixture"""
    record = json.loads(standin_registry.FIXTURE.read_text(encoding="utf-8"))
    status, body = _get(registry, "/api/v2/studies/NCT03412565")
    assert status == 200 and body == record
    status, body = _get(registry, "/api/v2/studies/NCT00000002")
    assert body["protocolSection"]["identificationModule"]["nctId"] == "NCT00000002"
    assert _get(registry, "/api/v2/studies/NCT99999999")[0] == 404


def test_standin_search_pages_with_a_total_count(registry):
    """test_standin_search_pages_with_a_total_count"""
    status, first = _get(registry, "/api/v2/studies?pageSize=2&countTotal=true")
    assert status == 200 and len(first["studies"]) == 2 and first["totalCount"] == 3
    _, second = _get(registry, f"/api/v2/studies?pageSize=2&pageToken={first['nextPageToken']}")
    assert len(second["studies"]) == 1 and "nextPageToken" not in second
    assert "totalCount" not in second


def test_standin_not_found_switch_makes_the_apps_lookup_say_not_found(registry, through_ctgov):
    """test_standin_not_found_switch_makes_the_apps_lookup_say_not_found"""
    registry.set("not_found")
    with pytest.raises(monitor.MonitorError, match="was not found on ClinicalTrials.gov"):
        monitor._fetch_record("NCT03412565", None)
    registry.set("not_found", False)
    assert monitor._fetch_record("NCT03412565", None)["protocolSection"]


def test_standin_server_error_switch_makes_both_calls_fail_as_the_registry_would(registry, through_ctgov):
    """test_standin_server_error_switch_makes_both_calls_fail_as_the_registry_would"""
    registry.set("server_error")
    with pytest.raises(monitor.MonitorError, match=r"returned an error for NCT03412565 \(500\)"):
        monitor._fetch_record("NCT03412565", None)
    assert _get(registry, "/api/v2/studies?pageSize=1")[0] == 500
    with pytest.raises(urllib.error.HTTPError):
        ctgov.search(limit=1)


def test_standin_slow_switch_delays_the_answer(registry):
    """test_standin_slow_switch_delays_the_answer"""
    import time

    registry.set("slow", True, delay=0.6)
    started = time.monotonic()
    assert _get(registry, "/api/v2/studies/NCT03412565")[0] == 200
    assert time.monotonic() - started >= 0.55
    registry.set("slow", False)
    started = time.monotonic()
    _get(registry, "/api/v2/studies/NCT03412565")
    assert time.monotonic() - started < 0.5


def test_standin_revise_switch_makes_the_next_check_find_a_change(registry, through_ctgov, tmp_path):
    """test_standin_revise_switch_makes_the_next_check_find_a_change"""
    conn = storage.connect(str(tmp_path / "t.db"))
    list_id = monitor.create_list(conn, "L")
    monitor.add(conn, "NCT03412565", list_id)
    assert monitor.check(conn, "NCT03412565")["outcome"] == "unchanged"
    registry.set("revise")
    result = monitor.check(conn, "NCT03412565")
    assert result["outcome"] == "updated"
    moved = {c["field"] for c in storage.list_changes(conn, "NCT03412565")}
    assert len(moved) >= 3, moved
    conn.close()


def test_standin_register_switch_makes_the_next_saved_search_run_find_a_new_match(registry, through_ctgov, tmp_path):
    """test_standin_register_switch_makes_the_next_saved_search_run_find_a_new_match"""
    conn = storage.connect(str(tmp_path / "t.db"))
    list_id = monitor.create_list(conn, "L")
    for nct in ("NCT03412565", "NCT00000002", "NCT00000003"):
        monitor.add(conn, nct, list_id)
    storage.set_list_search(conn, list_id, {"cond": "anything"})
    assert monitor.find_new(conn, list_id)["outcome"] == "nothing_found"
    registry.set("register")
    result = monitor.find_new(conn, list_id)
    assert result["outcome"] == "found" and result["found"] == [standin_registry.REGISTERED_ID]
    conn.close()
