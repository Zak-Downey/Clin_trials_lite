"""Searching the registry on four axes, and filing what comes back.

A medical affairs lead does not think in NCT IDs; they think "everything
Janssen has in phase 3 for multiple myeloma". That query, the rows it returns,
and what happens when several of them are added to a list are all tested here
without touching the network: the registry call is the seam, stubbed the same
way the single-trial fetch already is.
"""

from __future__ import annotations

import urllib.error

import pytest

import ctgov
import monitor
import storage


# --- the four fields becoming registry query parameters


def test_a_condition_becomes_the_registrys_condition_parameter():
    assert ctgov.search_params(cond="multiple myeloma") == {"query.cond": "multiple myeloma"}


def test_all_four_axes_travel_together():
    params = ctgov.search_params(
        cond="multiple myeloma", intr="daratumumab", spons="Janssen", phases=("PHASE3",)
    )

    assert params == {
        "query.cond": "multiple myeloma",
        "query.intr": "daratumumab",
        "query.spons": "Janssen",
        "filter.advanced": "AREA[Phase](PHASE3)",
    }


def test_several_phases_are_asked_for_as_any_of_them():
    params = ctgov.search_params(phases=("PHASE2", "PHASE3"))

    assert params["filter.advanced"] == "AREA[Phase](PHASE2 OR PHASE3)"


def test_a_blank_axis_is_left_out_rather_than_sent_empty():
    assert ctgov.search_params(cond="  ", intr="daratumumab") == {"query.intr": "daratumumab"}


def test_a_query_with_nothing_in_it_has_no_parameters():
    assert ctgov.search_params() == {}


# --- the three narrowing axes
#
# Sponsor class, status and start date do not name a programme; they say which
# of the studies already named are worth reading. Each goes through the
# advanced filter, so what is asserted here is the expression they build and,
# above all, that they AND together rather than replacing one another.


def test_a_sponsor_class_becomes_an_advanced_filter():
    params = ctgov.search_params(cond="cll", sponsor_types=("INDUSTRY",))

    assert params["filter.advanced"] == "AREA[LeadSponsorClass](INDUSTRY)"


def test_several_sponsor_classes_are_asked_for_as_any_of_them():
    params = ctgov.search_params(sponsor_types=("INDUSTRY", "NIH"))

    assert params["filter.advanced"] == "AREA[LeadSponsorClass](INDUSTRY OR NIH)"


def test_a_status_becomes_an_advanced_filter():
    params = ctgov.search_params(statuses=("RECRUITING",))

    assert params["filter.advanced"] == "AREA[OverallStatus](RECRUITING)"


def test_a_start_window_with_both_ends_is_a_range():
    params = ctgov.search_params(started_from="2024-01-01", started_to="2024-12-31")

    assert params["filter.advanced"] == "AREA[StartDate]RANGE[2024-01-01,2024-12-31]"


def test_a_start_window_open_at_the_far_end_runs_to_max():
    params = ctgov.search_params(started_from="2024-01-01")

    assert params["filter.advanced"] == "AREA[StartDate]RANGE[2024-01-01,MAX]"


def test_a_start_window_open_at_the_near_end_runs_from_min():
    params = ctgov.search_params(started_to="2024-12-31")

    assert params["filter.advanced"] == "AREA[StartDate]RANGE[MIN,2024-12-31]"


def test_every_narrowing_axis_ands_with_the_others_rather_than_replacing_it():
    """The one failure that would silently widen a search instead of narrowing it."""
    params = ctgov.search_params(
        cond="cll",
        phases=("PHASE3",),
        sponsor_types=("INDUSTRY",),
        statuses=("RECRUITING", "NOT_YET_RECRUITING"),
        started_from="2024-01-01",
    )

    assert params["filter.advanced"] == (
        "AREA[Phase](PHASE3)"
        " AND AREA[LeadSponsorClass](INDUSTRY)"
        " AND AREA[OverallStatus](RECRUITING OR NOT_YET_RECRUITING)"
        " AND AREA[StartDate]RANGE[2024-01-01,MAX]"
    )
    assert params["query.cond"] == "cll"


def test_a_narrowing_axis_left_empty_adds_no_filter():
    assert ctgov.search_params(cond="cll", sponsor_types=(), statuses=(), started_from="") == {
        "query.cond": "cll"
    }


# --- searching


def test_a_search_with_every_field_blank_is_refused(make_finder):
    finder = make_finder()

    with pytest.raises(monitor.MonitorError, match="at least one"):
        monitor.search(find=finder)

    assert finder.calls == []


def test_a_study_becomes_a_row_reading_like_the_watchlist(record, make_finder):
    found = monitor.search(cond="multiple myeloma", find=make_finder([record]))

    row = found["rows"][0]
    assert row["nct_id"] == "NCT03412565"
    assert row["sponsor"] == "Janssen Research & Development, LLC"
    assert row["title"]
    assert row["phases"] == ["PHASE2"]
    assert row["status"] == "COMPLETED"
    assert row["conditions"]
    assert row["interventions"]


def test_a_search_carries_the_four_fields_to_the_registry(record, make_finder):
    finder = make_finder([record])

    monitor.search(
        cond="myeloma", intr="daratumumab", spons="Janssen", phases=["PHASE3"], find=finder
    )

    asked = finder.calls[0]
    assert asked["cond"] == "myeloma"
    assert asked["intr"] == "daratumumab"
    assert asked["spons"] == "Janssen"
    assert asked["phases"] == ("PHASE3",)


def test_a_search_matching_nothing_returns_no_rows(make_finder):
    found = monitor.search(cond="nothing at all", find=make_finder([]))

    assert found["rows"] == []
    assert found["capped"] is False


def test_a_result_set_under_the_cap_is_not_called_capped(record, make_finder):
    found = monitor.search(cond="myeloma", limit=3, find=make_finder([record]))

    assert found["capped"] is False


def test_a_result_set_at_the_cap_says_it_is_capped(record, make_finder, restyled):
    studies = [restyled(record, f"NCT0000000{i}") for i in range(4)]

    found = monitor.search(cond="myeloma", limit=3, find=make_finder(studies))

    assert len(found["rows"]) == 3
    assert found["capped"] is True


def test_an_unreachable_registry_is_reported_rather_than_showing_an_empty_table(make_finder):
    finder = make_finder(failure=urllib.error.URLError("down"))

    with pytest.raises(monitor.MonitorError, match="Could not reach"):
        monitor.search(cond="myeloma", find=finder)


# --- filing several results into a list


def test_several_trials_are_added_to_the_chosen_list_at_once(
    conn, record, make_fetcher, restyled
):
    myeloma = monitor.create_list(conn, "Myeloma")
    fetcher = make_fetcher(
        records={"NCT00000001": restyled(record, "NCT00000001")}, default=record
    )

    outcome = monitor.add_many(conn, ["NCT03412565", "NCT00000001"], myeloma, fetch=fetcher)

    assert outcome["added"] == ["NCT03412565", "NCT00000001"]
    assert {t["nct_id"] for t in storage.list_trials(conn, myeloma)} == {
        "NCT03412565",
        "NCT00000001",
    }


def test_a_result_already_in_the_chosen_list_is_reported_not_added_twice(conn, fetcher):
    myeloma = monitor.create_list(conn, "Myeloma")
    monitor.add(conn, "NCT03412565", myeloma, fetch=fetcher)

    outcome = monitor.add_many(conn, ["NCT03412565"], myeloma, fetch=fetcher)

    assert outcome["added"] == []
    assert outcome["already"] == ["NCT03412565"]
    assert len(storage.list_trials(conn, myeloma)) == 1


def test_a_trial_monitored_elsewhere_joins_without_being_refetched(conn, fetcher):
    lung = monitor.create_list(conn, "Lung")
    myeloma = monitor.create_list(conn, "Myeloma")
    monitor.add(conn, "NCT03412565", lung, fetch=fetcher)
    began = storage.get_trial(conn, "NCT03412565")["monitoring_began"]

    monitor.add_many(conn, ["NCT03412565"], myeloma, fetch=fetcher)

    assert fetcher.calls == ["NCT03412565"]
    assert storage.count_snapshots(conn, "NCT03412565") == 1
    assert storage.get_trial(conn, "NCT03412565")["monitoring_began"] == began


def test_one_trial_failing_does_not_stop_the_rest_being_added(conn, record, make_fetcher):
    myeloma = monitor.create_list(conn, "Myeloma")
    fetcher = make_fetcher(
        failures={"NCT00000001": urllib.error.URLError("down")}, default=record
    )

    outcome = monitor.add_many(conn, ["NCT00000001", "NCT03412565"], myeloma, fetch=fetcher)

    assert outcome["added"] == ["NCT03412565"]
    assert [f["nct_id"] for f in outcome["failed"]] == ["NCT00000001"]
    assert [t["nct_id"] for t in storage.list_trials(conn, myeloma)] == ["NCT03412565"]


def test_results_can_be_filed_into_a_list_named_on_the_spot(
    conn, record, make_fetcher, restyled
):
    fetcher = make_fetcher(
        records={"NCT00000001": restyled(record, "NCT00000001")}, default=record
    )

    outcome, made = monitor.add_to_new_list(
        conn, ["NCT03412565", "NCT00000001"], "Myeloma — Janssen", fetch=fetcher
    )

    assert outcome["added"] == ["NCT03412565", "NCT00000001"]
    assert storage.get_list(conn, made)["name"] == "Myeloma — Janssen"


def test_a_new_list_nothing_landed_in_goes_back(conn, make_fetcher):
    failing = make_fetcher(failures={"NCT03412565": urllib.error.URLError("down")})

    with pytest.raises(monitor.MonitorError):
        monitor.add_to_new_list(conn, ["NCT03412565"], "Myeloma", fetch=failing)

    assert storage.find_list(conn, "Myeloma") is None


def test_a_new_list_that_partly_filled_is_kept(conn, record, make_fetcher):
    fetcher = make_fetcher(
        failures={"NCT00000001": urllib.error.URLError("down")}, default=record
    )

    outcome, made = monitor.add_to_new_list(
        conn, ["NCT03412565", "NCT00000001"], "Myeloma", fetch=fetcher
    )

    assert outcome["added"] == ["NCT03412565"]
    assert storage.get_list(conn, made) is not None


# --- the narrowing axes travelling with a query
#
# A query is one shape wherever it goes: run from the form now, or stored
# against a list and re-run on every check. These assert the new axes reach the
# registry from the form, and that the refusal still turns on the four axes
# that name a programme rather than on the three that only narrow one.


def test_the_narrowing_axes_reach_the_registry(make_finder):
    finder = make_finder([])

    monitor.search(
        cond="cll",
        sponsor_types=("INDUSTRY",),
        statuses=("RECRUITING",),
        started_from="2024-01-01",
        started_to="2024-12-31",
        find=finder,
    )

    asked = finder.calls[0]
    assert asked["sponsor_types"] == ("INDUSTRY",)
    assert asked["statuses"] == ("RECRUITING",)
    assert asked["started_from"] == "2024-01-01"
    assert asked["started_to"] == "2024-12-31"


def test_a_search_naming_only_the_narrowing_axes_is_refused(make_finder):
    """Industry, recruiting and a date window do not name a programme.

    Refused in the same words as an empty search, because the fix is the same:
    say what kind of study you are looking for.
    """
    finder = make_finder([])

    with pytest.raises(monitor.MonitorError, match="at least one"):
        monitor.search(
            sponsor_types=("INDUSTRY",),
            statuses=("RECRUITING",),
            started_from="2024-01-01",
            find=finder,
        )

    assert finder.calls == []


def test_a_query_keeps_the_narrowing_axes_it_was_given():
    query = monitor.as_query(
        cond="cll",
        sponsor_types=["INDUSTRY"],
        statuses=["RECRUITING"],
        started_from="2024-01-01",
        started_to="",
    )

    assert query["sponsor_types"] == ["INDUSTRY"]
    assert query["statuses"] == ["RECRUITING"]
    assert query["started_from"] == "2024-01-01"
    assert query["started_to"] == ""


def test_an_axis_nobody_set_is_an_axis_that_does_not_narrow(make_finder):
    """A query missing a key entirely, which is the shape ticket 13 stored.

    Asserted against a dict built by hand rather than by `as_query`, because
    `as_query` fills every key: routed through it, the missing-key path this is
    about is never reached. The stored-and-re-run route is covered in
    test_found_trials.py, which is where a query is read back off a list.
    """
    finder = make_finder([])
    stored = {"cond": "cll", "intr": "", "spons": "", "phases": ["PHASE3"]}

    monitor._matches(stored, 40, finder)

    asked = finder.calls[0]
    assert asked["cond"] == "cll"
    # A blank text axis reaches the client as text, not as an empty tuple.
    assert asked["intr"] == ""
    assert asked["spons"] == ""
    assert asked["sponsor_types"] == ()
    assert asked["statuses"] == ()
    assert asked["started_from"] == ""
    assert asked["started_to"] == ""


def test_a_window_that_ends_before_it_starts_is_refused(make_finder):
    """Otherwise it returns nothing, and nothing is what a real miss looks like.

    The registry accepts an inverted range and answers it with zero studies, so
    the analyst is told "nothing found" about a query that could never have
    found anything. Refused up front instead, naming the two dates, because the
    fix is to swap them and only the reader can say which way round.
    """
    finder = make_finder([])

    with pytest.raises(monitor.MonitorError, match="ends before"):
        monitor.search(
            cond="cll", started_from="2025-01-01", started_to="2024-01-01", find=finder
        )

    assert finder.calls == []


def test_a_window_ending_on_the_day_it_starts_is_allowed(make_finder):
    """Both ends are inclusive, so a single-day window is a day, not an error."""
    finder = make_finder([])

    monitor.search(cond="cll", started_from="2024-01-01", started_to="2024-01-01", find=finder)

    assert finder.calls
