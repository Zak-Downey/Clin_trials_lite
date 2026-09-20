"""What the app is published as: one static page and a named list of modules.

The page is going to a public URL, and the repository it is assembled from
holds a working database of somebody's monitoring, the internal specs and
issues, the test suite, and a simulator that fabricates trial movements. So
what ships is listed a file at a time rather than swept up from a directory,
and these tests are what hold that list to the app it has to carry -- complete
enough to run, and nothing beyond it.
"""

from __future__ import annotations

import ast
import importlib
import os
import pathlib
import re
from unittest import mock

import pytest

import build_site
import storage

ROOT = pathlib.Path(__file__).resolve().parent.parent


def named_by(source: str):
    """Every module this file names, as an import or as a path it hands Streamlit.

    Both spellings count: `app.py` reaches its two pages by naming their files
    to `st.Page`, and a page missing from the site is as broken as a missing
    import.
    """
    for node in ast.walk(ast.parse((ROOT / source).read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            yield from (alias.name.replace(".", "/") + ".py" for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            yield node.module.replace(".", "/") + ".py"
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.value


def reachable(entrypoint: str) -> set[str]:
    """Every module in this repository the entrypoint reaches, directly or not.

    Worked out from the app itself rather than from the published list, so the
    two can disagree -- which is the whole point of asking.
    """
    found: set[str] = set()
    queue = [entrypoint]
    while queue:
        source = queue.pop()
        if source in found:
            continue
        found.add(source)
        for name in named_by(source):
            candidate = pathlib.Path(name)
            if name.endswith(".py") and (ROOT / candidate).is_file():
                queue.append(candidate.as_posix())
    return found


def test_the_published_list_carries_every_module_the_app_reaches():
    missing = reachable("app.py") - set(build_site.published())

    assert not missing, f"the app imports these but the site would not carry them: {sorted(missing)}"


def test_the_published_list_carries_nothing_the_app_does_not_reach():
    """The list is what ships, so anything on it that the app never imports is
    something published for no reason -- the direction of mistake that matters
    here, because the site is public."""
    extra = set(build_site.published()) - reachable("app.py")

    assert not extra, f"the site would carry these, but the app never imports them: {sorted(extra)}"


def test_the_working_database_and_the_developer_tools_stay_behind():
    """Named one by one, because a regression here is not recoverable.

    These are the files that would be embarrassing rather than merely wrong:
    somebody's monitoring history, the tools for fabricating trial movements,
    and the notes written on the assumption nobody outside would read them.
    """
    listed = set(build_site.published())

    assert "simulate.py" not in listed
    assert "explore.py" not in listed
    assert not [source for source in listed if source.endswith(".db")]
    assert not [source for source in listed if source.startswith(("tests/", ".scratch/", "docs/"))]


def test_building_the_site_writes_the_page_and_its_modules_and_nothing_else(tmp_path):
    dest = tmp_path / "site"

    build_site.build(dest)

    written = sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file())
    assert written == sorted(["index.html", *build_site.published()])


def test_the_built_modules_are_the_ones_in_the_repository(tmp_path):
    """The published app is the committed code, not a copy that drifted from it."""
    dest = tmp_path / "site"

    build_site.build(dest)

    for source in build_site.published():
        assert (dest / source).read_bytes() == (ROOT / source).read_bytes()


# --- where the watchlist is kept
#
# In the browser the app's filesystem is memory, and memory is gone on reload.
# A monitor that forgets every trial on a stray refresh destroys the analyst's
# work without ever admitting it, so the database is put in a directory backed
# by the browser's own persistent store. The failure mode is the quiet kind --
# everything looks right for a whole session and is gone the next morning --
# which is why the wiring is asserted here rather than left to be noticed.
#
# Read from the page here rather than through build_site, which reads the same
# file: what the build needs to know is which modules travel, and where the
# database goes is no business of its. What these do borrow is its habit of
# raising when the page does not say, because a page that stopped saying is the
# thing being tested for and an empty answer would read as a passing one.

PERSISTENT = re.compile(r"idbfsMountpoints:\s*\[(.*?)\]", re.DOTALL)
DATABASE = re.compile(r'MONITOR_DB:\s*"([^"]+)"')

PAGE = ROOT / "web" / "index.html"


def _said(pattern: re.Pattern, what: str) -> str:
    """What the page says, by one of the patterns above."""
    said = pattern.search(PAGE.read_text(encoding="utf-8"))
    if not said:
        raise AssertionError(f"{PAGE} does not say {what}")
    return said.group(1)


def _said_all(pattern: re.Pattern, what: str) -> list[str]:
    """Every time the page says it, for the things it is expected to say twice."""
    said = pattern.findall(PAGE.read_text(encoding="utf-8"))
    if not said:
        raise AssertionError(f"{PAGE} does not say {what}")
    return said


def persistent_directories() -> list[str]:
    """The directories the page asks the browser to keep across a reload."""
    return build_site.QUOTED.findall(
        _said(PERSISTENT, "which directories the browser should keep, so nothing"
              " written in it would survive a reload")
    )


def database_path() -> str:
    """Where the page tells the app to keep its database."""
    return _said(DATABASE, "where the database goes")


@pytest.fixture
def opened_with():
    """Where storage would open its database, for a given `MONITOR_DB`, or none.

    It reads the location once, when it is imported, so the only way to ask is
    to import it again -- and the only way to leave the rest of the suite alone
    is to import it back afterwards.
    """

    def read(path: str | None) -> str:
        with mock.patch.dict(os.environ):
            # Only this one variable, so nothing else the environment carries
            # is part of what is being asked.
            os.environ.pop("MONITOR_DB", None)
            if path is not None:
                os.environ["MONITOR_DB"] = path
            return importlib.reload(storage).DB_PATH

    yield read
    importlib.reload(storage)


def test_the_page_asks_the_browser_to_keep_a_directory():
    assert persistent_directories()


def test_the_database_is_kept_inside_a_persistent_directory():
    """The one that matters. A database a hair outside the mounted directory is
    a working app for exactly as long as the tab stays open."""
    kept = database_path()

    assert any(
        kept.startswith(f"{directory.rstrip('/')}/") for directory in persistent_directories()
    ), f"{kept} is not inside any of {persistent_directories()}, so it will not survive a reload"


def test_the_page_names_the_database_by_the_variable_storage_reads(opened_with):
    """The page and the storage layer meet at one environment variable, and this
    is what holds them to the same one: the path the page names is the path the
    app opens.

    What it cannot hold is the browser to the page. That the runtime honours
    either setting was established by driving the built site, and a version of
    stlite that quietly stopped would pass every test here.
    """
    kept = database_path()

    assert opened_with(kept) == kept


def test_the_app_still_opens_its_ordinary_database_file_locally(opened_with):
    """Run under Streamlit with nothing set, the app is where it always was."""
    assert opened_with(None) == "monitor.db"


# --- which Streamlit a visitor gets
#
# Two URLs load stlite -- a stylesheet and a module -- and the version in them
# decides which Streamlit the app runs on. It is pinned rather than left to a
# range so that an upgrade is a deliberate act: a range would let a visitor's
# refresh move the runtime under them.
#
# Half an upgrade is the quiet failure. The stylesheet of one stlite over the
# JavaScript of another loads and mostly works, and what it breaks it breaks in
# the browser, where nothing here is watching.

# Deliberately matches any version, pin or range: what the page loads is one
# question and whether it pinned it is the next one.
STLITE = re.compile(r"@stlite/browser@([^/\"]+)/")

# A pin, as opposed to a range or a tag. `^1.9` and `latest` both resolve to
# whatever is newest at the moment of the request.
EXACT = re.compile(r"\d+\.\d+\.\d+")


def stlite_versions() -> list[str]:
    """Every stlite version the page loads, in the order it names them."""
    return _said_all(STLITE, "where it loads stlite from")


def test_the_page_loads_one_stlite_and_pins_it():
    versions = stlite_versions()

    assert len(versions) == 2, (
        f"the page loads stlite from {len(versions)} place(s), not the stylesheet"
        " and the module it needs"
    )
    assert len(set(versions)) == 1, (
        f"the page's two halves of stlite are different releases: {versions}"
    )
    assert EXACT.fullmatch(versions[0]), (
        f"{versions[0]!r} is a range or a tag, not a pin, so a refresh can change"
        " the runtime under a visitor"
    )
