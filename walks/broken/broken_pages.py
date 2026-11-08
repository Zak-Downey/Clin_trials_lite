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
