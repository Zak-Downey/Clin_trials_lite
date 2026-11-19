"""The browser tests' stand-in registry, as the walk helper starts and stops it."""

from __future__ import annotations

import time

from walks import helper


def test_a_stand_in_registry_started_and_stopped_by_the_helper_is_done_in_under_a_fifth_of_a_second():
    started = time.monotonic()
    registry = helper.Registry()
    registry.close()
    assert time.monotonic() - started < 0.2
