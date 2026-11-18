"""walker-trial-page-recheck-01: after Remove from this list and a switch to another of the trial's
tabs, Next trial restarts the watchlist's Needs review queue from its top instead of going on to
the trial after this one (spec: user stories 16, 17 and 22).

Red now: in Myeloma's queue the third trial is opened, removed from Myeloma, History then Changes
are opened, and Next trial goes to the queue's first trial. Without the tab switch it goes to the
fourth (the control below is green now). Green once both go to the fourth.
"""

from __future__ import annotations

import re

import pytest

from walks.test_trial_address_walk import MYELOMA, seed_two_queues


@pytest.mark.parametrize("switch_tabs", [False, True], ids=["no-switch", "after-tab-switch"])
def test_next_trial_after_removal_goes_on_to_the_following_trial(make_app, make_walk, switch_tabs):
    app = make_app(seed=seed_two_queues)
    walk = make_walk(app)
    page = walk.page
    page.goto(f"{app.url}#/watchlists/{MYELOMA}/needs-review")
    page.locator("li.card h3 a").nth(4).wait_for()
    queue = page.locator("li.card").evaluate_all("cs => cs.map(c => c.dataset.nct)")
    page.locator("li.card h3 a").nth(2).click()
    page.get_by_role("button", name="Mark reviewed").wait_for()
    page.get_by_role("button", name="More actions").click()
    page.get_by_role("menuitem", name="Remove from this list").click()
    page.locator(".banner", has_text="Removed from Myeloma").wait_for()
    if switch_tabs:
        page.get_by_role("tab", name="History").click()
        page.get_by_role("heading", name="Trial history").wait_for()
        page.get_by_role("tab", name=re.compile("^Changes")).click()
        page.get_by_role("button", name="Mark reviewed").wait_for()
        page.wait_for_timeout(300)  # Next trial is wired once the queue's answer is in
    page.get_by_role("button", name="Next trial").click()
    page.wait_for_function(f"!location.hash.includes('{queue[2]}')")
    walk.shot("next-trial")
    assert page.evaluate("location.hash") == f"#/trials/{queue[3]}?list={MYELOMA}"
