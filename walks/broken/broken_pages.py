"""Deliberately broken pages, one per guard. Not part of the suite: test_walk_guards.py
runs this file by name and expects every walk in it to FAIL. Lacks: everything but the fault."""


def start(make_app, make_walk):
    app = make_app()
    walk = make_walk(app)
    walk.page.goto(app.url)
    walk.page.wait_for_load_state("networkidle")
    return walk


def test_broken_console_error(make_app, make_walk):
    """broken page: a console error"""
    start(make_app, make_walk).page.evaluate("console.error('deliberate console error')")


def test_broken_failed_request(make_app, make_walk):
    """broken page: a failed request"""
    page = start(make_app, make_walk).page
    page.evaluate("fetch('/static/missing-file.js').catch(() => {})")
    page.wait_for_timeout(300)


def test_broken_foreign_request(make_app, make_walk):
    """broken page: a request to somewhere but the app"""
    page = start(make_app, make_walk).page
    page.evaluate("fetch('http://127.0.0.1:9/elsewhere').catch(() => {})")
    page.wait_for_timeout(300)


def test_broken_sideways_scroll(make_app, make_walk):
    """broken page: horizontal scrolling"""
    page = start(make_app, make_walk).page
    page.evaluate("document.body.insertAdjacentHTML('beforeend', '<div style=\"width:3000px;height:1px\"></div>')")


def test_broken_page_error(make_app, make_walk):
    """broken page: an uncaught page error"""
    page = start(make_app, make_walk).page
    page.evaluate("setTimeout(() => { throw new Error('deliberate') }, 0)")
    page.wait_for_timeout(300)


def test_broken_request_to_the_app_that_gets_no_answer(make_app, make_walk):
    """broken page: a request to the app's own server that fails at the network"""
    page = start(make_app, make_walk).page
    page.route("**/static/aborted.js", lambda route: route.abort())
    page.evaluate("fetch('/static/aborted.js').catch(() => {})")
    page.wait_for_timeout(300)


def test_broken_sideways_scroll_only_in_the_middle(make_app, make_walk):
    """broken page: wider than the window at a screenshot, narrow again by the end"""
    walk = start(make_app, make_walk)
    walk.page.evaluate("document.body.insertAdjacentHTML('beforeend', '<div id=\"wide\" style=\"width:3000px;height:1px\"></div>')")
    walk.shot("wide")
    walk.page.evaluate("document.getElementById('wide').remove()")


def test_broken_region_that_scrolls_sideways(make_app, make_walk):
    """broken page: a region scrolling sideways inside the page"""
    page = start(make_app, make_walk).page
    page.evaluate("""document.body.insertAdjacentHTML('beforeend',
      '<div id="strip" style="width:200px;overflow-x:auto"><div style="width:900px;height:1px"></div></div>')""")


def test_broken_first_of_two_pages_has_an_error(make_app, make_walk):
    """broken page: the first of two pages logs an error"""
    app = make_app()
    first = make_walk(app)
    first.page.goto(app.url)
    first.page.wait_for_load_state("networkidle")
    first.page.evaluate("console.error('error on the first page')")
    second = make_walk(app)
    second.page.goto(app.url)
    second.page.wait_for_load_state("networkidle")


def test_broken_expected_response_that_never_comes(make_app, make_walk):
    """broken page: a walk expects a 404 and the app answers 200"""
    walk = start(make_app, make_walk)
    walk.expect(404, "/api/watchlists")
    walk.page.evaluate("fetch('/api/watchlists')")
    walk.page.wait_for_timeout(300)


def test_broken_other_status_than_the_expected_one(make_app, make_walk):
    """broken page: a walk expects a 404 and gets one at another path"""
    walk = start(make_app, make_walk)
    walk.expect(404, "/api/watchlists/999/needs-review")
    walk.page.evaluate("fetch('/api/watchlists/998/needs-review')")
    walk.page.wait_for_timeout(300)


def test_broken_page_closed_after_an_error(make_app, make_walk):
    """broken page: a console error and then the page is closed"""
    walk = start(make_app, make_walk)
    walk.page.evaluate("console.error('error before the page closed')")
    walk.page.close()
