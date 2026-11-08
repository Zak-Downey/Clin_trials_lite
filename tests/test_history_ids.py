"""A trial's history carries each move's change ID and its check.

Lacks: moves folded from a qualifier alone, and trials with several checks.
"""

import monitor
import storage


def test_history_moves_carry_the_change_id_and_the_check(conn, record):
    monitor.add(conn, "NCT03412565", fetch=lambda _n: record, when="2026-11-01T08:00:00+00:00")
    storage.add_change(conn, "NCT03412565", {"field": "enrollment", "previous": 1, "current": 2}, "2026-11-08T16:45:00+00:00")
    (move,) = monitor.history(conn, "NCT03412565")
    assert move["id"] == storage.list_changes(conn, "NCT03412565")[0]["id"]
    assert move["check"] == "2026-11-08T16:45:00+00:00"
