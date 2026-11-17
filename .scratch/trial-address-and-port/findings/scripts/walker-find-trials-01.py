"""walker-find-trials-01: after adding from the registry details page, the page still says "Not monitored".

Data: walks/test_trial_address_walk.py's seed; NCT00000003 is in no watchlist.
Red now: the line under the title keeps "Not monitored" beside "Added to Elsewhere.".
Green once the line names the watchlist the trial was just added to.
"""
from walks.test_trial_address_walk import seed_two_queues


def test_the_trial_line_names_the_watchlist_just_added_to(make_app, make_walk):
    app = make_app(seed=seed_two_queues)
    walk = make_walk(app)
    page = walk.page
    page.goto(f"{app.url}#/registry/NCT00000003")
    page.get_by_role("button", name="Add to watchlist").wait_for()
    meta = page.locator(".trial-head .meta")
    assert "Not monitored" in meta.inner_text()
    page.get_by_label("Add to").select_option(label="Elsewhere")
    page.get_by_role("button", name="Add to watchlist").click()
    page.get_by_text("Added to Elsewhere.").wait_for()
    walk.shot("added")
    assert "Not monitored" not in meta.inner_text(), meta.inner_text()
    assert "Elsewhere" in meta.inner_text(), meta.inner_text()
