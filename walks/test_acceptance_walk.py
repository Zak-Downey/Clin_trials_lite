"""Walk: the acceptance journey, keyboard only, end to end (ticket 15).

Data: an empty database against the stand-in registry. The only step not taken through the
page is the registry's own revise and register switch. Every focus move is a Tab (or
Shift+Tab) key press and every action an Enter, Space, arrow or typed key: no click, no
fill, no select_option, no check. The first page load (goto) is the only navigation not made
by a key. WebKit reaches links and buttons with Option+Tab, as Safari does by default. Runs at 1440 x 900 and 1024 x 768 in Chromium and at 1440 x 900 in WebKit.
Lacks: Firefox, a real screen reader, a touch device, and the Simulated-label walk (separate).
"""

from __future__ import annotations

import csv
import io
import re

import pytest

from walks import helper

ENGINES = {
    "chromium-1440x900": ("chromium", (1440, 900)),
    "chromium-1024x768": ("chromium", (1024, 768)),
    "webkit-1440x900": ("webkit", (1440, 900)),
}


@pytest.fixture(params=list(ENGINES))
def engine(request):
    return request.param


@pytest.fixture
def viewport(engine):  # replaces conftest's: the walk's own three runs
    helper.VIEWPORTS.setdefault(engine, ENGINES[engine][1])
    return engine


@pytest.fixture
def browser(engine):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        launched = getattr(pw, ENGINES[engine][0]).launch()
        yield launched
        launched.close()


# What a control must show when it has focus, read from the page's computed style.
RING = """(e) => {
  const s = getComputedStyle(e);
  const outline = s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0;
  const shadow = s.boxShadow !== 'none';
  return outline || shadow;
}"""

# The control's accessible name, as far as a text label goes: aria-label, label, text, value.
NAME = """(e) => {
  const by = (id) => (document.getElementById(id) || {}).innerText;
  const label = e.labels && e.labels.length ? [...e.labels].map((l) => l.innerText).join(' ') : '';
  const named = e.getAttribute('aria-labelledby') ? e.getAttribute('aria-labelledby').split(' ').map(by).join(' ') : '';
  return (e.getAttribute('aria-label') || named || label || e.innerText || e.value || e.title || '').trim();
}"""

REAL = {"A", "BUTTON", "INPUT", "SELECT", "SUMMARY", "TEXTAREA"}


class Keys:
    """Moves and acts only with the keyboard, and records every control it reaches."""

    def __init__(self, page, engine, walk=None):
        self.page, self.engine, self.walk, self.reached = page, engine, walk, []

    def chord(self, back: bool) -> str:
        """Safari's Tab skips links and buttons unless Option is held (its default setting); Option+Tab is its way."""
        base = "Shift+Tab" if back else "Tab"
        return f"Alt+{base}" if ENGINES[self.engine][0] == "webkit" else base

    def _is_active(self, target) -> bool:
        return target.evaluate("(e) => e === document.activeElement")

    def _before_active(self, target) -> bool:
        return target.evaluate(
            "(e) => { const a = document.activeElement; return a !== document.body && "
            "!!(e.compareDocumentPosition(a) & Node.DOCUMENT_POSITION_FOLLOWING) }")

    def focus(self, target, limit=300):
        """Tab (or Shift+Tab, when the target precedes the focus) until target holds focus."""
        target = target.first
        target.wait_for(state="visible")
        for _ in range(limit):
            if self._is_active(target):
                break
            self.page.keyboard.press(self.chord(self._before_active(target)))
            self.moved()
            if not self._is_active(target):
                self.pass_stop()
        else:
            raise AssertionError(f"could not reach {target} by keyboard in {limit} presses")
        self.note(target)
        return target

    def moved(self):
        """After a key: no sideways scroll of the page or a region, and no open dialog wider than the window."""
        if self.walk is not None:
            self.walk.guards.measure()
        wide = self.page.evaluate(
            "() => [document.documentElement.scrollWidth - document.documentElement.clientWidth, "
            "[...document.querySelectorAll('dialog[open]')].some((d) => { const r = d.getBoundingClientRect(); "
            "return r.left < -1 || r.right > document.documentElement.clientWidth + 1; })]")
        assert wide[0] <= 0, f"horizontal scrolling: the page is {wide[0]}px wider than the window"
        assert not wide[1], "horizontal scrolling: an open dialog is wider than the window"

    def pass_stop(self):
        """A stop passed on the way (not aimed at) must be a real control with a name and a ring."""
        if self.page.evaluate("document.activeElement === document.body"):
            return
        before = len(self.reached)
        self.note(self.page.locator(":focus").first)
        bad = [c for c in self.reached[before:] if not (c["real"] and c["name"] and c["ring"])]
        assert not bad, f"a stop passed on the way is not a real, named, ringed control: {bad}"

    def note(self, target):
        info = target.evaluate(
            "(e) => ({tag: e.tagName, type: e.type || '', text: (e.innerText || '').trim().slice(0, 40), "
            "id: e.id, nct: (e.closest('[data-nct]') || {dataset: {}}).dataset.nct || ''})")
        info["name"] = target.evaluate(NAME)
        info["ring"] = target.evaluate(RING)
        info["real"] = info["tag"] in REAL
        self.reached.append(info)

    def press(self, target, key="Enter"):
        self.focus(target).press(key)
        self.moved()

    def type(self, target, text, submit=False):
        field = self.focus(target)
        self.page.keyboard.type(text)
        if submit:
            self.page.keyboard.press("Enter")
        self.moved()

    def choose(self, select, label):
        """Pick an option of a focused <select> by typing its name."""
        field = self.focus(select)
        self.page.keyboard.type(label)
        self.moved()
        shown = field.evaluate("(s) => s.selectedOptions[0].textContent")
        assert shown == label, shown


def open_empty(make_app, make_walk, engine):
    app = make_app()
    walk = make_walk(app)
    walk.page.goto(app.url)
    walk.page.get_by_role("heading", level=1).wait_for()
    return app, walk, Keys(walk.page, engine, walk)


def sidebar(page, name):
    return page.get_by_label("Watchlists").get_by_role("link", name=re.compile(f"^{name}"))


def test_walk_the_whole_journey_by_keyboard_alone(make_app, make_walk, engine, tmp_path):
    """test_walk_the_whole_journey_by_keyboard_alone"""
    app, walk, keys = open_empty(make_app, make_walk, engine)
    page = walk.page
    pending = []

    # 1. Create a watchlist from the sidebar.
    keys.press(page.get_by_role("button", name="+ New watchlist"))
    dialog = page.get_by_role("dialog", name="New watchlist")
    dialog.wait_for()
    assert page.evaluate("document.activeElement.id") == "new-watchlist-name"  # focus lands in the dialog
    page.keyboard.type("Myeloma")
    page.keyboard.press("Enter")  # submits the form
    dialog.wait_for(state="detached")
    sidebar(page, "Myeloma").wait_for()
    walk.shot("created")

    # 2. Search; select across two pages; add.
    keys.press(page.get_by_role("navigation").get_by_role("link", name="Find trials"))
    page.get_by_role("heading", level=1, name="Find trials").wait_for()
    keys.type(page.get_by_label("Condition"), "many", submit=True)
    page.get_by_role("heading", name="134 matches").wait_for()
    box = lambda nct: page.locator(f'li.card[data-nct="{nct}"] input[type=checkbox]')  # noqa: E731
    for nct in ("NCT10000001", "NCT10000002"):
        keys.press(box(nct), "Space")
    page.get_by_text("2 trials selected").wait_for()
    keys.press(page.get_by_role("button", name="Next"))
    page.get_by_text("11–20 of 134 matches").wait_for()
    keys.press(box("NCT10000011"), "Space")
    page.get_by_text("3 trials selected").wait_for()
    assert box("NCT10000011").is_checked()
    walk.shot("selected")
    keys.choose(page.get_by_label("Add to"), "Myeloma")
    keys.press(page.get_by_role("button", name="Add 3 trials"))
    page.get_by_text("3 added").wait_for()
    assert sidebar(page, "Myeloma").locator(".counts").inner_text() == "3 trials"
    walk.shot("added")

    # 3. The trial the registry will revise comes in by its ID.
    keys.press(page.get_by_role("tab", name="Add by NCT ID"))
    keys.choose(page.get_by_label("Destination"), "Myeloma")
    keys.type(page.get_by_label("NCT ID"), "NCT03412565", submit=True)
    page.locator(".found", has_text="NCT03412565").wait_for()
    keys.press(page.get_by_role("button", name="Add to watchlist"))
    page.get_by_text("Added NCT03412565 to Myeloma.").wait_for()

    # 4. Save a search that finds the registry's three studies.
    keys.press(page.get_by_role("tab", name="Search"))
    page.get_by_role("heading", level=1, name="Find trials").wait_for()
    keys.type(page.get_by_label("Condition"), "myeloma", submit=True)
    page.get_by_role("heading", name="3 matches").wait_for()
    keys.press(page.get_by_role("button", name="Watch this search"))
    watch = page.get_by_role("dialog", name="Watch this search")
    watch.wait_for()
    keys.choose(watch.get_by_label("Watchlist"), "Myeloma")
    keys.press(watch.get_by_role("button", name="Watch this search"))
    watch.get_by_role("heading", name="Search saved").wait_for()
    keys.press(watch.get_by_role("link", name=re.compile("^Open watchlist")))
    page.get_by_role("heading", level=1, name="Myeloma").wait_for()
    page.get_by_text("Saved search is on").wait_for()
    walk.shot("saved-search")

    # 5. Check for updates: nothing has moved yet.
    keys.press(page.get_by_role("button", name="Check for updates"))
    status = page.locator("#check-status")
    status.get_by_text("Check complete · No new changes detected").wait_for(timeout=30000)
    assert "Saved search succeeded: 2 new trials found." in status.inner_text(), status.inner_text()
    page.get_by_text("All caught up").wait_for()

    # 6. The registry moves (the walk's one step off the page), and the next check sees it.
    app.registry.set("revise", True)
    app.registry.set("register", True)
    keys.press(page.get_by_role("button", name="Check for updates"))
    status.get_by_text("Check complete · 1 trial changed").wait_for(timeout=30000)
    assert "Saved search succeeded: 1 new trial found." in status.inner_text(), status.inner_text()
    card = page.locator('li.card[data-nct="NCT03412565"]')
    card.wait_for()
    assert sidebar(page, "Myeloma").locator(".badge").get_attribute("title") == "1 to review"
    walk.shot("changed")

    # 7. Open the changed trial; review it; undo; review again.
    keys.press(card.locator("h3 a"))
    page.get_by_role("button", name="Mark reviewed").wait_for()
    changes = page.locator("article.change")
    assert changes.count() >= 3
    walk.shot("trial")
    keys.press(page.get_by_role("button", name="Mark reviewed"))
    page.get_by_text(re.compile(r"\d+ changes? marked reviewed")).wait_for()
    assert page.evaluate("document.activeElement.textContent") == "Undo"  # the pressed button is now disabled: focus moves on, not to <body>
    labels = page.locator(".reviewed-label:visible")
    assert labels.count() == changes.count()
    assert all(text.strip() for text in labels.all_inner_texts())  # said in words, not by colour
    page.locator(f'.badge[title="0 to review"]').first.wait_for(state="attached")
    keys.press(page.get_by_role("button", name="Undo"))
    page.get_by_role("button", name="Undo").wait_for(state="detached")
    assert page.evaluate("document.activeElement.textContent") == "Mark reviewed"
    assert page.locator(".reviewed-label:visible").count() == 0
    page.get_by_role("button", name="Mark reviewed").wait_for()
    keys.press(page.get_by_role("button", name="Mark reviewed"))
    page.get_by_text(re.compile(r"\d+ changes? marked reviewed")).wait_for()
    walk.shot("reviewed")
    keys.press(page.get_by_role("link", name="‹ Back to Myeloma"))
    page.get_by_role("heading", level=1, name="Myeloma").wait_for()
    page.get_by_text("All caught up").wait_for()

    # 8. New matches: add the new one; dismiss one and restore it.
    keys.press(page.get_by_role("tab", name=re.compile("^New matches")))
    page.get_by_role("heading", level=2, name="3 new matches").wait_for()
    match = lambda nct: page.locator(f'li.card[data-nct="{nct}"] input[type=checkbox]')  # noqa: E731
    bar = page.get_by_role("region", name="New matches actions")
    keys.press(match("NCT00000099"), "Space")
    bar.get_by_text("1 selected").wait_for()
    keys.press(bar.get_by_role("button", name="Add 1 to watchlist"))
    bar.get_by_text("1 added").wait_for()
    page.get_by_role("heading", level=2, name="2 new matches").wait_for()
    keys.press(match("NCT00000002"), "Space")
    keys.press(bar.get_by_role("button", name="Dismiss 1"))
    keys.press(bar.get_by_role("button", name="Yes, dismiss 1"))
    bar.get_by_text("1 trial dismissed.").wait_for()
    page.get_by_role("heading", level=2, name="1 new match").wait_for()
    walk.shot("dismissed")
    keys.press(page.get_by_role("button", name="View dismissed"))
    page.get_by_role("heading", level=2, name="1 dismissed match").wait_for()
    keys.press(page.locator('li.card[data-nct="NCT00000002"]').get_by_role("button", name=re.compile("^Restore")))
    page.get_by_text("Nothing has been dismissed.").wait_for()
    keys.press(page.get_by_role("button", name="Back to new matches"))
    page.get_by_role("heading", level=2, name="2 new matches").wait_for()
    page.locator('li.card[data-nct="NCT00000002"]').wait_for()

    # 9. Summary: view, copy, export.
    keys.press(page.get_by_role("tab", name="Summary"))
    page.locator("#summary-heading").wait_for()
    heading = page.locator("#summary-heading").inner_text()
    assert re.search(r"1 trial · [1-9]\d* field changes?", heading), heading
    walk.shot("summary")
    page.context.grant_permissions(["clipboard-read", "clipboard-write"], origin=app.url.rstrip("/")) \
        if ENGINES[engine][0] == "chromium" else None
    keys.press(page.get_by_role("button", name="Copy summary"))
    page.locator("#summary-notice").wait_for()
    if ENGINES[engine][0] == "chromium":
        text = page.evaluate("() => navigator.clipboard.readText()")
        assert "https://clinicaltrials.gov/study/NCT03412565" in text
    with page.expect_download() as info:
        keys.press(page.get_by_role("button", name="Export CSV"))
    rows = list(csv.DictReader(io.StringIO(open(info.value.path(), encoding="utf-8").read())))
    assert rows and {r["NCT ID"] for r in rows} == {"NCT03412565"}
    assert {r["Review status"] for r in rows} == {"Reviewed"}
    walk.shot("exported")

    # Every control reached is a real control with a name and a focus ring.
    assert len(keys.reached) > 30
    bad = [c for c in keys.reached if not (c["real"] and c["name"] and c["ring"])]
    assert not bad, bad


def crawl(page, keys, limit=400):
    """Tab through every stop of the current view, noting each; stop on a stop already seen or on <body>."""
    page.evaluate("document.querySelectorAll('[data-crawled]').forEach((e) => e.removeAttribute('data-crawled'))")
    page.evaluate("document.activeElement && document.activeElement.blur()")
    seen = 0
    for _ in range(limit):
        page.keyboard.press(keys.chord(False))
        if page.evaluate("document.activeElement === document.body || document.activeElement.hasAttribute('data-crawled')"):
            break
        page.evaluate("document.activeElement.setAttribute('data-crawled', '1')")
        keys.note(page.locator("[data-crawled]:focus"))
        seen += 1
    else:
        raise AssertionError("the tab order never came round")
    return seen


def assert_controls(keys, since=0):
    bad = [c for c in keys.reached[since:] if not (c["real"] and c["name"] and c["ring"])]
    assert not bad, bad


# Properties that say a state without colour: weight, a line, a border, a mark in the text.
NOT_COLOUR = """(e) => {
  const s = getComputedStyle(e), b = getComputedStyle(e, '::before');
  return JSON.stringify([s.fontWeight, s.fontStyle, s.textDecorationLine, s.borderBottomWidth, s.borderLeftWidth,
    s.borderTopWidth, s.outlineStyle, s.boxShadow === 'none' ? '' : 'shadow', b.content]);
}"""


def differs_beyond_colour(on, off):
    return on.evaluate(NOT_COLOUR) != off.evaluate(NOT_COLOUR)


def test_walk_every_stop_in_every_view_is_a_real_labelled_control_with_a_focus_ring_and_states_are_not_colour_alone(make_app, make_walk, engine):
    """test_walk_every_stop_in_every_view_is_a_real_labelled_control_with_a_focus_ring_and_states_are_not_colour_alone"""
    from walks.test_trial_page_walk import seed_trial_page

    app = make_app(seed=seed_trial_page)
    walk = make_walk(app)
    page = walk.page
    keys = Keys(page, engine, walk)
    page.goto(app.url)
    page.locator("ul.queue > li.card").first.wait_for()
    stops = {}
    for name, hash_, ready in (
        ("needs-review", "#/watchlists/1/needs-review", 'li.card[data-nct="NCT03412565"]'),
        ("all-trials", "#/watchlists/1/all-trials", 'tr[data-nct="NCT03412565"]'),
        ("summary", "#/watchlists/1/summary", "#summary-heading"),
        ("trial", "#/trials/NCT03412565", 'article.change'),
        ("find", "#/find", 'input#find-cond, [name=cond]'),
    ):
        page.evaluate("(h) => { location.hash = h }", hash_)
        page.locator(ready).first.wait_for()
        before = len(keys.reached)
        stops[name] = crawl(page, keys)
        assert stops[name] >= 8, (name, stops)
        assert_controls(keys, before)
        walk.shot(f"crawl-{name}")
    # The tab and the sidebar link that are current differ from the others by more than colour.
    page.evaluate("(h) => { location.hash = h }", "#/watchlists/1/needs-review")
    page.locator("li.card").first.wait_for()
    tabs = page.get_by_role("tablist", name="Watchlist views").get_by_role("tab")
    assert tabs.nth(0).get_attribute("aria-selected") == "true"
    assert differs_beyond_colour(tabs.nth(0), tabs.nth(1))
    assert tabs.nth(0).get_attribute("aria-selected") != tabs.nth(1).get_attribute("aria-selected")
    links = page.get_by_label("Watchlists").get_by_role("link")
    current = page.get_by_label("Watchlists").locator("a.active")
    other = page.get_by_label("Watchlists").locator("a:not(.active)")
    assert differs_beyond_colour(current.first, other.first)
    assert current.first.get_attribute("aria-current") == "page"
    # A selected phase carries a mark in its text; a selected result is a checked checkbox with a count in words.
    page.evaluate("(h) => { location.hash = h }", "#/find")
    page.get_by_role("button", name="More filters").wait_for()
    keys.press(page.get_by_role("button", name="More filters"))
    toggles = page.locator("button.toggle")
    keys.press(toggles.first, "Space")
    assert toggles.first.get_attribute("aria-pressed") == "true"
    assert differs_beyond_colour(toggles.first, toggles.nth(1))
    keys.type(page.get_by_label("Condition"), "many", submit=True)
    page.get_by_role("heading", name="134 matches").wait_for()
    keys.press(page.locator("li.card input[type=checkbox]").first, "Space")
    page.get_by_text("1 trial selected").wait_for()
    before = len(keys.reached)
    crawl(page, keys)
    assert_controls(keys, before)
    walk.shot("crawl-results")


def test_walk_a_failed_trial_in_a_check_is_named_in_words_and_its_retry_is_reachable_by_keyboard(make_app, make_walk, engine):
    """test_walk_a_failed_trial_in_a_check_is_named_in_words_and_its_retry_is_reachable_by_keyboard"""
    from walks.test_check_walk import seed_checked

    app = make_app(seed=seed_checked)
    walk = make_walk(app)
    page = walk.page
    keys = Keys(page, engine, walk)
    page.goto(app.url)
    page.get_by_role("button", name="Check for updates").wait_for()
    app.registry.set("fail", True, ids=["NCT00000002"])
    keys.press(page.get_by_role("button", name="Check for updates"))
    status = page.get_by_role("status")
    status.get_by_role("heading", name="Check incomplete").wait_for(timeout=30000)
    assert "1 trial could not be checked" in status.inner_text()
    keys.press(status.get_by_role("button", name="Show details"))
    assert "NCT00000002" in status.locator(".details").inner_text()
    app.registry.set("fail", False)
    keys.press(status.get_by_role("button", name="Retry failed"))
    status.get_by_text("Check complete").wait_for(timeout=30000)
    before = 0
    assert_controls(keys, before)
    walk.shot("failed-then-retried")


def open_new_watchlist(make_app, make_walk, engine):
    app, walk, keys = open_empty(make_app, make_walk, engine)
    keys.press(walk.page.get_by_role("button", name="+ New watchlist"))
    walk.page.get_by_role("dialog", name="New watchlist").wait_for()
    return walk, keys


def test_walk_the_acceptance_journey_measures_horizontal_scroll_on_every_keyboard_move_and_fails_on_a_wide_new_watchlist_dialog(make_app, make_walk, engine):
    """test_walk_the_acceptance_journey_measures_horizontal_scroll_on_every_keyboard_move_and_fails_on_a_wide_new_watchlist_dialog"""
    walk, keys = open_new_watchlist(make_app, make_walk, engine)
    page = walk.page
    keys.type(page.get_by_label("Name"), "Wide")  # a normal dialog passes every move
    page.add_style_tag(content="#view { min-width: 3000px; }")  # the page itself goes wide
    with pytest.raises(AssertionError, match="the page is"):
        keys.type(page.get_by_label("Name"), "Wide")
    page.add_style_tag(content="#view { min-width: 0 !important; }")
    page.add_style_tag(content="dialog.dialog { width: 2400px !important; max-width: none !important; }")
    with pytest.raises(AssertionError, match="wider than the window"):
        keys.press(page.get_by_role("button", name="Cancel"))
    walk.guards.found.clear()  # the failure is the point here


def test_walk_the_acceptance_journey_checks_every_tab_stop_it_passes_and_fails_when_a_control_passed_on_the_way_loses_its_name(make_app, make_walk, engine):
    """test_walk_the_acceptance_journey_checks_every_tab_stop_it_passes_and_fails_when_a_control_passed_on_the_way_loses_its_name"""
    walk, keys = open_new_watchlist(make_app, make_walk, engine)
    page = walk.page
    keys.focus(page.get_by_label("Name"))
    before = len(keys.reached)
    keys.focus(page.get_by_role("button", name="Create watchlist"))  # passes Cancel, named: fine
    assert any(c["text"] == "Cancel" for c in keys.reached[before:]), keys.reached[before:]
    keys.focus(page.get_by_label("Name"))
    page.get_by_role("button", name="Cancel").evaluate("(b) => { b.textContent = ''; }")  # Cancel loses its name
    with pytest.raises(AssertionError, match="not a real, named, ringed control"):
        keys.focus(page.locator("button.primary"))
