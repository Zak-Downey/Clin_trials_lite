"""Fixtures for the walks: one browser per worker, a fresh context, app and registry per walk."""

from __future__ import annotations

import pytest

from walks import helper


@pytest.fixture(scope="session")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        chromium = pw.chromium.launch()
        yield chromium
        chromium.close()


@pytest.fixture
def registry():
    stand_in = helper.Registry()
    yield stand_in
    stand_in.close()


@pytest.fixture
def make_app(tmp_path, registry):
    apps = []

    def build(seed=None):
        app = helper.App(tmp_path, registry, seed)
        apps.append(app)
        return app

    yield build
    for app in apps:
        app.close()


@pytest.fixture(params=list(helper.VIEWPORTS))
def viewport(request):
    return request.param


class Walk:
    """The page, its guards and screenshots."""

    def __init__(self, page, guards, name):
        self.page, self.guards, self.name, self.count = page, guards, name, 0

    def shot(self, step: str) -> str:
        self.count += 1
        helper.SHOTS.mkdir(parents=True, exist_ok=True)
        path = helper.SHOTS / f"{self.name}-{self.count:02d}-{step}.png"
        self.page.screenshot(path=str(path))
        return str(path)


@pytest.fixture
def make_walk(browser, viewport, request):
    """walk = make_walk(app): a page on the app at the viewport, guarded."""
    contexts = []

    def build(app) -> Walk:
        width, height = helper.VIEWPORTS[viewport]
        # The browser is put in a different zone from the server so a page that
        # shifts a time into the browser's own zone shows.
        context = browser.new_context(
            viewport={"width": width, "height": height}, locale="en-US", timezone_id="Asia/Tokyo")
        context.set_default_timeout(5000)
        contexts.append(context)
        page = context.new_page()
        walk = Walk(page, helper.Guards(page, app.url.rstrip("/")),
                    f"{helper.shot_name(request.node.nodeid)}")
        request.node.walk = walk
        return walk

    yield build
    for context in contexts:
        context.close()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    walk = getattr(item, "walk", None)
    if walk is None or call.when != "call":
        return
    problems = [] if walk.page.is_closed() else walk.guards.problems()
    if report.failed or problems:
        try:
            walk.shot("final")
        except Exception:
            pass
    if problems and not report.failed:
        report.outcome = "failed"
        report.longrepr = "walk guard tripped:\n  " + "\n  ".join(problems)
