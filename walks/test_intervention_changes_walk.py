"""Walk: an interventions change names what was removed, added and unchanged (intervention-changes, ticket 02).

Data: the trial page's seed (walks/test_trial_page_walk.py): NCT03412565 checked
against the stand-in registry's "revise" record, one intervention fewer
(Carfilzomib), beside completion date and enrolment moves; NCT00000002 simulated,
whose rewound past lacks Carfilzomib, so its check finds it added. Two fillers
gain an interventions change each: NCT10000001 a full replacement, NCT10000002
a list that went from filled to empty and one from empty to filled. The comma
walk's own seed gives NCT10000001 a name holding a comma ("Interferon alfa-2b,
recombinant") that the record split into two names. Lacks: a long unbroken drug
name, and a change in the History tab's wording (unchanged).
"""

from __future__ import annotations

from walks.test_trial_page_walk import open_trial, seed_trial_page

SIX = ["Daratumumab", "Bortezomib", "Lenalidomide", "Dexamethasone", "Melphalan", "Prednisone"]


def seed(db, registry):
    import storage

    seed_trial_page(db, registry)
    conn = storage.connect(db)
    storage.add_change(conn, "NCT10000001", {"field": "interventions", "previous": ["Melphalan", "Prednisone"],
                                             "current": ["Carfilzomib", "Dexamethasone"]}, "2026-11-08T10:00:00+00:00")
    storage.add_change(conn, "NCT10000002", {"field": "interventions", "previous": ["Melphalan", "Prednisone"],
                                             "current": []}, "2026-11-08T10:00:00+00:00")
    storage.add_change(conn, "NCT10000002", {"field": "interventions", "previous": [],
                                             "current": ["Carfilzomib", "Dexamethasone"]}, "2026-11-08T11:00:00+00:00")
    conn.close()


def _rows(card):
    """Each line of an interventions card as (label, what it says), in order.

    A line naming interventions says them as a list, one entry per drawn list item,
    so two names never read as one and one name holding a comma never reads as two.
    A line with no list item ("None", the unchanged count) says its text as one entry.
    """
    words = ("(el) => { const items = [...el.querySelectorAll('li')].map((li) => li.textContent.trim());"
             " if (items.length) return items;"
             " const c = el.cloneNode(true); c.querySelectorAll('button').forEach((b) => b.remove());"
             " return [c.textContent.trim()]; }")
    return [(row.locator(".split-label").inner_text().strip(), row.locator(".split-names").evaluate(words))
            for row in card.locator(".split-row").all()]


def test_walk_a_removed_intervention_reads_removed_added_none_and_six_unchanged_behind_show(make_app, make_walk):
    """test_walk_a_removed_intervention_reads_removed_added_none_and_six_unchanged_behind_show"""
    _, walk = open_trial(make_app, make_walk)
    page = walk.page
    card = page.locator("article.change", has_text="Interventions")
    assert card.count() == 1
    assert _rows(card) == [("Removed", ["Carfilzomib"]), ("Added", ["None"]), ("Unchanged", ["6 interventions"])]
    assert card.get_by_text("Previously").count() == 0 and card.get_by_text("Now", exact=True).count() == 0
    names = card.locator(".unchanged-names")
    assert names.is_hidden()
    for name in SIX:
        assert card.get_by_text(name, exact=True).count() == 0 or card.get_by_text(name, exact=True).is_hidden()
    walk.shot("folded")

    show = card.get_by_role("button", name="Show")
    assert show.get_attribute("aria-expanded") == "false"
    show.focus()
    page.keyboard.press("Enter")
    hide = card.get_by_role("button", name="Hide")
    hide.wait_for()
    assert hide.get_attribute("aria-expanded") == "true"
    assert names.is_visible()
    assert [n.strip() for n in names.locator("li").all_inner_texts()] == SIX
    walk.shot("unfolded")
    page.keyboard.press("Space")
    card.get_by_role("button", name="Show").wait_for()
    assert names.is_hidden()
    assert card.get_by_role("button", name="Show").get_attribute("aria-expanded") == "false"

    # Every other change on the page keeps Previously / Now.
    others = page.locator("article.change").filter(has_not_text="Interventions")
    assert others.count() == 4
    for i in range(others.count()):
        other = others.nth(i)
        assert other.get_by_text("Previously").count() == 1 and other.get_by_text("Now", exact=True).count() == 1
    assert page.evaluate("(el) => el.scrollWidth <= el.clientWidth", card.element_handle())


def test_walk_a_simulated_added_intervention_reads_removed_none_and_keeps_the_simulated_label(make_app, make_walk):
    """test_walk_a_simulated_added_intervention_reads_removed_none_and_keeps_the_simulated_label"""
    _, walk = open_trial(make_app, make_walk, "NCT00000002")
    page = walk.page
    assert page.get_by_text("Simulated changes").is_visible()
    card = page.locator("article.change", has_text="Interventions")
    assert _rows(card) == [("Removed", ["None"]), ("Added", ["Carfilzomib"]), ("Unchanged", ["6 interventions"])]
    walk.shot("simulated")
    page.get_by_role("button", name="Mark reviewed").click()
    page.get_by_text("changes marked reviewed. This trial stays open.").wait_for()
    assert card.locator(".reviewed-label").is_visible()


def test_walk_a_replaced_emptied_and_filled_list_each_read_by_side(make_app, make_walk):
    """test_walk_a_replaced_emptied_and_filled_list_each_read_by_side"""
    app = make_app(seed=seed)
    walk = make_walk(app)
    page = walk.page
    page.goto(f"{app.url}#/trials/NCT10000001")
    card = page.locator("article.change", has_text="Interventions")
    card.wait_for()
    assert _rows(card) == [("Removed", ["Melphalan", "Prednisone"]),
                           ("Added", ["Carfilzomib", "Dexamethasone"]), ("Unchanged", ["None"])]
    assert card.get_by_role("button").count() == 0
    walk.shot("replaced")

    page.goto(f"{app.url}#/trials/NCT10000002")
    cards = page.locator("article.change", has_text="Interventions")
    cards.nth(1).wait_for()
    assert _rows(cards.nth(0)) == [("Removed", ["None"]), ("Added", ["Carfilzomib", "Dexamethasone"]),
                                   ("Unchanged", ["None"])]
    assert _rows(cards.nth(1)) == [("Removed", ["Melphalan", "Prednisone"]), ("Added", ["None"]),
                                   ("Unchanged", ["None"])]
    walk.shot("emptied-and-filled")


def seed_comma(db, registry):
    import storage

    seed_trial_page(db, registry)
    conn = storage.connect(db)
    storage.add_change(conn, "NCT10000001", {"field": "interventions",
                                             "previous": ["Interferon alfa-2b, recombinant", "Melphalan"],
                                             "current": ["Melphalan", "Interferon alfa-2b", "recombinant"]},
                       "2026-11-08T10:00:00+00:00")
    conn.close()


def test_walk_a_name_holding_a_comma_reads_as_one_entry_apart_from_two_names(make_app, make_walk):
    """test_walk_a_name_holding_a_comma_reads_as_one_entry_apart_from_two_names"""
    app = make_app(seed=seed_comma)
    walk = make_walk(app)
    page = walk.page
    page.goto(f"{app.url}#/trials/NCT10000001")
    card = page.locator("article.change", has_text="Interventions")
    card.wait_for()
    assert _rows(card) == [("Removed", ["Interferon alfa-2b, recombinant"]),
                           ("Added", ["Interferon alfa-2b", "recombinant"]), ("Unchanged", ["1 intervention"])]
    # Each name is visibly its own entry: every list item sits on a line below the one before it.
    for kind in ("removed", "added"):
        items = card.locator(f".split-row.{kind} .split-names li").all()
        boxes = [item.bounding_box() for item in items]
        for above, below in zip(boxes, boxes[1:]):
            assert below["y"] >= above["y"] + above["height"] - 1, f"{kind} names share a line: {boxes}"
    assert page.evaluate("(el) => el.scrollWidth <= el.clientWidth", card.element_handle())
    walk.shot("comma-names")
