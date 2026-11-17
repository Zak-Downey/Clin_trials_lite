"""walker-trial-page-recheck-02: "Back to" Summary returns to a period the analyst has since changed.

Red now: Summary is set to This month, a trial is opened, the browser's Back returns to Summary,
This week is chosen, the browser's Forward returns to the trial, and "‹ Back to Myeloma" lands on
This month. The browser's Back from the same trial lands on This week. Green once "Back to" lands
on This week, the period the analyst last chose on that Summary.
"""

from __future__ import annotations

from walks import test_summary_walk as summary_seed


def test_back_to_summary_after_changing_the_period_lands_on_the_new_period(make_app, make_walk):
    _, walk = summary_seed.open_summary(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="This month").click()
    page.wait_for_url("**/summary?period=month")
    page.locator('li.card.trial[data-nct="NCT03412565"] h3 a').click()
    page.get_by_role("tab", name="History").wait_for()
    page.go_back()
    page.locator("#summary-heading").wait_for()
    page.get_by_role("button", name="This week").click()
    page.wait_for_url("**/summary?period=week")
    page.go_forward()
    page.locator("a.back").wait_for()
    page.locator("a.back").click()
    page.locator("#summary-heading").wait_for()
    walk.shot("back-to-summary")
    assert page.evaluate("location.hash") == "#/watchlists/1/summary?period=week"
    assert page.locator('[aria-label="Period"] [aria-pressed="true"]').inner_text() == "This week"
