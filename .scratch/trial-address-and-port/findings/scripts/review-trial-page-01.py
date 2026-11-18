"""review-trial-page-01: after Remove from this list on the trial page, switching to the trial's
own Trial details or History tab forgets the watchlist the analyst came from (spec: user stories 15
and 22, "Only a later reload falls back")."""

from __future__ import annotations

import re

from walks.test_trial_address_walk import ELSEWHERE, open_from_elsewhere


def test_switching_the_trial_tab_after_removing_it_from_the_list_keeps_that_list(make_app, make_walk):
    _, walk = open_from_elsewhere(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="More actions").click()
    page.get_by_role("menuitem", name="Remove from this list").click()
    page.get_by_text("Removed from Elsewhere.").wait_for()
    assert page.locator("a.back").inner_text() == "‹ Back to Elsewhere"
    page.get_by_role("tab", name="History").click()
    page.get_by_role("heading", name="Trial history").wait_for()
    assert page.locator("a.back").inner_text() == "‹ Back to Elsewhere"
    assert re.search(rf"\?list={ELSEWHERE}", page.evaluate("location.hash"))
