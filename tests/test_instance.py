"""The one-server-per-database claim: a second start waits for the first's address.

Lacks: a crash of the holder (the operating system drops the lock; not forced here).
"""

import threading
import time

from webapp import instance


def test_a_second_start_waits_for_the_address_the_first_is_about_to_publish(tmp_path):
    """test_a_second_start_waits_for_the_address_the_first_is_about_to_publish"""
    db = str(tmp_path / "m.db")
    first = instance.claim(db)
    assert isinstance(first, instance.Claim)
    threading.Timer(0.3, first.publish, args=("http://127.0.0.1:5555/",)).start()
    started = time.monotonic()
    assert instance.claim(db, wait=5) == "http://127.0.0.1:5555/"
    assert time.monotonic() - started >= 0.25


def test_a_second_start_gives_up_with_none_when_no_address_ever_arrives(tmp_path):
    """test_a_second_start_gives_up_with_none_when_no_address_ever_arrives"""
    db = str(tmp_path / "m.db")
    first = instance.claim(db)
    assert isinstance(first, instance.Claim)
    started = time.monotonic()
    assert instance.claim(db, wait=0.3) is None
    assert 0.25 <= time.monotonic() - started < 3


def test_a_dead_runs_address_is_not_offered_by_a_new_holder_that_has_not_published(tmp_path):
    """test_a_dead_runs_address_is_not_offered_by_a_new_holder_that_has_not_published"""
    db = str(tmp_path / "m.db")
    (tmp_path / "m.db.lock").write_text("http://127.0.0.1:1/")
    first = instance.claim(db)
    assert isinstance(first, instance.Claim)
    assert instance.claim(db, wait=0.2) is None
