"""Red: a trial held by many watchlists with long names. Run:
.venv/bin/python -m pytest -p walks.conftest .scratch/html-front-end/explore/trial-page/test_red_many_watchlists.py -q
"""
from __future__ import annotations

from walks.test_trial_page_walk import seed_trial_page


def seed_many(db, registry):
    import monitor
    import storage

    seed_trial_page(db, registry)
    conn = storage.connect(db)
    for n in range(40):
        name = "Z" * 70 if n == 0 else f'List <b>"{n}" & ünï ' + "long name " * 6
        lid = monitor.create_list(conn, name, when="2026-11-01T08:00:00+00:00")
        monitor.add(conn, "NCT03412565", lid, fetch=registry.fetch, when="2026-11-01T08:00:00+00:00")
    conn.close()


def test_the_review_bar_stays_small_and_the_page_does_not_scroll_sideways_with_many_long_named_lists(make_app, make_walk):
    """test_the_review_bar_stays_small_and_the_page_does_not_scroll_sideways_with_many_long_named_lists"""
    app = make_app(seed=seed_many)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url + "#/trials/NCT03412565")
    page.get_by_role("button", name="Mark reviewed").wait_for()
    walk.shot("bar")  # the shot's sideways-scroll guard fails the walk at 1024 x 768
    height = page.viewport_size["height"]
    assert page.get_by_role("region", name="Review").bounding_box()["height"] < height / 3
    mark = page.get_by_role("button", name="Mark reviewed").bounding_box()
    assert mark["x"] + mark["width"] <= page.viewport_size["width"]
    page.get_by_role("button", name="More actions").click()
    walk.shot("menu")
    assert page.get_by_role("menu").bounding_box()["height"] < height
