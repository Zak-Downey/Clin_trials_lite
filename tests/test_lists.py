"""Named watchlists, and which trials belong to them.

Somebody covering two therapy areas keeps myeloma apart from lung, so a trial
belongs to a *list* rather than to one undifferentiated watchlist -- and to more
than one at a time, since indications overlap. All of it is tested here without
running Streamlit: the page only chooses which list to show.
"""

from __future__ import annotations

import copy
import sqlite3

import pytest

import monitor
import storage


@pytest.fixture
def myeloma(conn) -> int:
    return monitor.create_list(conn, "Myeloma")


def other_record(record: dict, nct_id: str) -> dict:
    """The captured record, standing in for a second study."""
    copied = copy.deepcopy(record)
    copied["protocolSection"]["identificationModule"]["nctId"] = nct_id
    return copied


# --- creating, renaming, deleting


def test_a_new_database_opens_with_one_list_to_stand_in(conn):
    """The page always has a list to show, even before anybody names one."""
    names = [row["name"] for row in storage.list_lists(conn)]

    assert names == [storage.DEFAULT_LIST]


def test_a_list_can_be_created_and_is_found_by_name(conn):
    monitor.create_list(conn, "Myeloma")

    assert storage.find_list(conn, "Myeloma") is not None


def test_two_lists_cannot_share_a_name(conn, myeloma):
    with pytest.raises(monitor.MonitorError, match="already"):
        monitor.create_list(conn, "Myeloma")


def test_a_list_name_that_only_differs_by_surrounding_space_is_the_same_name(conn, myeloma):
    with pytest.raises(monitor.MonitorError, match="already"):
        monitor.create_list(conn, "  Myeloma  ")


def test_a_list_needs_a_name(conn):
    with pytest.raises(monitor.MonitorError, match="name"):
        monitor.create_list(conn, "   ")


def test_renaming_a_list_keeps_what_is_in_it(conn, myeloma, fetcher):
    monitor.add(conn, "NCT03412565", myeloma, fetch=fetcher)

    monitor.rename_list(conn, myeloma, "Myeloma — Janssen")

    assert storage.get_list(conn, myeloma)["name"] == "Myeloma — Janssen"
    assert [r["nct_id"] for r in storage.list_trials(conn, myeloma)] == ["NCT03412565"]


def test_a_list_cannot_be_renamed_onto_another_lists_name(conn, myeloma):
    lung = monitor.create_list(conn, "Lung")

    with pytest.raises(monitor.MonitorError, match="already"):
        monitor.rename_list(conn, lung, "Myeloma")


def test_a_list_can_be_renamed_to_the_name_it_already_has(conn, myeloma):
    monitor.rename_list(conn, myeloma, "Myeloma")

    assert storage.get_list(conn, myeloma)["name"] == "Myeloma"


def test_deleting_a_list_removes_it(conn, myeloma):
    monitor.delete_list(conn, myeloma)

    assert storage.find_list(conn, "Myeloma") is None


# --- a trial in more than one list


def test_a_trial_can_belong_to_two_lists_at_once(conn, myeloma, fetcher):
    lung = monitor.create_list(conn, "Lung")
    monitor.add(conn, "NCT03412565", myeloma, fetch=fetcher)
    monitor.add(conn, "NCT03412565", lung, fetch=fetcher)

    assert [r["nct_id"] for r in storage.list_trials(conn, myeloma)] == ["NCT03412565"]
    assert [r["nct_id"] for r in storage.list_trials(conn, lung)] == ["NCT03412565"]


def test_a_trial_already_monitored_joins_the_second_list_without_being_refetched(
    conn, myeloma, fetcher
):
    """Its history is the point of monitoring it; joining a list must not restart it."""
    lung = monitor.create_list(conn, "Lung")
    monitor.add(conn, "NCT03412565", myeloma, fetch=fetcher)
    began = storage.get_trial(conn, "NCT03412565")["monitoring_began"]

    monitor.add(conn, "NCT03412565", lung, fetch=fetcher)

    assert fetcher.calls == ["NCT03412565"]
    assert storage.count_snapshots(conn, "NCT03412565") == 1
    assert storage.get_trial(conn, "NCT03412565")["monitoring_began"] == began


def test_adding_a_trial_to_a_list_it_is_already_in_is_refused(conn, myeloma, fetcher):
    monitor.add(conn, "NCT03412565", myeloma, fetch=fetcher)

    with pytest.raises(monitor.MonitorError, match="already"):
        monitor.add(conn, "NCT03412565", myeloma, fetch=fetcher)


def test_removing_a_trial_from_one_list_leaves_it_in_the_other(conn, myeloma, fetcher):
    lung = monitor.create_list(conn, "Lung")
    monitor.add(conn, "NCT03412565", myeloma, fetch=fetcher)
    monitor.add(conn, "NCT03412565", lung, fetch=fetcher)

    monitor.remove(conn, "NCT03412565", myeloma)

    assert storage.list_trials(conn, myeloma) == []
    assert [r["nct_id"] for r in storage.list_trials(conn, lung)] == ["NCT03412565"]
    assert storage.get_trial(conn, "NCT03412565") is not None


def test_a_trial_left_in_no_list_at_all_stops_being_monitored(conn, myeloma, fetcher):
    monitor.add(conn, "NCT03412565", myeloma, fetch=fetcher)

    monitor.remove(conn, "NCT03412565", myeloma)

    assert storage.get_trial(conn, "NCT03412565") is None
    assert storage.count_snapshots(conn, "NCT03412565") == 0


def test_deleting_a_list_stops_monitoring_only_what_no_other_list_holds(
    conn, myeloma, record, make_fetcher
):
    lung = monitor.create_list(conn, "Lung")
    monitor.add(conn, "NCT03412565", myeloma, fetch=make_fetcher(default=record))
    monitor.add(conn, "NCT03412565", lung, fetch=make_fetcher(default=record))
    monitor.add(
        conn, "NCT00000001", myeloma, fetch=make_fetcher(default=other_record(record, "NCT00000001"))
    )

    monitor.delete_list(conn, myeloma)

    assert storage.get_trial(conn, "NCT03412565") is not None
    assert storage.get_trial(conn, "NCT00000001") is None


# --- reading one list at a time


def test_the_watchlist_narrows_to_the_list_it_is_asked_for(conn, myeloma, record, make_fetcher):
    lung = monitor.create_list(conn, "Lung")
    monitor.add(conn, "NCT03412565", myeloma, fetch=make_fetcher(default=record))
    monitor.add(
        conn, "NCT00000001", lung, fetch=make_fetcher(default=other_record(record, "NCT00000001"))
    )

    assert [r["nct_id"] for r in monitor.watchlist(conn, myeloma)] == ["NCT03412565"]
    assert [r["nct_id"] for r in monitor.watchlist(conn, lung)] == ["NCT00000001"]


def test_the_feed_narrows_to_the_list_it_is_asked_for(conn, myeloma, record, make_fetcher):
    lung = monitor.create_list(conn, "Lung")
    monitor.add(conn, "NCT03412565", myeloma, fetch=make_fetcher(default=record))
    monitor.add(
        conn, "NCT00000001", lung, fetch=make_fetcher(default=other_record(record, "NCT00000001"))
    )

    assert {e["nct_id"] for e in monitor.feed(conn, myeloma)} == {"NCT03412565"}


def test_a_change_on_a_trial_in_two_lists_is_visible_from_both(conn, myeloma, fetcher):
    lung = monitor.create_list(conn, "Lung")
    monitor.add(conn, "NCT03412565", myeloma, fetch=fetcher)
    monitor.add(conn, "NCT03412565", lung, fetch=fetcher)
    storage.add_change(
        conn,
        "NCT03412565",
        {"field": "enrollment", "previous": 1, "current": 2},
        "2026-09-05T10:00:00+00:00",
    )

    for chosen in (myeloma, lung):
        row = monitor.watchlist(conn, chosen)[0]
        assert row["change"]["fields"] == ["enrollment"]
        assert row["unreviewed"] == 1


def test_asking_for_no_list_in_particular_reads_everything_monitored(
    conn, myeloma, record, make_fetcher
):
    lung = monitor.create_list(conn, "Lung")
    monitor.add(conn, "NCT03412565", myeloma, fetch=make_fetcher(default=record))
    monitor.add(
        conn, "NCT00000001", lung, fetch=make_fetcher(default=other_record(record, "NCT00000001"))
    )

    assert len(monitor.watchlist(conn)) == 2


# --- a database that predates lists


def pre_lists_database(path) -> str:
    """A database written before lists existed: trials, no lists table."""
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE trials (
            nct_id TEXT PRIMARY KEY,
            monitoring_began TEXT NOT NULL,
            last_checked TEXT,
            last_reviewed TEXT
        );
        INSERT INTO trials (nct_id, monitoring_began) VALUES ('NCT03412565', '2026-01-01');
        INSERT INTO trials (nct_id, monitoring_began) VALUES ('NCT00000001', '2026-01-02');
        """
    )
    conn.commit()
    conn.close()
    return str(path)


def test_a_database_predating_lists_opens_with_everything_in_one_list(tmp_path):
    path = pre_lists_database(tmp_path / "old.db")

    conn = storage.connect(path)

    lists = storage.list_lists(conn)
    assert len(lists) == 1
    held = [r["nct_id"] for r in storage.list_trials(conn, lists[0]["id"])]
    assert held == ["NCT03412565", "NCT00000001"]


def test_opening_a_migrated_database_again_does_not_make_a_second_list(tmp_path):
    path = pre_lists_database(tmp_path / "old.db")
    storage.connect(path).close()

    conn = storage.connect(path)

    assert len(storage.list_lists(conn)) == 1


def test_reopening_a_database_does_not_re_home_a_trial_that_lost_its_last_list(
    tmp_path, record, make_fetcher
):
    """Dropping a trial is deliberate; a reconnect must not quietly undo it."""
    path = str(tmp_path / "live.db")
    conn = storage.connect(path)
    only = storage.list_lists(conn)[0]["id"]
    monitor.add(conn, "NCT03412565", only, fetch=make_fetcher(default=record))
    # The trial outliving its membership is the state a reconnect must not
    # rescue, so it is made directly rather than through monitor.remove.
    storage.remove_member(conn, only, "NCT03412565")
    conn.close()

    conn = storage.connect(path)

    assert storage.list_trials(conn, only) == []


def test_adding_without_naming_a_list_says_so_when_there_are_none(conn, fetcher):
    storage.delete_list(conn, storage.list_lists(conn)[0]["id"])

    with pytest.raises(monitor.MonitorError, match="no lists"):
        monitor.add(conn, "NCT03412565", fetch=fetcher)
