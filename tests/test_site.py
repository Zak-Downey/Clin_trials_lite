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
import pathlib

import pytest

import build_site

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
