"""The Summary tab's API: periods, grouping, the plain text and the CSV (ticket 12).

Uses the captured NCT03412565 record restyled into three trials in one watchlist,
with the machine's zone set to Asia/Tokyo so a stamp's local day differs from its
UTC day. NCT03412565 moved a field in two checks (enrolment twice) and one other
field; NCT00000002 has one simulated change; NCT00000003 one reviewed change.
Lacks: a second watchlist, a trial with no stored title, a value with a comma-free
simple shape (the CSV test uses a value with a comma and a quote).
"""

from __future__ import annotations

import csv
import io
import time

import pytest

import monitor
import storage

LIST_ID = 1
TODAY = "2026-11-08"  # a Sunday: the week is 2-8 November
CHECK_A = "2026-11-03T03:00:00+00:00"  # 12:00 in Tokyo, 3 Nov
CHECK_B = "2026-11-08T20:00:00+00:00"  # 5:00 on 9 Nov in Tokyo: outside the week, inside the next
CHECK_OLD = "2026-10-20T10:00:00+00:00"


@pytest.fixture(autouse=True)
def tokyo(monkeypatch):
    monkeypatch.setenv("TZ", "Asia/Tokyo")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


@pytest.fixture
def seeded(api, record, restyled):
    conn = storage.connect(api.path)
    acronym_record = restyled(record, "NCT00000002")
    acronym_record["protocolSection"]["identificationModule"]["acronym"] = "ACRO"
    third = restyled(record, "NCT00000003")
    for nct, rec in (("NCT03412565", record), ("NCT00000002", acronym_record), ("NCT00000003", third)):
        monitor.add(conn, nct, LIST_ID, fetch=lambda _n, rec=rec: rec, when="2026-10-01T08:00:00+00:00")
    storage.add_change(conn, "NCT03412565", {"field": "enrollment", "previous": 10, "current": 20}, CHECK_A)
    storage.add_change(conn, "NCT03412565", {"field": "briefTitle", "previous": "Old, \"quoted\"", "current": "New"}, CHECK_A)
    storage.add_change(conn, "NCT03412565", {"field": "enrollment", "previous": 20, "current": 30}, CHECK_B)
    storage.add_change(conn, "NCT03412565", {"field": "enrollment", "previous": 5, "current": 10}, CHECK_OLD)
    storage.add_change(conn, "NCT00000002", {"field": "enrollment", "previous": 1, "current": 2}, CHECK_A, synthetic=True)
    storage.add_change(conn, "NCT00000003", {"field": "enrollment", "previous": 1, "current": 2}, CHECK_A)
    storage.mark_reviewed(conn, "NCT00000003", CHECK_B)
    conn.close()
    return api


def summary(api, query):
    status, body = api.get(f"/api/watchlists/{LIST_ID}/summary?today={TODAY}&{query}")
    assert status == 200, body
    return body


def test_this_week_runs_monday_to_sunday_and_filters_on_detection_in_the_local_zone(seeded):
    """test_this_week_runs_monday_to_sunday_and_filters_on_detection_in_the_local_zone"""
    body = summary(seeded, "period=week")
    assert (body["period"]["start"], body["period"]["end"]) == ("2026-11-02", "2026-11-08")
    # CHECK_B is 9 Nov in Tokyo: outside; CHECK_OLD is October.
    assert body["counts"]["field_changes"] == 4
    assert body["counts"]["trials"] == 3
    assert sorted(t["nct_id"] for t in body["trials"]) == ["NCT00000002", "NCT00000003", "NCT03412565"]


def test_this_month_is_the_calendar_month_and_reviewed_changes_stay_in(seeded):
    """test_this_month_is_the_calendar_month_and_reviewed_changes_stay_in"""
    body = summary(seeded, "period=month")
    assert (body["period"]["start"], body["period"]["end"]) == ("2026-11-01", "2026-11-30")
    # CHECK_B (9 Nov local) is now in; the reviewed trial counts as reviewed, not absent.
    assert body["counts"]["field_changes"] == 5
    assert body["counts"]["reviewed"] == 1 and body["counts"]["awaiting_review"] == 4
    assert body["zone"] == "JST"


def test_a_custom_range_is_inclusive_and_validated(seeded):
    """test_a_custom_range_is_inclusive_and_validated"""
    body = summary(seeded, "period=custom&from=2026-10-20&to=2026-10-20")
    assert body["counts"]["field_changes"] == 1
    for query in ("period=custom&from=2026-11-05&to=2026-11-01", "period=custom&from=2026-11-05",
                  "period=custom&from=nope&to=2026-11-01", "period=year"):
        status, err = seeded.get(f"/api/watchlists/{LIST_ID}/summary?{query}")
        assert status == 400 and err["error"]["kind"] == "invalid_request"


def test_an_unknown_watchlist_has_no_summary(seeded):
    """test_an_unknown_watchlist_has_no_summary"""
    status, err = seeded.get("/api/watchlists/99/summary?period=week")
    assert status == 404 and err["error"]["kind"] == "watchlist_not_found"


def test_the_summary_keeps_every_transition_of_a_field_that_moved_in_two_checks_in_order(seeded):
    """test_the_summary_keeps_every_transition_of_a_field_that_moved_in_two_checks_in_order"""
    body = summary(seeded, "period=month")
    trial = next(t for t in body["trials"] if t["nct_id"] == "NCT03412565")
    assert trial["change_count"] == 3 and trial["check_count"] == 2
    # Newest check first; inside it, every transition.
    assert [sorted(c["field"] for c in check["changes"]) for check in trial["checks"]] == [
        ["enrollment"], ["briefTitle", "enrollment"]]
    assert [c["detected_at"]["iso"] for c in trial["checks"]] == [
        "2026-11-09T05:00:00+09:00", "2026-11-03T12:00:00+09:00"]
    enrol = [(c["previous"], c["current"]) for check in trial["checks"] for c in check["changes"]
             if c["field"] == "enrollment"]
    assert enrol == [("20", "30"), ("10", "20")]
    # The latest-change line names the newest check's fields only, not the older check's title.
    assert trial["latest"] == "Latest: enrollment updated."


def test_trials_carry_heading_link_and_simulated_flag(seeded):
    """test_trials_carry_heading_link_and_simulated_flag"""
    body = summary(seeded, "period=week")
    by = {t["nct_id"]: t for t in body["trials"]}
    assert by["NCT00000002"]["heading"] == "ACRO"
    assert by["NCT00000002"]["simulated"] is True and by["NCT03412565"]["simulated"] is False
    assert by["NCT00000002"]["checks"][0]["changes"][0]["simulated"] is True
    assert by["NCT03412565"]["url"].endswith("/NCT03412565")


def test_the_text_has_each_trials_registry_link(seeded):
    """test_the_text_has_each_trials_registry_link"""
    body = summary(seeded, "period=week")
    for nct in ("NCT03412565", "NCT00000002", "NCT00000003"):
        assert f"https://clinicaltrials.gov/study/{nct}" in body["text"]


def test_the_csv_has_one_row_per_field_change_with_the_agreed_columns(seeded):
    """test_the_csv_has_one_row_per_field_change_with_the_agreed_columns"""
    body = summary(seeded, "period=month")
    rows = list(csv.DictReader(io.StringIO(body["csv"].removeprefix("\ufeff"))))
    assert list(rows[0]) == ["Watchlist", "NCT ID", "Title", "Field", "Previous value", "New value",
                             "Registry updated", "Detected", "Review status", "Simulated", "Registry record"]
    assert len(rows) == 5
    title = next(r for r in rows if r["Previous value"].startswith("Old"))
    assert title["Previous value"] == 'Old, "quoted"'
    assert title["Detected"] == "2026-11-03T12:00:00+09:00"
    assert title["Registry updated"] and title["Review status"] == "Awaiting review"
    assert {r["Review status"] for r in rows if r["NCT ID"] == "NCT00000003"} == {"Reviewed"}
    assert [r["Simulated"] for r in rows if r["NCT ID"] == "NCT00000002"] == ["Simulated"]
    assert body["filename"].endswith("2026-11-01-to-2026-11-30.csv")


def test_an_empty_period_has_no_file_and_says_so(seeded):
    """test_an_empty_period_has_no_file_and_says_so"""
    body = summary(seeded, "period=custom&from=2026-01-01&to=2026-01-31")
    assert body["counts"] == {"trials": 0, "field_changes": 0, "awaiting_review": 0, "reviewed": 0}
    assert body["trials"] == [] and body["csv"] is None


def test_the_latest_line_names_the_newest_check_whatever_the_field_order(seeded):
    """test_the_latest_line_names_the_newest_check_whatever_the_field_order"""
    conn = storage.connect(seeded.path)
    storage.add_change(conn, "NCT00000003", {"field": "briefTitle", "previous": "A", "current": "B"}, CHECK_B)
    conn.close()
    body = summary(seeded, "period=month")
    trial = next(t for t in body["trials"] if t["nct_id"] == "NCT00000003")
    assert trial["latest"] == "Latest: brief title updated."


def test_the_csv_starts_with_a_byte_order_mark_and_reads_back_in_utf8_sig(seeded):
    """test_the_csv_starts_with_a_byte_order_mark_and_reads_back_in_utf8_sig"""
    conn = storage.connect(seeded.path)
    storage.add_change(conn, "NCT00000003", {"field": "briefTitle", "previous": None, "current": "B"}, CHECK_A)
    conn.close()
    text = summary(seeded, "period=month")["csv"]
    assert text.startswith("\ufeff")
    rows = list(csv.DictReader(io.StringIO(text.encode("utf-8").decode("utf-8-sig"))))
    assert list(rows[0])[0] == "Watchlist"
    assert "\u2014" in {v for r in rows for v in r.values()}


def test_a_title_that_looks_like_a_formula_is_prefixed_in_the_csv_only(seeded):
    """test_a_title_that_looks_like_a_formula_is_prefixed_in_the_csv_only"""
    conn = storage.connect(seeded.path)
    storage.add_change(conn, "NCT00000003", {"field": "briefTitle", "previous": "=1+1", "current": "@x"}, CHECK_A)
    conn.close()
    body = summary(seeded, "period=month")
    rows = list(csv.DictReader(io.StringIO(body["csv"].removeprefix("\ufeff"))))
    row = next(r for r in rows if r["Previous value"].endswith("=1+1"))
    assert row["Previous value"] == "'=1+1" and row["New value"] == "'@x"
    assert "=1+1" in body["text"] and "'=1+1" not in body["text"]
    page = next(t for t in body["trials"] if t["nct_id"] == "NCT00000003")
    assert any(c["previous"] == "=1+1" for ck in page["checks"] for c in ck["changes"])
