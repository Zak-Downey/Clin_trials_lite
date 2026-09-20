"""What the documentation has to say, because nothing else can say it.

An analyst's watchlists live in their own browser and nowhere else. That is a
deliberate consequence of having no login, and it is invisible from inside the
app: a watchlist that survived yesterday's refresh looks exactly like a
watchlist that is backed up somewhere. The difference only shows up on the day
somebody clears their site data, opens the app on a second machine, or asks a
colleague to look at their list -- by which point months of monitoring are
gone, or the morning is.

So the promise the app does *not* make has to be written down, and these hold
the two places a person looks -- the README they read to run it, and the
decision record they read to understand it -- to actually saying it. A
documentation fact is not covered by any other test in this suite: the app
behaves identically whether or not anybody was ever warned.

Each claim is checked inside the section that is supposed to make it, rather
than anywhere in the file. That is the difference between a test that fails
when a warning is deleted and one that passes on a word borrowed from an
unrelated sentence elsewhere in the document -- "sync" appears in this ADR's
account of how stlite writes to IndexedDB, and `http.server` appeared in the
README long before anything explained why serving it matters.
"""

from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
ADRS = ROOT / "docs" / "adr"

# The decision this feature turned on, recorded alongside the one already here.
DECISION = ADRS / "0002-the-app-is-published-as-webassembly-with-browser-local-storage.md"
FIRST_DECISION = ADRS / "0001-sponsor-type-matches-the-lead-sponsor-only.md"


@pytest.fixture
def readme() -> str:
    return (ROOT / "README.md").read_text(encoding="utf-8").lower()


@pytest.fixture
def adr() -> str:
    if not DECISION.exists():
        raise AssertionError(
            f"{DECISION.relative_to(ROOT)} does not exist: the trade-off behind"
            " browser-local storage is recorded nowhere a future reader will look"
        )
    return DECISION.read_text(encoding="utf-8").lower()


def section(text: str, heading: str) -> str:
    """The body of one `##` section, up to the next heading of that level.

    Claims are asserted against the section that owes them, so that removing
    the sentence that makes a point fails the test that asks for it.
    """
    found = re.search(
        rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not found:
        raise AssertionError(f"no section headed {heading!r}")
    return found.group(1)


def headings(text: str) -> list[str]:
    """The `##` headings of a markdown document, in order, lowercased."""
    return [line.strip().lower() for line in text.splitlines() if line.startswith("## ")]


def says(text: str, *alternatives: str) -> bool:
    """Whether the text makes a point, in any of the wordings given.

    Alternatives are for genuinely interchangeable phrasings of one claim. They
    are not slack: every alternative is a way of saying the same thing, so a
    passing test still means the point is made somewhere in the section asked.
    """
    return any(re.search(phrasing, text) for phrasing in alternatives)


def test_the_readme_says_where_the_app_is_published(readme):
    """The live URL itself, not a template to fill in.

    A reader who has to work out their own `<owner>` and `<repo>` cannot check
    whether what they are reading describes the site that is actually up.
    """
    published = section(readme, "published to github pages")

    assert "zak-downey.github.io/clin_trials_lite" in published


def test_the_readme_says_the_page_has_to_be_served(readme):
    """The mistake that looks like a broken app rather than a wrong step.

    A `file://` page is not allowed to load the code the app is made of, so
    double-clicking `index.html` gets a starting-up message, then a blank page,
    and no error anybody can act on. Anybody who tries the obvious thing first
    needs telling.
    """
    browser = section(readme, "in a browser, with no python installed")

    assert says(browser, r"file://", r"as a file", r"double-click"), (
        "the README does not name opening the page as a file as the thing that fails"
    )
    assert says(browser, r"\bserved\b", r"\bserve it\b", r"must be served"), (
        "the README does not say the page has to be served; `http.server` appearing in"
        " a command is not the same as explaining why it is there"
    )


def test_the_readme_says_watchlists_live_in_that_browser_alone(readme):
    """Stated plainly, in the README, rather than left to be inferred.

    Three separate surprises, each of which costs somebody real work: there is
    no copy anywhere else, the list does not follow them to another machine,
    and nobody is keeping it safe for them.
    """
    lives = section(readme, "where your watchlists live")

    assert says(lives, r"browser alone", r"only in .{0,30}browser", r"nowhere else"), (
        "the README does not say watchlists are stored in the visitor's browser alone"
    )
    assert says(lives, r"not backed up", r"no backup", r"nobody (is holding|backs)"), (
        "the README does not say watchlists are not backed up"
    )
    assert says(lives, r"do not follow", r"does not follow", r"no sync", r"not .{0,20}sync"), (
        "the README does not say watchlists do not follow the analyst to another machine"
    )


def test_the_readme_says_clearing_site_data_destroys_them(readme):
    """The specific, ordinary action that throws the work away.

    "Stored locally" does not tell anybody that the browser's own Clear
    browsing data button is a delete button for their monitoring.
    """
    lives = section(readme, "where your watchlists live")

    assert says(lives, r"clear(ing|s|ed)? .{0,40}(site|browsing) data")
    assert says(lives, r"destroy", r"lost", r"loses", r"gone", r"delete")


def test_an_adr_records_why_the_app_is_published_this_way(adr):
    """Not that it is WebAssembly, which the code shows, but why.

    A future reader looking at an app with no accounts needs to find a decision
    rather than an omission, so the record has to carry both halves: what was
    decided, and the requirement it followed from.
    """
    decided = section(adr, "the decision")
    why = section(adr, "why")

    assert says(decided, r"webassembly", r"wasm")
    assert says(decided, r"browser"), "the decision does not say where the data ends up"
    assert says(why, r"no login", r"without (a )?login", r"no account"), (
        "the ADR does not give the requirement the decision followed from"
    )


def test_the_adr_states_the_trade_off_it_accepts(adr):
    """The whole reason the record earns its place.

    Somebody who later wants two analysts on one list is not fixing a bug, and
    the record is what tells them that. It can only do that if it names what
    was given up -- as a cost, not in passing: this ADR also explains that
    stlite *syncs* a directory to IndexedDB, which is a sentence about how the
    saving works and says nothing about what the analyst does not get.
    """
    why = section(adr, "why")

    for given_up in ["no sync", "no backup", "no sharing"]:
        assert given_up in why, (
            f'the ADR does not name "{given_up}" as part of what no login costs, so a'
            " reader cannot tell a deliberate trade-off from an oversight"
        )


def test_the_adr_carries_every_section_the_one_already_here_does(adr):
    """One shape for decisions, so the second is read the way the first is."""
    first = FIRST_DECISION.read_text(encoding="utf-8")
    missing = sorted(set(headings(first)) - set(headings(adr)))

    assert not missing, f"the new ADR is missing sections the existing one has: {missing}"
    assert says(adr, r"\*\*status:\*\*"), "the ADR does not carry a status line"
