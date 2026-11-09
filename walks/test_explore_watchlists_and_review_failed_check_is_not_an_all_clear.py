"""Explore: a check in which every trial failed must not leave the empty queue reading "All caught up".

Data: helper.seed_queue; the "Quiet" watchlist (one trial, never checked), the stand-in
registry answering every lookup with a server error. Lacks: a partial failure.
Run: .venv/bin/python -m pytest -p walks.conftest <this file> -q
"""

from walks import helper


def test_walk_a_check_where_every_trial_failed_is_not_an_all_clear(make_app, make_walk):
    """test_walk_a_check_where_every_trial_failed_is_not_an_all_clear"""
    app = make_app(seed=helper.seed_queue)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url + "#/watchlists/2/needs-review")
    page.get_by_text("All caught up").wait_for()
    assert "Not checked yet" in page.locator("#watchlist-meta").inner_text()
    app.registry.set("server_error", True)
    page.get_by_role("button", name="Check for updates").click()
    page.get_by_text("Check incomplete").wait_for()
    walk.shot("failed-check")
    # The header's "Last checked" is when the check finished, by design (spec, "Check failures persist per trial").
    # The empty queue must not read as an all-clear while a trial's latest check failed.
    caught_up = page.locator(".caught-up").inner_text()
    assert "All caught up" not in caught_up, f"the empty queue after a total failure: {caught_up!r}"
    assert "could not be checked" in caught_up, caught_up
