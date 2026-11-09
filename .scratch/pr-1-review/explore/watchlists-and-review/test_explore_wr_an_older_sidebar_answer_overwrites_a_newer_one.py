"""Explore: two quick review changes whose sidebar answers arrive in the wrong order leave stale badges.

Data: helper.seed_queue. The slow answer is held by Playwright (read from the server at once, delivered later).
Lacks: the same race on the header's own re-read (check.js onChange).
Run: .venv/bin/python -m pytest -p walks.conftest --rootdir . <this file> -q
"""

from walks import helper


def badges(page):
    return page.evaluate("[...document.querySelectorAll('#sidebar a')].map((a) => a.querySelector('.badge').textContent)")


def test_walk_a_late_older_sidebar_answer_does_not_overwrite_the_newer_badges(make_app, make_walk):
    app = make_app(seed=helper.seed_queue)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url + "#/trials/NCT00000002")
    page.get_by_role("button", name="Mark reviewed").wait_for()
    page.wait_for_timeout(300)
    held = []

    def handler(route):
        if route.request.method == "GET" and not held:
            held.append((route, route.fetch()))  # the answer as it stands after Mark reviewed
        else:
            route.continue_()

    page.route("**/api/watchlists", handler)
    page.get_by_role("button", name="Mark reviewed").click()
    page.get_by_role("button", name="Undo").wait_for()
    page.wait_for_timeout(200)
    assert held, "Mark reviewed did not re-read the watchlists"
    page.get_by_role("button", name="Undo").click()
    page.get_by_role("button", name="Mark reviewed").wait_for()
    page.wait_for_timeout(500)
    assert badges(page) == ["2", "0"]
    held[0][0].fulfill(response=held[0][1])  # the older answer arrives last
    page.wait_for_timeout(500)
    walk.shot("after-late-answer")
    assert badges(page) == ["2", "0"], f"the sidebar shows {badges(page)}: an older answer overwrote the newer one"
