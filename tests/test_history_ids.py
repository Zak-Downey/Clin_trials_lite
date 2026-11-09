"""A trial's history carries each move's change ID and its check.

Lacks: moves folded from a qualifier alone, and trials with several checks.
"""

import monitor
import storage


def test_history_moves_carry_the_change_id_and_the_check(conn, record):
    """test_history_moves_carry_the_change_id_and_the_check"""
    monitor.add(conn, "NCT03412565", fetch=lambda _n: record, when="2026-11-01T08:00:00+00:00")
    storage.add_change(conn, "NCT03412565", {"field": "enrollment", "previous": 1, "current": 2}, "2026-11-08T16:45:00+00:00")
    (move,) = monitor.history(conn, "NCT03412565")
    assert move["ids"] == [storage.list_changes(conn, "NCT03412565")[0]["id"]]
    assert move["check"] == "2026-11-08T16:45:00+00:00"


def test_a_folded_move_carries_every_id_it_folds_and_is_reviewed_only_if_all_are(conn, record):
    """test_a_folded_move_carries_every_id_it_folds_and_is_reviewed_only_if_all_are"""
    monitor.add(conn, "NCT03412565", fetch=lambda _n: record, when="2026-11-01T08:00:00+00:00")
    when = "2026-11-08T16:45:00+00:00"
    storage.add_change(conn, "NCT03412565", {"field": "primaryCompletionDate", "previous": "2026-01", "current": "2026-06"}, when)
    storage.add_change(conn, "NCT03412565", {"field": "primaryCompletionDateType", "previous": "ESTIMATED", "current": "ACTUAL"}, when)
    (move,) = monitor.history(conn, "NCT03412565")
    assert sorted(move["ids"]) == sorted(c["id"] for c in storage.list_changes(conn, "NCT03412565"))
    assert len(move["ids"]) == 2 and move["reviewed"] is False
    conn.execute("UPDATE changes SET reviewed = 1 WHERE field = 'primaryCompletionDate'")
    conn.commit()
    (move,) = monitor.history(conn, "NCT03412565")
    assert move["reviewed"] is False
