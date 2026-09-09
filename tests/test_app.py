"""The pages themselves, driven through Streamlit's app-test harness.

The app is two pages, so a test that adds a trial stands on the Search page and
a test that reads one stands on the Watchlist. The database is seeded through
the fetching seam first, so rendering a page never touches the network.
"""

from __future__ import annotations

import copy
import pathlib
import urllib.error

import pytest
from streamlit.testing.v1 import AppTest

import display
import monitor
import storage

APP = str(pathlib.Path(__file__).resolve().parent.parent / "app.py")
WATCHLIST = "views/watchlist.py"


SEARCH = "views/search.py"


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", str(tmp_path / "app.db"))
    return AppTest.from_file(APP, default_timeout=30)


def press(app, label: str):
    """Click a button by the words on it.

    Forms submit buttons take no key, and the Search page now has three
    buttons, so addressing them by position would break the moment one moves.
    """
    for button in app.button:
        if button.label == label:
            return button.click()
    raise AssertionError(f"no button labelled {label!r}")


def add_trial(app, nct_id: str):
    """Add a trial the way the analyst does: from the Search page."""
    app.switch_page(SEARCH).run()
    app.text_input(key="nct_id").set_value(nct_id)
    press(app, "Start monitoring").run()
    return app


def watchlist(app) -> list[dict]:
    """The rendered watchlist table, one dict per line."""
    return app.dataframe[0].value.to_dict("records")


def open_profile(app, index: int = 0):
    """Select a watchlist line so its profile renders below the table.

    The harness clears the table's selection at the start of every run, so the
    selection is set once for the run that opens the profile and again for
    whatever run follows, which is how a control inside the profile stays
    clickable.
    """

    def hold():
        app.session_state["watchlist"] = {"selection": {"rows": [index], "columns": []}}

    hold()
    app.run()
    hold()
    return app


def test_the_page_renders_an_empty_watchlist(app):
    app.run()

    assert not app.exception
    assert "Trial Change Monitor" in app.title[0].value
    assert any("Nothing in this list yet" in info.value for info in app.info)


def test_a_watched_trial_gets_one_line_carrying_what_identifies_the_study(app, fetcher):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)

    app.run()

    assert not app.exception
    lines = watchlist(app)
    assert len(lines) == 1
    assert lines[0]["NCT ID"] == "NCT03412565"
    assert lines[0]["Sponsor"] == "Janssen Research & Development, LLC"
    assert lines[0]["Trial status"] == "Completed"
    assert lines[0]["Official title"]
    assert lines[0]["Phase"] == "Phase 2"
    assert lines[0]["Conditions"]
    assert lines[0]["Interventions"]


def test_a_trial_that_has_never_changed_says_so_on_its_line(app, fetcher):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)

    app.run()

    line = watchlist(app)[0]
    assert line["What changed"] == display.EMPTY
    assert line["Registry updated"] is None
    assert line["Detected"] is None


def test_the_selected_row_shows_every_monitored_field(app, fetcher):
    conn = storage.connect()
    monitor.add(conn, "NCT03412565", fetch=fetcher)
    expected = monitor.profile_of(conn, "NCT03412565")

    app.run()
    open_profile(app)

    rendered = " ".join(m.value for m in app.markdown)
    missing = [k for k in expected if display.label(k) not in rendered]
    assert not missing


def test_an_opened_trial_reads_as_titled_cards(app, fetcher):
    """The dossier: every card the profile fills is on the page, titled."""
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)

    app.run()
    open_profile(app)

    assert not app.exception
    rendered = " ".join(m.value for m in app.markdown)
    for title, _ in display.CARDS:
        assert title.upper() in rendered


def test_each_card_costs_the_page_a_single_block(app, fetcher):
    """The density win. A card drawn field by field would be as tall as the
    stack it replaces, because Streamlit margins every block it draws."""
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)

    app.run()
    open_profile(app)

    titles = [t.upper() for t, _ in display.CARDS]
    cards = [m.value for m in app.markdown if m.value.startswith(tuple(f"**{t}" for t in titles))]
    assert len(cards) == len(titles)
    # Every field of the profile is inside one of those blocks, not beside them.
    fields = monitor.profile_of(storage.connect(), "NCT03412565")
    dossier = " ".join(cards)
    assert not [k for k in fields if display.label(k) not in dossier]


def test_reviewing_clears_the_counts_from_the_card_titles(app, fetcher, monkeypatch):
    """The bell counts what is unread, not what has ever moved."""
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)

    app.run()
    app.button(key="simulate").click().run()
    app.button(key="check_all").click().run()
    open_profile(app)
    assert display.UNREVIEWED in " ".join(m.value for m in app.markdown)

    app.button(key="review_NCT03412565").click().run()
    open_profile(app)

    assert not app.exception
    titles = [m.value for m in app.markdown if m.value.startswith("**")]
    assert titles
    assert not [t for t in titles if display.UNREVIEWED in t]


def test_no_profile_is_shown_until_a_row_is_selected(app, fetcher):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)

    app.run()

    assert "Enrollment" not in " ".join(m.value for m in app.markdown)


def test_the_feed_shows_the_started_monitoring_entry(app, fetcher):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)

    app.run()

    rendered = " ".join(m.value for m in app.markdown)
    assert "started monitoring" in rendered


def test_an_empty_submission_is_reported_inline(app):
    app.run()
    app.switch_page(SEARCH).run()
    press(app, "Start monitoring").run()

    assert not app.exception
    assert any("Paste an NCT ID" in err.value for err in app.error)


def test_checking_a_clean_watchlist_reports_no_changes(app, fetcher, monkeypatch):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)

    app.run()
    app.button(key="check_all").click().run()

    assert not app.exception
    assert any("no changes" in msg.value for msg in app.success)


def test_a_trial_that_fails_to_check_is_reported_inline(app, fetcher, make_fetcher, monkeypatch):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)
    monkeypatch.setattr(
        monitor,
        "_default_fetch",
        make_fetcher(failures={"NCT03412565": urllib.error.URLError("connection refused")}),
    )

    app.run()
    app.button(key="check_all").click().run()

    assert not app.exception
    assert any("connection refused" in err.value for err in app.error)
    assert not app.success


def test_an_empty_watchlist_offers_no_check_control(app):
    app.run()

    assert not app.exception
    assert not [b for b in app.button if b.label == "Check all"]


# --- the developer-only simulator


def test_the_developer_tools_are_labelled_as_synthetic(app, fetcher):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)

    app.run()

    labels = " ".join(exp.label for exp in app.expander).lower()
    assert "developer" in labels
    assert "synthetic" in labels


def test_simulating_a_change_and_checking_shows_it_in_the_feed(app, fetcher, monkeypatch):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)

    app.run()
    app.button(key="simulate").click().run()
    app.button(key="check_all").click().run()

    assert not app.exception
    rendered = " ".join(m.value for m in app.markdown)
    assert "3 fields changed" in rendered


def test_simulated_data_is_badged_wherever_it_appears(app, fetcher, monkeypatch):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)

    app.run()
    app.button(key="simulate").click().run()

    # Badged on the watchlist line while the stored profile is the fabricated one.
    assert display.SYNTHETIC_MARK in watchlist(app)[0]["NCT ID"]

    app.button(key="check_all").click().run()

    # And on the feed entry for the change it caused.
    assert display.SYNTHETIC in " ".join(m.value for m in app.markdown)


def test_deleting_synthetic_data_clears_it_from_the_page(app, fetcher, monkeypatch):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)

    app.run()
    app.button(key="simulate").click().run()
    app.button(key="check_all").click().run()
    app.button(key="delete_synthetic").click().run()

    assert not app.exception
    rendered = " ".join(m.value for m in app.markdown)
    assert "fields changed" not in rendered
    assert display.SYNTHETIC_MARK not in rendered
    # The trial itself is real, and stays.
    assert watchlist(app)[0]["NCT ID"] == "NCT03412565"


def test_simulating_is_offered_only_once_a_trial_is_watched(app):
    app.run()

    assert not app.exception
    assert not [b for b in app.button if b.key == "simulate"]


# --- seeing what moved


def test_a_changed_trial_shows_the_moved_field_highlighted_in_its_profile(
    app, fetcher, monkeypatch
):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)

    app.run()
    app.button(key="simulate").click().run()
    app.button(key="check_all").click().run()
    open_profile(app)

    assert not app.exception
    rendered = " ".join(m.value for m in app.markdown)
    # The whole profile is still there, with the moved fields marked up.
    assert "Official title" in rendered
    assert display.HIGHLIGHT_HIGH_SIGNAL in rendered
    assert "Previously" in rendered


def test_an_unchanged_trial_opens_to_a_plain_profile(app, fetcher):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)

    app.run()
    open_profile(app)

    assert not app.exception
    rendered = " ".join(m.value for m in app.markdown)
    assert "Enrollment" in rendered
    assert display.HIGHLIGHT not in rendered
    assert display.HIGHLIGHT_HIGH_SIGNAL not in rendered


# --- marking a trial reviewed


@pytest.fixture
def live(app, fetcher, monkeypatch):
    """The page with one watched trial, and the check button wired to the stub."""
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)
    app.run()
    return app


def highlighted(app) -> bool:
    rendered = " ".join(m.value for m in app.markdown)
    return display.HIGHLIGHT_HIGH_SIGNAL in rendered or display.HIGHLIGHT in rendered


def test_a_trial_with_no_unreviewed_changes_offers_no_review_control(live):
    open_profile(live)

    assert not [b for b in live.button if b.key == "review_NCT03412565"]


def test_the_whole_loop_from_adding_to_reviewing_and_changing_again_is_walkable(
    app, fetcher, monkeypatch
):
    """Every step taken through the page, as the analyst takes them."""
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)
    app.run()

    add_trial(app, "NCT03412565")
    assert any("Now monitoring NCT03412565" in msg.value for msg in app.success)

    app.switch_page(WATCHLIST).run()
    app.button(key="check_all").click().run()
    assert watchlist(app)[0]["What changed"] == display.EMPTY

    app.button(key="simulate").click().run()
    app.button(key="check_all").click().run()

    # What moved is read off the table itself, before anything is opened.
    line = watchlist(app)[0]
    assert display.UNREVIEWED in line["What changed"]
    assert "Enrollment" in line["What changed"]
    # When the sponsor revised the record, told apart from when we noticed.
    assert line["Registry updated"] is not None
    assert line["Detected"] is not None

    open_profile(app)
    assert highlighted(app)

    app.button(key="review_NCT03412565").click().run()
    open_profile(app)
    assert not highlighted(app)

    # Read, but not forgotten: the names stay on the line, the bell clears.
    line = watchlist(app)[0]
    assert "Enrollment" in line["What changed"]
    assert display.UNREVIEWED not in line["What changed"]

    app.button(key="simulate").click().run()
    app.button(key="check_all").click().run()
    open_profile(app)

    assert not app.exception
    assert highlighted(app)


def test_reviewing_marks_the_feed_entry_as_read_without_removing_it(live):
    live.button(key="simulate").click().run()
    live.button(key="check_all").click().run()
    assert "unreviewed" in " ".join(m.value for m in live.markdown)

    open_profile(live)
    live.button(key="review_NCT03412565").click().run()

    rendered = " ".join(m.value for m in live.markdown)
    assert "3 fields changed" in rendered
    assert "unreviewed" not in rendered


# --- two pages, and one named list at a time


def named(app, name: str) -> int:
    """Create a list from the Watchlist page and return its id."""
    app.switch_page(WATCHLIST).run()
    app.text_input(key="new_list").set_value(name).run()
    app.button(key="create_list").click().run()
    return storage.find_list(storage.connect(), name)["id"]


def showing(app, list_id: int):
    """Stand on the Watchlist page with that list chosen."""
    app.switch_page(WATCHLIST).run()
    app.selectbox(key="chosen_list").set_value(list_id).run()
    return app


def test_the_browser_lands_on_the_watchlist(app):
    app.run()

    assert not app.exception
    # The list picker is the watchlist page; the paste box is the other one.
    assert app.selectbox(key="chosen_list").value == storage.list_lists(storage.connect())[0]["id"]
    assert not [t for t in app.text_input if t.key == "nct_id"]


def test_the_search_page_is_where_a_trial_is_added(app):
    app.run()
    app.switch_page(SEARCH).run()

    assert not app.exception
    assert app.text_input(key="nct_id") is not None
    # And the watchlist no longer carries the paste box.
    app.switch_page(WATCHLIST).run()
    assert not [t for t in app.text_input if t.key == "nct_id"]


def test_a_created_list_can_be_chosen_and_shows_only_its_own_trials(app, fetcher):
    app.run()
    lung = named(app, "Lung")
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)  # the default list

    showing(app, lung)

    assert not app.exception
    assert any("Lung (0)" in sub.value for sub in app.subheader)
    assert not app.dataframe


def test_two_lists_cannot_share_a_name_on_the_page(app):
    app.run()
    named(app, "Lung")

    app.text_input(key="new_list").set_value("Lung").run()
    app.button(key="create_list").click().run()

    assert any("already a list" in err.value for err in app.error)


def test_renaming_a_list_keeps_what_it_holds(app, fetcher):
    app.run()
    lung = named(app, "Lung")
    monitor.add(storage.connect(), "NCT03412565", lung, fetch=fetcher)
    showing(app, lung)

    app.text_input(key=f"rename_{lung}").set_value("Lung — AZ").run()
    app.button(key="rename_list").click().run()

    assert not app.exception
    assert any("Lung — AZ (1)" in sub.value for sub in app.subheader)


def test_a_trial_in_two_lists_is_readable_from_both_and_leaves_one_when_removed(app, fetcher):
    conn = storage.connect()
    app.run()
    lung = named(app, "Lung")
    myeloma = named(app, "Myeloma")
    monitor.add(conn, "NCT03412565", lung, fetch=fetcher)
    monitor.add(conn, "NCT03412565", myeloma, fetch=fetcher)

    for chosen in (lung, myeloma):
        showing(app, chosen)
        assert watchlist(app)[0]["NCT ID"] == "NCT03412565"

    showing(app, myeloma)
    open_profile(app)
    app.button(key="remove_NCT03412565").click().run()

    assert not app.exception
    assert not app.dataframe
    showing(app, lung)
    assert watchlist(app)[0]["NCT ID"] == "NCT03412565"
    assert storage.get_trial(conn, "NCT03412565") is not None


def test_a_trial_removed_from_its_only_list_stops_being_monitored(app, fetcher):
    conn = storage.connect()
    app.run()
    lung = named(app, "Lung")
    monitor.add(conn, "NCT03412565", lung, fetch=fetcher)
    showing(app, lung)

    open_profile(app)
    app.button(key="remove_NCT03412565").click().run()

    assert not app.exception
    assert storage.get_trial(conn, "NCT03412565") is None


def test_adding_from_the_search_page_lands_in_the_chosen_list(app, fetcher, monkeypatch):
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)
    app.run()
    lung = named(app, "Lung")

    app.switch_page(SEARCH).run()
    app.selectbox(key="destination_list").set_value(lung).run()
    app.text_input(key="nct_id").set_value("NCT03412565")
    press(app, "Start monitoring").run()

    assert not app.exception
    assert any("Lung" in msg.value for msg in app.success)
    showing(app, lung)
    assert watchlist(app)[0]["NCT ID"] == "NCT03412565"


def test_the_search_page_can_name_a_new_list_as_it_adds(app, fetcher, monkeypatch):
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)
    app.run()
    app.switch_page(SEARCH).run()

    app.selectbox(key="destination_list").set_value("+ New list…").run()
    app.text_input(key="destination_list_name").set_value("Myeloma").run()
    app.text_input(key="nct_id").set_value("NCT03412565")
    press(app, "Start monitoring").run()

    assert not app.exception
    conn = storage.connect()
    created = storage.find_list(conn, "Myeloma")
    assert created is not None
    assert [t["nct_id"] for t in storage.list_trials(conn, created["id"])] == ["NCT03412565"]


def test_a_database_predating_lists_keeps_working(app, fetcher, tmp_path, monkeypatch):
    """Nobody re-adds a trial: what was already monitored opens in one list."""
    conn = storage.connect()
    monitor.add(conn, "NCT03412565", fetch=fetcher)
    conn.execute("DELETE FROM list_members")
    conn.execute("DELETE FROM lists")
    conn.commit()

    app.run()

    assert not app.exception
    assert watchlist(app)[0]["NCT ID"] == "NCT03412565"


def test_the_whole_loop_through_a_named_list_is_walkable(app, fetcher, monkeypatch):
    """Create a list, fill it from the Search page, then read it."""
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)
    app.run()

    myeloma = named(app, "Myeloma")

    app.switch_page(SEARCH).run()
    app.selectbox(key="destination_list").set_value(myeloma).run()
    app.text_input(key="nct_id").set_value("NCT03412565")
    press(app, "Start monitoring").run()

    showing(app, myeloma)
    app.button(key="check_all").click().run()
    assert watchlist(app)[0]["What changed"] == display.EMPTY

    app.button(key="simulate").click().run()
    app.button(key="check_all").click().run()

    line = watchlist(app)[0]
    assert display.UNREVIEWED in line["What changed"]

    open_profile(app)
    assert highlighted(app)

    app.button(key="review_NCT03412565").click().run()
    open_profile(app)

    assert not app.exception
    assert not highlighted(app)
    assert "Enrollment" in watchlist(app)[0]["What changed"]
    assert display.UNREVIEWED not in watchlist(app)[0]["What changed"]


def test_deleting_the_last_list_leaves_a_stand_in_rather_than_an_empty_page(app, fetcher):
    """The page always shows a list, so there always has to be one to show."""
    conn = storage.connect()
    app.run()
    only = storage.list_lists(conn)[0]["id"]
    monitor.add(conn, "NCT03412565", only, fetch=fetcher)

    app.button(key="delete_list").click().run()

    assert not app.exception
    assert len(storage.list_lists(conn)) == 1
    # The trial went with the list, because nothing else was holding it.
    assert storage.get_trial(conn, "NCT03412565") is None
    assert any("Nothing in this list yet" in info.value for info in app.info)


# --- searching the registry and filling a list
#
# The registry search is stubbed at monitor's own seam, so the page is driven
# for real without a request leaving the machine.


def stub_search(monkeypatch, studies=None, failure=None):
    """Make the page's registry search return these studies, or fail."""

    def find(**params):
        if failure is not None:
            raise failure
        return list(studies or [])

    monkeypatch.setattr(monitor, "_default_find", find)


def other_study(record: dict, nct_id: str) -> dict:
    """The captured record, standing in for a second study in a result set."""
    copied = copy.deepcopy(record)
    copied["protocolSection"]["identificationModule"]["nctId"] = nct_id
    return copied


def run_search(app, condition: str = "multiple myeloma"):
    app.switch_page(SEARCH).run()
    app.text_input(key="cond").set_value(condition)
    press(app, "Search").run()
    return app


def tick(app, rows: list[int]):
    """Tick result rows, the way the harness expresses a table selection.

    Held across two runs for the same reason opening a profile is: the harness
    clears a table's selection at the start of every run, so the control that
    depends on it only stays live if the selection is set again afterwards.
    """

    def hold():
        app.session_state["results"] = {"selection": {"rows": rows, "columns": []}}

    hold()
    app.run()
    hold()
    return app


def test_the_search_page_offers_the_four_axes(app):
    app.switch_page(SEARCH).run()

    keys = {widget.key for widget in app.text_input}
    assert {"cond", "intr", "spons"} <= keys
    assert app.multiselect(key="phases") is not None


def test_a_search_with_every_field_blank_is_refused_on_the_page(app, monkeypatch):
    stub_search(monkeypatch, [])
    app.switch_page(SEARCH).run()

    press(app, "Search").run()

    assert not app.exception
    assert any("at least one" in err.value for err in app.error)


def test_results_arrive_as_a_table_of_the_watchlist_columns(app, record, monkeypatch):
    stub_search(monkeypatch, [record])

    run_search(app)

    assert not app.exception
    shown = app.dataframe[0].value.to_dict("records")[0]
    assert shown["NCT ID"] == "NCT03412565"
    assert set(shown) == {
        "NCT ID",
        "Sponsor",
        "Official title",
        "Phase",
        "Conditions",
        "Interventions",
        "Trial status",
    }


def test_a_search_matching_nothing_says_so(app, monkeypatch):
    stub_search(monkeypatch, [])

    run_search(app, "something nobody studies")

    assert not app.exception
    assert any("Nothing matched" in warn.value for warn in app.warning)


def test_an_unreachable_registry_reports_the_failure(app, monkeypatch):
    stub_search(monkeypatch, failure=urllib.error.URLError("down"))

    run_search(app)

    assert not app.exception
    assert any("Could not reach" in err.value for err in app.error)
    assert not app.dataframe


def test_a_capped_result_set_says_it_is_capped(app, record, monkeypatch):
    studies = [other_study(record, f"NCT1000{i:04d}") for i in range(monitor.RESULT_CAP + 1)]
    stub_search(monkeypatch, studies)

    run_search(app)

    assert not app.exception
    assert any("first" in cap.value and "of more" in cap.value for cap in app.caption)


def test_selected_results_are_added_to_the_list_chosen_afterwards(
    app, record, fetcher, monkeypatch
):
    stub_search(monkeypatch, [record, other_study(record, "NCT00000001")])
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)
    app.run()
    lung = named(app, "Lung")

    run_search(app)
    app.selectbox(key="results_list").set_value(lung).run()
    tick(app, [0, 1])
    press(app, "Add selected").run()

    assert not app.exception
    held = {t["nct_id"] for t in storage.list_trials(storage.connect(), lung)}
    assert held == {"NCT03412565", "NCT00000001"}


def test_a_result_already_in_the_chosen_list_is_shown_as_already_there(
    app, record, fetcher, monkeypatch
):
    stub_search(monkeypatch, [record])
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)
    app.run()
    conn = storage.connect()
    only = storage.list_lists(conn)[0]["id"]
    monitor.add(conn, "NCT03412565", only, fetch=fetcher)

    run_search(app)
    tick(app, [0])
    press(app, "Add selected").run()

    assert not app.exception
    assert any("already" in warn.value for warn in app.warning)
    assert len(storage.list_trials(conn, only)) == 1


def test_the_whole_search_loop_into_a_new_named_list_is_walkable(
    app, record, fetcher, monkeypatch
):
    """Search, select several, file into a list named on the spot, then read it."""
    stub_search(monkeypatch, [record, other_study(record, "NCT00000001")])
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)
    app.run()

    run_search(app)
    app.selectbox(key="results_list").set_value("+ New list…").run()
    app.text_input(key="results_list_name").set_value("Myeloma — Janssen").run()
    tick(app, [0, 1])
    press(app, "Add selected").run()

    assert not app.exception
    made = storage.find_list(storage.connect(), "Myeloma — Janssen")
    assert made is not None

    showing(app, made["id"])
    assert len(watchlist(app)) == 2

    app.button(key="check_all").click().run()
    assert not app.exception
    assert watchlist(app)[0]["What changed"] == display.EMPTY

    app.button(key="simulate").click().run()
    app.button(key="check_all").click().run()

    assert display.UNREVIEWED in watchlist(app)[0]["What changed"]


def test_a_narrower_second_search_does_not_carry_the_old_selection(
    app, record, fetcher, monkeypatch
):
    """Row numbers mean a different study once the results behind them change.

    The selection is held across the search the way a browser holds it -- the
    client sends it back with every rerun -- because that is the only way the
    stale row number reaches the code that reads it.
    """
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)
    stub_search(
        monkeypatch,
        [record, other_study(record, "NCT00000001"), other_study(record, "NCT00000002")],
    )
    run_search(app)
    tick(app, [2])

    stub_search(monkeypatch, [other_study(record, "NCT00000009")])
    app.text_input(key="cond").set_value("something narrower")
    app.session_state["results"] = {"selection": {"rows": [2], "columns": []}}
    press(app, "Search").run()

    assert not app.exception
    assert any("0 selected" in cap.value for cap in app.caption)


def test_pasting_a_trial_the_list_already_holds_names_the_list(app, fetcher, monkeypatch):
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)
    conn = storage.connect()
    app.run()
    only = storage.list_lists(conn)[0]["id"]
    monitor.add(conn, "NCT03412565", only, fetch=fetcher)

    add_trial(app, "NCT03412565")

    assert not app.exception
    said = " ".join(msg.value for msg in app.warning)
    assert "NCT03412565 was already in" in said
    assert storage.get_list(conn, only)["name"] in said
