"""Explore: a watchlist name with no break points (a long code or URL) pushes the page wider than the window.

Data: helper.seed_queue, with watchlist 1 renamed to 200 unbroken characters, and an
empty watchlist made through "+ New watchlist" with the same kind of name. Lacks: names
with spaces (those wrap).
Run: .venv/bin/python -m pytest -p walks.conftest <this file> -q
"""

from walks import helper

UNBROKEN = "x" * 200


def seed(db, registry):
    import monitor
    import storage
    helper.seed_queue(db, registry)
    conn = storage.connect(db)
    monitor.rename_list(conn, storage.list_lists(conn)[0]["id"], UNBROKEN)
    conn.close()


def too_wide(page):
    return page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")


def test_walk_an_unbroken_name_does_not_widen_the_trial_page(make_app, make_walk):
    """Back to <name> and the Removed from <name> banner must wrap."""
    app = make_app(seed=seed)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url)
    page.get_by_role("link", name="Review changes").first.click()
    page.get_by_role("button", name="Mark reviewed").wait_for()
    assert too_wide(page) == 0, "the Back to link is wider than the window"
    walk.shot("back-link")
    page.get_by_role("button", name="More actions").click()
    page.get_by_role("menuitem", name="Remove from this list").click()
    page.get_by_text("Its history is kept").or_(page.get_by_text("Removed from")).first.wait_for()
    assert too_wide(page) == 0, "the Removed from banner is wider than the window"
    walk.shot("removed-banner")


def test_walk_an_unbroken_name_does_not_widen_the_first_use_page(make_app, make_walk):
    """A new, empty watchlist shows the name as a heading; it must wrap."""
    app = make_app(seed=helper.seed_queue)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url)
    page.get_by_role("heading", level=1).wait_for()
    page.get_by_role("button", name="+ New watchlist").click()
    page.get_by_label("Name").fill(UNBROKEN)
    page.get_by_role("button", name="Create watchlist").click()
    page.get_by_label("Watchlists").get_by_role("link", name=UNBROKEN).click()
    page.get_by_role("heading", name="Monitor your first trial").wait_for()
    walk.shot("first-use")
    assert too_wide(page) == 0, "the first-use heading is wider than the window"
