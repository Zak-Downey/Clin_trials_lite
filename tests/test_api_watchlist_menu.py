"""Rename and delete a watchlist through the API (ticket 13).

Uses the suite's stub server: two watchlists, three trials from the captured record
(two in list 1, one shared with list 2). Lacks: a rename racing a check, hundreds of
watchlists.
"""

from __future__ import annotations

import monitor
import storage


def seeded(api, record, restyled, make_fetcher):
    conn = storage.connect(api.path)
    served = {n: restyled(record, n) for n in ("NCT00000001", "NCT00000002", "NCT00000003")}
    fetch = make_fetcher(served)
    other = monitor.create_list(conn, "Other", when="2026-11-01T08:00:00+00:00")
    for nct, lists in (("NCT00000001", (1,)), ("NCT00000002", (1, other)), ("NCT00000003", (other,))):
        monitor.add(conn, nct, lists[0], fetch=fetch, when="2026-11-01T08:00:00+00:00")
        for extra in lists[1:]:
            storage.add_member(conn, extra, nct)
    storage.add_change(conn, "NCT00000001", {"field": "enrollment", "previous": 1, "current": 2}, "2026-11-02T08:00:00+00:00")
    conn.close()
    return other, fetch


def test_rename_changes_the_name_and_keeps_what_the_watchlist_holds(api, record, restyled, make_fetcher):
    """test_rename_changes_the_name_and_keeps_what_the_watchlist_holds"""
    other, _ = seeded(api, record, restyled, make_fetcher)
    status, body = api.post("/api/watchlists/1/rename", {"name": "  Myeloma renamed "})
    assert status == 200 and body["watchlist"]["name"] == "Myeloma renamed"
    assert body["watchlist"]["trial_count"] == 2
    assert [w["name"] for w in body["watchlists"]] == [w["name"] for w in api.get("/api/watchlists")[1]["watchlists"]]


def test_rename_refuses_an_empty_or_duplicate_name_and_keeps_the_old_one(api, record, restyled, make_fetcher):
    """test_rename_refuses_an_empty_or_duplicate_name_and_keeps_the_old_one"""
    seeded(api, record, restyled, make_fetcher)
    before = api.get("/api/watchlists")[1]["watchlists"][0]["name"]
    assert api.post("/api/watchlists/1/rename", {"name": "  "}) [1]["error"]["kind"] == "name_empty"
    status, body = api.post("/api/watchlists/1/rename", {"name": "other"})
    assert (status, body["error"]["kind"]) == (409, "name_taken")
    assert api.get("/api/watchlists")[1]["watchlists"][0]["name"] == before
    assert api.post("/api/watchlists/999/rename", {"name": "x"})[0] == 404


def test_deleting_a_watchlist_keeps_every_trials_history_and_trials_in_another_list_keep_being_checked(
    api, record, restyled, make_fetcher
):
    """test_deleting_a_watchlist_keeps_every_trials_history_and_trials_in_another_list_keep_being_checked"""
    other, fetch = seeded(api, record, restyled, make_fetcher)
    conn = storage.connect(api.path)
    snapshots = {n: storage.count_snapshots(conn, n) for n in ("NCT00000001", "NCT00000002", "NCT00000003")}
    status, body = api.post("/api/watchlists/1/delete")
    assert status == 200 and [w["id"] for w in body["watchlists"]] == [other]
    assert api.get("/api/watchlists/1/needs-review")[0] == 404
    # Every trial, snapshot and change is still there.
    assert {n: storage.count_snapshots(conn, n) for n in snapshots} == snapshots
    assert [c["field"] for c in storage.list_changes(conn, "NCT00000001")] == ["enrollment"]
    # NCT00000001 held only by the deleted list: no longer checked. The other two still are.
    assert storage.lists_holding(conn, "NCT00000001") == []
    assert [t["nct_id"] for t in storage.list_trials(conn, other)] == ["NCT00000002", "NCT00000003"]
    assert [e["kind"] for e in storage.monitoring_events(conn, "NCT00000001")] == ["stopped"]
    assert storage.monitoring_events(conn, "NCT00000002") == []
    assert api.post("/api/watchlists/1/delete")[0] == 404
    conn.close()
