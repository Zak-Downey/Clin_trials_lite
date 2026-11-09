"""Explore: a check in which every trial failed still stamps "Last checked <now>" and says "All caught up".

Data: helper.seed_queue; the "Quiet" watchlist (one trial, never checked), the stand-in
registry answering every lookup with a server error. Lacks: a partial failure.
Run: .venv/bin/python -m pytest -p walks.conftest <this file> -q
"""

from walks import helper


def test_walk_a_check_where_every_trial_failed_does_not_claim_a_last_checked_time(make_app, make_walk):
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
    meta = page.locator("#watchlist-meta").inner_text()
    caught_up = page.locator(".caught-up").inner_text()
    assert "Not checked yet" in meta or "Last checked" not in meta, f"header after a total failure: {meta!r}"
    assert "Last checked" not in caught_up, f"the empty queue after a total failure: {caught_up!r}"
