"""Trials that appear, not just trials that move.

A watchlist that only re-reads records it already holds is blind to the thing a
medical affairs team most wants to hear: a competitor registering something
new. So a list can remember the search that filled it, and a check re-runs that
search and offers back anything matching it the list does not already hold.

A found trial *waits*. It joins the list when the analyst adopts it, and is
never offered again once dismissed -- the judgement about what belongs in a
curated list is the whole value of curating one, and a loose query must not
quietly make it for them.

All of it is tested through the registry seam, so nothing here touches the
network.
"""

from __future__ import annotations

import urllib.error

import pytest

import display
import monitor
import storage


@pytest.fixture
def myeloma(conn) -> int:
    return monitor.create_list(conn, "Myeloma")


@pytest.fixture
def watching(conn, myeloma) -> int:
    """A list already remembering the search that filled it."""
    monitor.remember_search(
        conn, myeloma, monitor.as_query(cond="multiple myeloma", spons="Janssen")
    )
    return myeloma


def run(conn, list_id, **kwargs) -> list[dict]:
    """A whole check run, as the list of results the page collects."""
    return list(monitor.check_all(conn, list_id, pause=0, **kwargs))


def searches(results: list[dict]) -> list[dict]:
    return [r for r in results if r["kind"] == "search"]


# --- a list remembering a search


def test_a_search_can_be_remembered_against_a_list(conn, myeloma):
    monitor.remember_search(
        conn,
        myeloma,
        monitor.as_query(cond="multiple myeloma", spons="Janssen", phases=("PHASE3",)),
    )

    assert monitor.remembered_search(conn, myeloma) == {
        "cond": "multiple myeloma",
        "intr": "",
        "spons": "Janssen",
        "phases": ["PHASE3"],
    }


def test_a_list_remembers_nothing_until_it_is_told_to(conn, myeloma):
    assert monitor.remembered_search(conn, myeloma) is None


def test_a_remembered_search_needs_at_least_one_axis(conn, myeloma):
    with pytest.raises(monitor.MonitorError, match="at least one"):
        monitor.remember_search(conn, myeloma, monitor.as_query(cond="   "))


def test_a_remembered_search_can_be_changed(conn, watching):
    monitor.remember_search(conn, watching, monitor.as_query(intr="daratumumab"))

    assert monitor.remembered_search(conn, watching)["intr"] == "daratumumab"
    assert monitor.remembered_search(conn, watching)["cond"] == ""


def test_a_remembered_search_can_be_cleared(conn, watching):
    monitor.forget_search(conn, watching)

    assert monitor.remembered_search(conn, watching) is None


def test_a_list_says_what_it_is_watching_for(conn, watching):
    line = display.search_line(monitor.remembered_search(conn, watching))

    assert "multiple myeloma" in line
    assert "Janssen" in line


def test_the_phases_a_search_names_are_read_as_phases(conn, myeloma):
    monitor.remember_search(conn, myeloma, monitor.as_query(phases=("PHASE3",)))

    assert "Phase 3" in display.search_line(monitor.remembered_search(conn, myeloma))


def test_a_remembered_search_survives_the_list_being_renamed(conn, watching):
    monitor.rename_list(conn, watching, "Myeloma — Janssen")

    assert monitor.remembered_search(conn, watching)["cond"] == "multiple myeloma"


# --- the search running as part of a check


def test_a_list_with_no_remembered_search_is_not_searched(conn, myeloma, make_finder):
    finder = make_finder()

    results = run(conn, myeloma, find=finder)

    assert finder.calls == []
    assert searches(results) == []


def test_a_list_without_a_remembered_search_checks_as_it_did_before(
    conn, myeloma, fetcher, make_finder
):
    monitor.add(conn, "NCT03412565", myeloma, fetch=fetcher)

    results = run(conn, myeloma, fetch=fetcher, find=make_finder())

    assert [r["kind"] for r in results] == ["trial"]
    assert results[0]["outcome"] == "unchanged"


def test_checking_a_list_re_runs_its_remembered_search(conn, watching, make_finder):
    finder = make_finder()

    run(conn, watching, find=finder)

    assert len(finder.calls) == 1
    assert finder.calls[0]["cond"] == "multiple myeloma"
    assert finder.calls[0]["spons"] == "Janssen"


def test_a_match_the_list_does_not_hold_is_reported_as_found(
    conn, watching, record, make_finder, restyled
):
    finder = make_finder([restyled(record, "NCT99999999")])

    results = run(conn, watching, find=finder)

    assert [r["outcome"] for r in searches(results)] == ["found"]
    assert searches(results)[0]["found"] == ["NCT99999999"]


def test_a_found_trial_is_reported_apart_from_a_changed_field(
    conn, watching, record, fetcher, make_finder, restyled
):
    """Two kinds of news: a competitor started something, or revised something."""
    monitor.add(conn, "NCT03412565", watching, fetch=fetcher)
    finder = make_finder([restyled(record, "NCT99999999")])

    results = run(conn, watching, fetch=fetcher, find=finder)

    assert [r["kind"] for r in results] == ["search", "trial"]


def test_a_found_trial_is_not_added_to_the_list(
    conn, watching, record, make_finder, restyled
):
    run(conn, watching, find=make_finder([restyled(record, "NCT99999999")]))

    assert storage.list_trials(conn, watching) == []
    assert not storage.is_member(conn, watching, "NCT99999999")


def test_a_found_trial_carries_what_identifies_the_study(
    conn, watching, record, make_finder, restyled
):
    """Offered on the same facts a watched trial is listed by, or the analyst
    is being asked to judge an NCT number."""
    run(conn, watching, find=make_finder([restyled(record, "NCT99999999")]))

    offered = monitor.found_trials(conn, watching)

    assert len(offered) == 1
    assert offered[0]["nct_id"] == "NCT99999999"
    assert offered[0]["sponsor"] == "Janssen Research & Development, LLC"
    assert offered[0]["title"]
    assert offered[0]["phases"]


def test_a_trial_already_in_the_list_is_not_reported_as_found(
    conn, watching, record, fetcher, make_finder
):
    monitor.add(conn, "NCT03412565", watching, fetch=fetcher)
    finder = make_finder([record])

    results = run(conn, watching, fetch=fetcher, find=finder)

    assert searches(results)[0]["outcome"] == "nothing_found"
    assert monitor.found_trials(conn, watching) == []


def test_a_trial_already_offered_is_not_offered_twice(
    conn, watching, record, make_finder, restyled
):
    finder = make_finder([restyled(record, "NCT99999999")])

    run(conn, watching, find=finder)
    second = run(conn, watching, find=finder)

    assert searches(second)[0]["outcome"] == "nothing_found"
    assert len(monitor.found_trials(conn, watching)) == 1


def test_a_trial_watched_under_another_list_is_still_offered_here(
    conn, watching, record, fetcher, make_finder
):
    """The judgement is per list: myeloma holding it says nothing about lung."""
    lung = monitor.create_list(conn, "Lung")
    monitor.add(conn, "NCT03412565", lung, fetch=fetcher)

    run(conn, watching, find=make_finder([record]))

    assert [r["nct_id"] for r in monitor.found_trials(conn, watching)] == ["NCT03412565"]


# --- the feed


def test_a_found_trial_appears_in_the_feed_unreviewed(
    conn, watching, record, make_finder, restyled
):
    run(conn, watching, find=make_finder([restyled(record, "NCT99999999")]))

    events = [e for e in monitor.feed(conn, watching) if e["nct_id"] == "NCT99999999"]

    assert len(events) == 1
    assert "new trial" in events[0]["kind"]
    assert events[0]["reviewed"] is False


def test_a_dismissed_trial_stops_being_unreviewed_in_the_feed(
    conn, watching, record, make_finder, restyled
):
    run(conn, watching, find=make_finder([restyled(record, "NCT99999999")]))

    monitor.dismiss(conn, watching, "NCT99999999")

    events = [e for e in monitor.feed(conn, watching) if e["nct_id"] == "NCT99999999"]
    assert events[0]["reviewed"] is True


# --- adopting and dismissing


def test_adopting_a_found_trial_records_its_baseline_and_adds_it(
    conn, watching, record, fetcher, make_finder, restyled
):
    run(conn, watching, find=make_finder([restyled(record, "NCT99999999")]))

    monitor.adopt(conn, watching, "NCT99999999", fetch=fetcher)

    assert storage.is_member(conn, watching, "NCT99999999")
    assert storage.count_snapshots(conn, "NCT99999999") == 1
    # A baseline, not 41 changes: adding a trial never reports its own fields
    # as having moved.
    assert storage.list_changes(conn, "NCT99999999") == []


def test_an_adopted_trial_is_no_longer_offered(
    conn, watching, record, fetcher, make_finder, restyled
):
    finder = make_finder([restyled(record, "NCT99999999")])
    run(conn, watching, find=finder)

    monitor.adopt(conn, watching, "NCT99999999", fetch=fetcher)

    assert monitor.found_trials(conn, watching) == []
    assert searches(run(conn, watching, fetch=fetcher, find=finder))[0][
        "outcome"
    ] == "nothing_found"


def test_a_trial_that_could_not_be_fetched_stays_on_offer(
    conn, watching, record, make_finder, make_fetcher, restyled
):
    run(conn, watching, find=make_finder([restyled(record, "NCT99999999")]))
    broken = make_fetcher(failures={"NCT99999999": urllib.error.URLError("down")})

    with pytest.raises(monitor.MonitorError):
        monitor.adopt(conn, watching, "NCT99999999", fetch=broken)

    assert [r["nct_id"] for r in monitor.found_trials(conn, watching)] == ["NCT99999999"]


def test_a_dismissed_trial_is_not_offered_again(
    conn, watching, record, make_finder, restyled
):
    finder = make_finder([restyled(record, "NCT99999999")])
    run(conn, watching, find=finder)

    monitor.dismiss(conn, watching, "NCT99999999")

    assert monitor.found_trials(conn, watching) == []
    assert searches(run(conn, watching, find=finder))[0]["outcome"] == "nothing_found"


def test_several_found_trials_are_adopted_in_one_go(
    conn, watching, record, fetcher, make_finder, restyled
):
    finder = make_finder(
        [restyled(record, "NCT99999999"), restyled(record, "NCT88888888")]
    )
    run(conn, watching, find=finder)

    outcome = monitor.adopt_many(
        conn, watching, ["NCT99999999", "NCT88888888"], fetch=fetcher
    )

    assert sorted(outcome["added"]) == ["NCT88888888", "NCT99999999"]
    assert monitor.found_trials(conn, watching) == []


# --- a search that fails


def test_a_failing_search_does_not_stop_the_trials_being_checked(
    conn, watching, fetcher, make_finder
):
    monitor.add(conn, "NCT03412565", watching, fetch=fetcher)
    finder = make_finder(failure=urllib.error.URLError("registry down"))

    results = run(conn, watching, fetch=fetcher, find=finder)

    assert searches(results)[0]["outcome"] == "error"
    assert [r["nct_id"] for r in results if r["kind"] == "trial"] == ["NCT03412565"]


def test_a_failing_search_is_reported_rather_than_read_as_nothing_new(
    conn, watching, fetcher, make_finder
):
    """An outage must not pass as "no competitor started anything"."""
    monitor.add(conn, "NCT03412565", watching, fetch=fetcher)
    finder = make_finder(failure=urllib.error.URLError("registry down"))

    summary = monitor.summarise(run(conn, watching, fetch=fetcher, find=finder))

    assert summary["level"] == "warning"
    assert "no changes" not in summary["message"]
    assert summary["search_failed"]


def test_a_failing_search_writes_nothing(conn, watching, make_finder):
    run(conn, watching, find=make_finder(failure=urllib.error.URLError("down")))

    assert monitor.found_trials(conn, watching) == []


def test_a_capped_search_says_so_rather_than_claiming_it_saw_everything(
    conn, watching, record, make_finder, restyled
):
    """A query matching thousands has not checked thousands, and "nothing new"
    would be a claim about studies the run never looked at."""
    studies = [restyled(record, f"NCT9999{i:04d}") for i in range(monitor.RESULT_CAP + 1)]

    results = run(conn, watching, find=make_finder(studies))

    assert "narrow it" in searches(results)[0]["detail"].lower()
    assert len(monitor.found_trials(conn, watching)) == monitor.RESULT_CAP


def test_an_uncapped_search_does_not_nag_about_narrowing(
    conn, watching, record, make_finder, restyled
):
    results = run(conn, watching, find=make_finder([restyled(record, "NCT99999999")]))

    assert "narrow" not in searches(results)[0]["detail"].lower()


# --- how the run reads


def test_a_run_that_found_a_trial_is_not_summarised_as_no_changes(
    conn, watching, record, fetcher, make_finder, restyled
):
    monitor.add(conn, "NCT03412565", watching, fetch=fetcher)
    finder = make_finder([record, restyled(record, "NCT99999999")])

    summary = monitor.summarise(run(conn, watching, fetch=fetcher, find=finder))

    assert summary["level"] == "warning"
    assert "no changes" not in summary["message"]
    assert "1 new trial found" in summary["message"]
    assert [r["found"] for r in summary["found"]] == [["NCT99999999"]]


def test_a_quiet_run_still_reads_as_nothing_happened(
    conn, watching, record, fetcher, make_finder
):
    monitor.add(conn, "NCT03412565", watching, fetch=fetcher)

    finder = make_finder([record])

    summary = monitor.summarise(run(conn, watching, fetch=fetcher, find=finder))

    assert summary["level"] == "success"
    assert "no changes" in summary["message"]
