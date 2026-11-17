"""walker-trial-page-01: "Back to" from a trial opened on Summary forgets the period the analyst chose.

Red now: the Summary period is set to "This month", a trial heading is opened, and "‹ Back to Myeloma"
lands on Summary with "This week" pressed and an address with no period. Before this build the
in-page memory kept the period (the old origin tab was "summary?period=month").
Green once "Back to" returns to the Summary period the trial was opened from, within the same page load.
"""

from __future__ import annotations

from walks import test_summary_walk as summary_seed


def test_back_to_summary_keeps_the_period_chosen(make_app, make_walk):
    _, walk = summary_seed.open_summary(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="This month").click()
    page.wait_for_url("**/summary?period=month")
    page.locator("li.card.trial h3 a").first.click()
    page.locator("a.back").wait_for()
    page.locator("a.back").click()
    page.locator("#summary-heading").wait_for()
    walk.shot("back-on-summary")
    assert page.evaluate("location.hash") == "#/watchlists/1/summary?period=month"
    assert page.locator('[aria-label="Period"] [aria-pressed="true"]').inner_text() == "This month"
