"""What the README has to say, because nothing else can say it.

The app behaves the same whether or not anybody was told where its data lives or
that the old site is gone, so these hold the README to saying so. Each claim is
checked inside the section that owes it, so deleting a sentence fails the test
that asks for it, and a word borrowed from elsewhere in the file does not pass.
"""

from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture
def readme() -> str:
    return (ROOT / "README.md").read_text(encoding="utf-8").lower()


def section(text: str, heading: str) -> str:
    """The body of one `##` section, up to the next heading of that level."""
    found = re.search(
        rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not found:
        raise AssertionError(f"no section headed {heading!r}")
    return found.group(1)


def test_the_readme_says_how_to_start_the_app(readme):
    """test_the_readme_says_how_to_start_the_app: the one command, in its section."""
    assert "python run.py" in section(readme, "trial change monitor")


def test_the_readme_says_where_the_database_file_lives_and_how_to_back_it_up(readme):
    """test_the_readme_says_where_the_database_file_lives_and_how_to_back_it_up: a file, copied."""
    lives = section(readme, "where your data lives")
    assert "monitor.db" in lives
    assert "monitor_db" in lives
    assert "to back it up, copy that file" in lives


def test_the_readme_says_the_app_runs_on_this_machine_only(readme):
    """test_the_readme_says_the_app_runs_on_this_machine_only: nobody else can reach it."""
    lives = section(readme, "where your data lives")
    assert "this machine only" in lives
    assert "127.0.0.1" in lives


def test_the_readme_says_the_old_published_site_is_retired(readme):
    """test_the_readme_says_the_old_published_site_is_retired: no live URL is left behind."""
    lives = section(readme, "where your data lives")
    assert re.search(r"github pages.{0,200}retired", lives, re.DOTALL)
    assert "github.io" not in readme
