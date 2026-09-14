"""How the site gets published: a workflow, and nothing a person has to remember.

The site is only as trustworthy as the thing that assembles it. A workflow that
copied the repository, or that ran on a branch nobody pushes to, would fail in
the two ways that look like success -- publishing too much, or publishing
nothing while reporting nothing wrong. These hold the workflow to the build
script that names what ships, and to the branches this repository is actually
developed on.
"""

from __future__ import annotations

import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"


@pytest.fixture
def workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def triggers(workflow: dict) -> dict:
    """The `on:` block. YAML reads a bare `on` as the boolean True."""
    return workflow.get("on", workflow.get(True))


def steps(workflow: dict) -> list[dict]:
    """Every step of every job, since which job does what is not what is asked here."""
    return [step for job in workflow["jobs"].values() for step in job.get("steps", [])]


def built_into(workflow: dict) -> str:
    """The directory the workflow tells `build_site.py` to write the site into."""
    for step in steps(workflow):
        written = re.search(r"build_site\.py\s+(\S+)", step.get("run", ""))
        if written:
            return written.group(1)
    raise AssertionError("nothing in the workflow runs build_site.py")


def test_the_workflow_watches_both_names_this_repository_goes_by(workflow):
    """The failure this guards against is the silent one.

    The repository records `main` as its default branch and is developed on
    `master`. A workflow watching only one of them does nothing at all on a
    push to the other, which reads exactly like a repository nobody pushed to.
    Watching both costs nothing and makes the mistake impossible.
    """
    on = triggers(workflow)

    assert set(on["push"]["branches"]) >= {"main", "master"}


def test_the_site_can_be_published_without_waiting_for_a_push(workflow):
    """So the first publication, and any re-run, is a button rather than a
    commit invented to trigger one."""
    assert "workflow_dispatch" in triggers(workflow)


def test_the_workflow_builds_the_site_with_the_script_that_names_what_ships(workflow):
    """Not a copied directory. `build_site.py` publishes the modules the page
    names and nothing else, and that is the only way the site is allowed to be
    assembled -- the tests in `test_site.py` are only worth anything if this is
    what runs."""
    assert built_into(workflow)


def test_the_workflow_publishes_only_what_the_build_wrote(workflow):
    """The artifact is the build's output directory, not the checkout."""
    uploads = [
        step for step in steps(workflow)
        if "upload-pages-artifact" in step.get("uses", "")
    ]

    assert uploads, "nothing uploads a Pages artifact"
    assert [step["with"]["path"] for step in uploads] == [built_into(workflow)], (
        "what is published is not what the build wrote, so the site would ship the"
        " checkout or nothing at all"
    )


def test_publishing_asks_for_no_secret_of_its_own(workflow):
    """Criterion: the build depends on no secret, token or account. The only
    credential in play is the one GitHub mints for the run itself, requested as
    a permission rather than stored anywhere."""
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "secrets." not in text
    granted = {
        name: level
        for job in workflow["jobs"].values()
        for name, level in job.get("permissions", {}).items()
    }
    assert granted["id-token"] == "write"
    assert granted["pages"] == "write"


def test_the_human_only_setup_steps_are_written_down():
    """Turning Pages on, and pointing it at the workflow, cannot be done from
    here. A next person who cannot find that out has a repository that looks
    fully wired and publishes nothing."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()

    assert "github pages" in readme
    assert "settings" in readme
