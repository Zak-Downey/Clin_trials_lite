"""walker-find-trials-02: a long watchlist name in "Add to" crushes the trial's title on the registry details page.

Data: walks/helper.py's seed_queue (watchlist 1 has the long name). At 1024 x 768 the title
is one or two letters per line and the picker runs past the right edge of the window.
Green once the title keeps a readable width and the picker stays inside the window.
"""
from walks import helper


def test_a_long_watchlist_name_leaves_the_title_readable(make_app, make_walk):
    app = make_app(seed=helper.seed_queue)
    walk = make_walk(app)
    page = walk.page
    page.goto(f"{app.url}#/registry/NCT00000002")
    page.get_by_role("button", name="Add to watchlist").wait_for()
    page.get_by_label("Add to").select_option(index=0)
    walk.shot("long-name-picked")
    title = page.get_by_role("heading", level=1).bounding_box()
    pick = page.get_by_label("Add to").bounding_box()
    width = page.evaluate("document.documentElement.clientWidth")
    assert title["width"] >= 240, f"the title is {title['width']:.0f}px wide"
    assert pick["x"] + pick["width"] <= width, f"the picker ends at {pick['x'] + pick['width']:.0f}px in a {width}px window"
