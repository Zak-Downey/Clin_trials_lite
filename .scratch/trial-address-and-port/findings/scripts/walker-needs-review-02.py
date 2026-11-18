"""walker-needs-review-02: after Remove from this list on the trial page, switching the trial's tab forgets the watchlist.

Data: walks/test_trial_address_walk.py's seed (NCT03412565 in "Myeloma" id 1 and "Elsewhere" id 2).
Spec story 22 and "Remove from this list. Unchanged": "Back to" keeps naming the watchlist the
analyst came from until a later reload. Switching to History re-reads the address, falls back to
the first watchlist and rewrites the address to list=1.
"""
from walks.test_trial_address_walk import seed_two_queues, ELSEWHERE


def test_switching_tab_after_remove_keeps_back_to_the_watchlist_came_from(make_app, make_walk):
    app = make_app(seed=seed_two_queues)
    walk = make_walk(app)
    page = walk.page
    page.goto(f"{app.url}#/watchlists/{ELSEWHERE}/all-trials")
    page.locator('tr[data-nct="NCT03412565"] a').click()
    page.get_by_role("link", name="‹ Back to Elsewhere").wait_for()
    page.get_by_role("button", name="More actions").click()
    page.get_by_role("menuitem", name="Remove from this list").click()
    page.get_by_text("Removed from Elsewhere.").wait_for()
    page.get_by_role("tab", name="History").click()
    page.get_by_role("heading", name="Trial history").wait_for()
    walk.shot("history-after-remove")
    assert page.locator("a.back").inner_text() == "‹ Back to Elsewhere", page.locator("a.back").inner_text()
    assert f"list={ELSEWHERE}" in page.evaluate("location.hash"), page.evaluate("location.hash")
