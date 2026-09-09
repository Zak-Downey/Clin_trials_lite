"""The change summary an analyst gets out of the tool.

The last mile out of this app is a briefing pasted into an email or a tracker,
not a page read on screen. So the summary is tested as what it produces: the
text somebody copies, and the CSV somebody opens in a spreadsheet.

Every test drives real checks through the fetching seam at controlled times, so
the registry dates and the detection dates are the ones the app really stores
rather than rows written straight into the tables.
"""

from __future__ import annotations

import copy
import csv
import datetime
import io

import pytest

import briefing
import display
import monitor
import simulate
import storage

NCT = "NCT03412565"


def revised(record: dict, registry_date: str, **edits) -> dict:
    """A copy of the record the sponsor has edited, with a fresh registry stamp.

    Each edit names a monitored field in the words of the registry module it
    lives in, so a test says what the sponsor did rather than how the record is
    shaped.
    """
    moved = copy.deepcopy(record)
    protocol = moved["protocolSection"]
    protocol["statusModule"]["lastUpdatePostDateStruct"]["date"] = registry_date

    if "status" in edits:
        protocol["statusModule"]["overallStatus"] = edits["status"]
    if "enrolment" in edits:
        protocol["designModule"]["enrollmentInfo"]["count"] = edits["enrolment"]
    if "title" in edits:
        protocol["identificationModule"]["officialTitle"] = edits["title"]
    if "completion" in edits:
        protocol["statusModule"]["completionDateStruct"]["date"] = edits["completion"]
    if "completion_type" in edits:
        protocol["statusModule"]["completionDateStruct"]["type"] = edits["completion_type"]
    return moved


@pytest.fixture
def watched(conn, record, fetcher):
    """One trial baselined before any of the checks below."""
    monitor.add(conn, NCT, fetch=fetcher, when="2026-01-01T00:00:00+00:00")
    return conn


@pytest.fixture
def detect(watched, record, make_fetcher):
    """Run one real check against an edited record, at a chosen moment.

    Edits accumulate, the way a sponsor's do: a second check serves the record
    the first one left behind, so a field nobody touched again stands still.
    """
    served = {"record": record}

    def run(detected: str, registry_date: str, **edits):
        served["record"] = revised(served["record"], registry_date, **edits)
        fetch = make_fetcher({NCT: served["record"]})
        return monitor.check(watched, NCT, fetch=fetch, when=detected)

    return run


def only_list(conn) -> int:
    return storage.list_lists(conn)[0]["id"]


def summary(conn, start: str, end: str) -> dict:
    """The summary for the one list, over a range given as two ISO dates."""
    return briefing.summarise(
        conn,
        only_list(conn),
        datetime.date.fromisoformat(start),
        datetime.date.fromisoformat(end),
    )


def rows_of(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text)))


def fields_in(summary: dict, nct_id: str = NCT) -> list[str]:
    entry = next(e for e in summary["entries"] if e["nct_id"] == nct_id)
    return [move["field"] for move in entry["moves"]]


# --- the date range


def test_a_change_detected_on_the_first_day_of_the_range_is_in_it(watched, detect):
    detect("2026-03-01T09:00:00+00:00", "2026-02-27", enrolment=300)

    assert fields_in(summary(watched, "2026-03-01", "2026-03-31")) == ["enrollment"]


def test_a_change_detected_on_the_last_day_of_the_range_is_in_it(watched, detect):
    detect("2026-03-31T23:30:00+00:00", "2026-03-30", enrolment=300)

    assert fields_in(summary(watched, "2026-03-01", "2026-03-31")) == ["enrollment"]


def test_a_change_detected_the_day_before_the_range_is_out_of_it(watched, detect):
    detect("2026-02-28T23:30:00+00:00", "2026-02-27", enrolment=300)

    assert summary(watched, "2026-03-01", "2026-03-31")["entries"] == []


def test_a_change_detected_the_day_after_the_range_is_out_of_it(watched, detect):
    detect("2026-04-01T00:30:00+00:00", "2026-03-30", enrolment=300)

    assert summary(watched, "2026-03-01", "2026-03-31")["entries"] == []


def test_a_range_reports_only_the_checks_inside_it(watched, detect):
    detect("2026-02-20T09:00:00+00:00", "2026-02-19", enrolment=300)
    detect("2026-03-10T09:00:00+00:00", "2026-03-09", enrolment=310)
    detect("2026-04-10T09:00:00+00:00", "2026-04-09", enrolment=320)

    reported = summary(watched, "2026-03-01", "2026-03-31")

    assert [m["current"] for m in reported["entries"][0]["moves"]] == [310]


# --- what one entry says


def test_the_summary_names_the_list_it_is_for(conn, record, fetcher):
    myeloma = monitor.create_list(conn, "Myeloma")
    monitor.add(conn, NCT, myeloma, fetch=fetcher)

    reported = briefing.summarise(
        conn, myeloma, datetime.date(2026, 3, 1), datetime.date(2026, 3, 31)
    )

    assert reported["list_name"] == "Myeloma"
    assert "Myeloma" in briefing.as_text(reported)


def test_an_entry_names_the_trial_and_links_to_the_registry_record(watched, detect):
    detect("2026-03-10T09:00:00+00:00", "2026-03-09", enrolment=300)

    entry = summary(watched, "2026-03-01", "2026-03-31")["entries"][0]

    assert entry["nct_id"] == NCT
    assert entry["title"]
    assert entry["url"] == f"{display.STUDY_URL}/{NCT}"


def test_a_move_carries_both_values(watched, detect, record):
    detect("2026-03-10T09:00:00+00:00", "2026-03-09", enrolment=300)

    move = summary(watched, "2026-03-01", "2026-03-31")["entries"][0]["moves"][0]

    assert move["previous"] == record["protocolSection"]["designModule"]["enrollmentInfo"]["count"]
    assert move["current"] == 300


def test_a_move_carries_the_registry_date_and_the_detection_date_apart(watched, detect):
    detect("2026-03-10T09:00:00+00:00", "2026-02-14", enrolment=300)

    move = summary(watched, "2026-03-01", "2026-03-31")["entries"][0]["moves"][0]

    assert move["registry_updated"] == "2026-02-14"
    assert move["detected"] == "2026-03-10T09:00:00+00:00"


def test_a_date_and_its_type_moving_together_are_one_entry(watched, detect):
    detect(
        "2026-03-10T09:00:00+00:00",
        "2026-03-09",
        completion="2026-10-31",
        completion_type="ACTUAL",
    )

    move = next(
        m
        for m in summary(watched, "2026-03-01", "2026-03-31")["entries"][0]["moves"]
        if m["field"] == "completionDate"
    )

    assert move["current"] == "2026-10-31"
    assert move["qualifier"] == "ACTUAL"
    assert "completionDateType" not in fields_in(summary(watched, "2026-03-01", "2026-03-31"))


def test_a_trial_that_did_not_move_in_the_range_gets_no_entry(watched, detect, record, make_fetcher):
    monitor.check(watched, NCT, fetch=make_fetcher({NCT: record}), when="2026-03-10T09:00:00+00:00")

    assert summary(watched, "2026-03-01", "2026-03-31")["entries"] == []


# --- ordering


def test_fields_are_ordered_high_signal_first_within_a_trial(watched, detect):
    detect(
        "2026-03-10T09:00:00+00:00",
        "2026-03-09",
        title="A study of something, amended",
        status="TERMINATED",
    )

    fields = fields_in(summary(watched, "2026-03-01", "2026-03-31"))

    assert fields[0] == "overallStatus"
    assert "officialTitle" in fields
    assert fields.index("overallStatus") < fields.index("officialTitle")


def test_moves_from_several_checks_are_gathered_under_one_trial(watched, detect):
    detect("2026-03-05T09:00:00+00:00", "2026-03-04", enrolment=300)
    detect("2026-03-20T09:00:00+00:00", "2026-03-19", status="TERMINATED")

    entries = summary(watched, "2026-03-01", "2026-03-31")["entries"]

    assert len(entries) == 1
    assert fields_in(summary(watched, "2026-03-01", "2026-03-31"))[0] == "overallStatus"
    assert len(entries[0]["moves"]) == 2


# --- reviewed and unreviewed alike


def test_a_reviewed_change_still_appears_in_the_briefing(watched, detect):
    detect("2026-03-10T09:00:00+00:00", "2026-03-09", enrolment=300)
    monitor.review(watched, NCT)

    reported = summary(watched, "2026-03-01", "2026-03-31")

    assert fields_in(reported) == ["enrollment"]
    assert NCT in briefing.as_text(reported)


def test_reviewed_and_unreviewed_changes_both_appear(watched, detect):
    detect("2026-03-05T09:00:00+00:00", "2026-03-04", enrolment=300)
    monitor.review(watched, NCT)
    detect("2026-03-20T09:00:00+00:00", "2026-03-19", status="TERMINATED")

    assert sorted(fields_in(summary(watched, "2026-03-01", "2026-03-31"))) == [
        "enrollment",
        "overallStatus",
    ]


# --- the two forms


def test_the_text_names_the_trial_its_fields_and_both_values(watched, detect):
    detect("2026-03-10T09:00:00+00:00", "2026-02-14", enrolment=300)

    text = briefing.as_text(summary(watched, "2026-03-01", "2026-03-31"))

    assert NCT in text
    assert f"{display.STUDY_URL}/{NCT}" in text
    assert display.label("enrollment") in text
    assert "300" in text
    assert "14 February 2026" in text
    assert "10 March 2026" in text


def test_the_csv_carries_one_row_per_move_with_both_dates(watched, detect):
    detect("2026-03-10T09:00:00+00:00", "2026-02-14", enrolment=300)

    rows = rows_of(briefing.as_csv(summary(watched, "2026-03-01", "2026-03-31")))

    assert len(rows) == 1
    assert rows[0]["NCT ID"] == NCT
    assert rows[0]["Field"] == display.label("enrollment")
    # Enrolment carries the registry's word for it, which travels with the value.
    assert rows[0]["Current"].startswith("300")
    assert rows[0]["Registry updated"] == "2026-02-14"
    assert rows[0]["Detected"] == "2026-03-10"
    assert rows[0]["Registry record"] == f"{display.STUDY_URL}/{NCT}"


def test_both_forms_report_the_same_moves(watched, detect):
    detect("2026-03-10T09:00:00+00:00", "2026-03-09", enrolment=300, status="TERMINATED")

    reported = summary(watched, "2026-03-01", "2026-03-31")
    text = briefing.as_text(reported)
    rows = rows_of(briefing.as_csv(reported))

    assert len(rows) == len(reported["entries"][0]["moves"])
    for row in rows:
        assert row["Field"] in text


def test_the_text_leads_on_the_high_signal_move(watched, detect):
    """The form most briefings are pasted from, so the ordering is pinned here too."""
    detect(
        "2026-03-10T09:00:00+00:00",
        "2026-03-09",
        title="A study of something, amended",
        status="TERMINATED",
    )

    moves = [
        line
        for line in briefing.as_text(summary(watched, "2026-03-01", "2026-03-31")).splitlines()
        if line.startswith("- ")
    ]

    assert moves[0].startswith(f"- {display.label('overallStatus')}:")


def test_the_csv_keeps_the_high_signal_ordering(watched, detect):
    detect(
        "2026-03-10T09:00:00+00:00",
        "2026-03-09",
        title="A study of something, amended",
        status="TERMINATED",
    )

    rows = rows_of(briefing.as_csv(summary(watched, "2026-03-01", "2026-03-31")))

    assert rows[0]["Field"] == display.label("overallStatus")


def test_a_multi_line_value_stays_on_one_line_of_the_text(watched, detect, record, make_fetcher):
    amended = copy.deepcopy(record)
    amended["protocolSection"]["statusModule"]["lastUpdatePostDateStruct"]["date"] = "2026-03-09"
    amended["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = (
        "Inclusion Criteria:\n\n* Aged 18 or over\n* Measurable disease"
    )
    monitor.check(
        watched, NCT, fetch=make_fetcher({NCT: amended}), when="2026-03-10T09:00:00+00:00"
    )

    text = briefing.as_text(summary(watched, "2026-03-01", "2026-03-31"))

    assert "Aged 18 or over" in text
    assert not any(line.strip() == "* Aged 18 or over" for line in text.splitlines())


# --- simulated data, marked in both


@pytest.fixture
def simulated(watched, record, make_fetcher):
    """A change found against a rewound history, which is a simulated one."""
    simulate.rewind(watched, NCT, when="2026-03-09T09:00:00+00:00")
    monitor.check(
        watched, NCT, fetch=make_fetcher({NCT: record}), when="2026-03-10T09:00:00+00:00"
    )
    return watched


def test_a_simulated_move_is_marked_in_the_summary(simulated):
    reported = summary(simulated, "2026-03-01", "2026-03-31")

    assert all(move["synthetic"] for move in reported["entries"][0]["moves"])
    assert reported["entries"][0]["synthetic"]


def test_a_simulated_move_is_marked_in_the_text(simulated):
    text = briefing.as_text(summary(simulated, "2026-03-01", "2026-03-31"))

    assert display.SYNTHETIC in text


def test_a_simulated_move_is_marked_in_every_csv_row(simulated):
    rows = rows_of(briefing.as_csv(summary(simulated, "2026-03-01", "2026-03-31")))

    assert rows
    assert all(row["Synthetic"] == briefing.SYNTHETIC for row in rows)


def test_a_real_move_is_not_marked_as_simulated(watched, detect):
    detect("2026-03-10T09:00:00+00:00", "2026-03-09", enrolment=300)

    reported = summary(watched, "2026-03-01", "2026-03-31")

    assert display.SYNTHETIC not in briefing.as_text(reported)
    assert rows_of(briefing.as_csv(reported))[0]["Synthetic"] == ""


# --- an empty range


def test_an_empty_range_says_so_rather_than_reading_as_a_fault(watched, detect):
    detect("2026-02-20T09:00:00+00:00", "2026-02-19", enrolment=300)

    text = briefing.as_text(summary(watched, "2026-03-01", "2026-03-31"))

    assert "No changes" in text
    assert "1 March 2026" in text
    assert "31 March 2026" in text


def test_an_empty_range_produces_no_file(watched):
    assert briefing.as_csv(summary(watched, "2026-03-01", "2026-03-31")) is None


def test_an_empty_list_produces_no_file_either(conn):
    reported = summary(conn, "2026-03-01", "2026-03-31")

    assert briefing.as_csv(reported) is None
    assert "No changes" in briefing.as_text(reported)


# --- the presets


def test_this_week_runs_from_monday_to_today():
    start, end = briefing.preset_range(briefing.THIS_WEEK, datetime.date(2026, 9, 9))

    assert (start, end) == (datetime.date(2026, 9, 7), datetime.date(2026, 9, 9))


def test_this_month_runs_from_the_first_to_today():
    start, end = briefing.preset_range(briefing.THIS_MONTH, datetime.date(2026, 9, 9))

    assert (start, end) == (datetime.date(2026, 9, 1), datetime.date(2026, 9, 9))


def test_a_custom_range_is_left_to_the_reader():
    assert briefing.preset_range(briefing.CUSTOM, datetime.date(2026, 9, 9)) is None


def test_the_file_is_named_for_the_list_and_the_range(watched):
    named = briefing.filename(summary(watched, "2026-03-01", "2026-03-31"))

    assert named.endswith(".csv")
    assert "2026-03-01" in named and "2026-03-31" in named
