"""walker-trial-page-01: an intervention name holding a comma is indistinguishable from two names.

Red while the Removed and Added lines join names with ", " so that the record
splitting "Interferon alfa-2b, recombinant" into "Interferon alfa-2b" and
"recombinant" reads as the same text removed and added. Green once each name
on a line can be told apart from its neighbours.
"""

from __future__ import annotations

from walks.test_trial_page_walk import seed_trial_page


def seed(db, registry):
    import storage

    seed_trial_page(db, registry)
    conn = storage.connect(db)
    storage.add_change(conn, "NCT10000001", {"field": "interventions",
                                             "previous": ["Interferon alfa-2b, recombinant", "Melphalan"],
                                             "current": ["Melphalan", "Interferon alfa-2b", "recombinant"]},
                       "2026-11-08T10:00:00+00:00")
    conn.close()


def test_a_name_with_a_comma_reads_apart_from_two_names(make_app, make_walk):
    app = make_app(seed=seed)
    walk = make_walk(app)
    page = walk.page
    page.goto(f"{app.url}#/trials/NCT10000001")
    card = page.locator("article.change", has_text="Interventions")
    card.wait_for()
    removed = card.locator(".split-row.removed .split-names").inner_text().strip()
    added = card.locator(".split-row.added .split-names").inner_text().strip()
    walk.shot("comma-names")
    assert removed != added, f"Removed and Added both read {removed!r}"
