"""GET /api/search: one page of a registry search, its true total and the cap.

Uses the captured NCT03412565 record restyled into as many studies as a test
needs, behind a stub page finder. Lacks: the live registry's real paging.
"""

from __future__ import annotations

import threading

import pytest

from webapp.server import make_server


@pytest.fixture
def search_api(tmp_path, record, restyled):
    import json
    import urllib.error
    import urllib.request

    state = {"total": 0, "failure": None, "calls": []}

    def find_page(page=1, page_size=10, **axes):
        state["calls"].append({"page": page, "page_size": page_size, **axes})
        if state["failure"]:
            raise state["failure"]
        total = state["total"]
        first = (page - 1) * page_size
        ids = [f"NCT{n:08d}" for n in range(first + 1, min(total, first + page_size) + 1)]
        return {"studies": [restyled(record, i) for i in ids], "total": total}

    server = make_server(str(tmp_path / "s.db"), find_page=find_page)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    class Client:
        s = state

        def get(self, route):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}{route}", timeout=10) as r:
                    return r.status, json.loads(r.read())
            except urllib.error.HTTPError as err:
                return err.code, json.loads(err.read())

    yield Client()
    server.shutdown()
    server.server_close()


def test_a_search_returns_ten_rows_and_the_registrys_total(search_api):
    search_api.s["total"] = 27
    status, body = search_api.get("/api/search?cond=myeloma")
    assert status == 200
    assert len(body["rows"]) == 10
    assert body["total"] == 27 and body["page"] == 1 and body["pages"] == 3
    assert body["capped"] is False
    assert body["rows"][0]["nct_id"] == "NCT00000001"
    assert {"title", "sponsor", "phase", "status"} <= set(body["rows"][0])


def test_the_last_page_is_short_and_page_two_starts_at_eleven(search_api):
    search_api.s["total"] = 27
    _, body = search_api.get("/api/search?cond=myeloma&page=3")
    assert [r["nct_id"] for r in body["rows"]][0] == "NCT00000021"
    assert len(body["rows"]) == 7


def test_over_one_hundred_matches_the_cap_applies_and_the_total_stays_true(search_api):
    search_api.s["total"] = 5214
    _, body = search_api.get("/api/search?cond=myeloma&page=10")
    assert body["total"] == 5214 and body["capped"] is True and body["pages"] == 10
    assert len(body["rows"]) == 10


def test_exactly_one_hundred_is_not_capped(search_api):
    search_api.s["total"] = 100
    _, body = search_api.get("/api/search?cond=myeloma")
    assert body["capped"] is False and body["pages"] == 10


def test_a_page_past_the_cap_is_refused(search_api):
    search_api.s["total"] = 5214
    status, body = search_api.get("/api/search?cond=myeloma&page=11")
    assert status == 400 and body["error"]["kind"] == "bad_page"


def test_every_axis_reaches_the_finder(search_api):
    search_api.s["total"] = 1
    search_api.get(
        "/api/search?cond=a&intr=b&spons=c&phase=PHASE2&phase=PHASE3&sponsor_type=INDUSTRY"
        "&status=RECRUITING&status=COMPLETED&started_from=2020-01&started_to=2021-01&page=1")
    call = search_api.s["calls"][0]
    assert call["cond"] == "a" and call["intr"] == "b" and call["spons"] == "c"
    assert list(call["phases"]) == ["PHASE2", "PHASE3"]
    assert list(call["sponsor_types"]) == ["INDUSTRY"]
    assert list(call["statuses"]) == ["RECRUITING", "COMPLETED"]
    assert call["started_from"] == "2020-01" and call["started_to"] == "2021-01"
    assert call["page"] == 1 and call["page_size"] == 10


def test_a_query_with_none_of_the_four_naming_fields_is_refused_without_a_registry_call(search_api):
    status, body = search_api.get("/api/search?status=RECRUITING")
    assert status == 400 and body["error"]["kind"] == "nothing_asked"
    assert search_api.s["calls"] == []


def test_zero_matches_is_an_empty_page_not_an_error(search_api):
    search_api.s["total"] = 0
    status, body = search_api.get("/api/search?cond=zzz")
    assert status == 200 and body["rows"] == [] and body["total"] == 0 and body["pages"] == 0


def test_a_registry_failure_is_a_502_with_its_kind(search_api):
    search_api.s["failure"] = RuntimeError("boom")
    status, body = search_api.get("/api/search?cond=x")
    assert status == 502 and body["error"]["kind"] == "registry_error"
