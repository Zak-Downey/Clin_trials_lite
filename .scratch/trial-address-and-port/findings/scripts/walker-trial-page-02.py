"""walker-trial-page-02: an address whose list is not a watchlist number (list=abc, list=0, list=) is left as typed.

Red now: #/trials/NCT03412565?list=abc opens with "Back to Myeloma" (the trial's first watchlist), but
the address still reads list=abc, so it names a watchlist the page is not using. An address naming a
watchlist number that does not hold the trial (list=99) is rewritten to list=1 in place.
Green once such an address is rewritten in place like list=99 is (to name the watchlist shown, or to
name none).
"""

from __future__ import annotations

import pytest

from walks.test_trial_address_walk import seed_two_queues


@pytest.mark.parametrize("bad", ["abc", "0", ""])
def test_a_list_that_is_not_a_watchlist_number_is_not_left_in_the_address(make_app, make_walk, bad):
    app = make_app(seed=seed_two_queues)
    walk = make_walk(app)
    page = walk.page
    page.goto(f"{app.url}#/trials/NCT03412565?list={bad}")
    page.get_by_role("button", name="Mark reviewed").wait_for()
    assert page.locator("a.back").inner_text() == "‹ Back to Myeloma"
    walk.shot("bad-list")
    assert page.evaluate("location.hash") in ("#/trials/NCT03412565?list=1", "#/trials/NCT03412565")
