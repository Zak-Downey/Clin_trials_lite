"""The pull-request workflow, read as text: GitHub cannot be run from here.

Nothing here claims the workflow works on GitHub. It holds what the file says: one job named `checks`,
when it runs, that nothing lets it be skipped, and that it runs every check.
"""

from __future__ import annotations

import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "checks.yml"


def text():
    return WORKFLOW.read_text()


def block(name, indent=0):
    """The lines under the key `name` at the given indent, up to the next key at that indent or less."""
    lines = text().splitlines()
    start = next(i for i, line in enumerate(lines) if line == " " * indent + f"{name}:")
    out = []
    for line in lines[start + 1:]:
        if line.strip() and not line.lstrip().startswith("#") and len(line) - len(line.lstrip()) <= indent:
            break
        out.append(line)
    return "\n".join(out)


def test_the_workflow_has_one_job_and_it_is_named_checks():
    jobs = block("jobs")
    job_keys = re.findall(r"^  ([\w-]+):\s*$", jobs, re.M)
    assert job_keys == ["checks"]
    assert re.search(r"^    name: checks\s*$", jobs, re.M)


def test_it_runs_on_a_pull_request_opened_pushed_to_reopened_or_marked_ready_and_by_hand_never_on_a_push():
    triggers = block("on")
    assert re.findall(r"^  ([\w-]+):", triggers, re.M) == ["pull_request", "workflow_dispatch"]
    types = re.search(r"types:\s*\[([^\]]*)\]", triggers).group(1)
    assert sorted(t.strip() for t in types.split(",")) == ["opened", "ready_for_review", "reopened", "synchronize"]
    assert not re.search(r"^\s*push\s*:", text(), re.M)


def test_nothing_filters_by_path_and_nothing_skips_a_draft():
    assert not re.search(r"^\s*(paths|paths-ignore|branches-ignore)\s*:", text(), re.M)
    assert "draft" not in "\n".join(line for line in text().splitlines() if not line.lstrip().startswith("#"))
    assert not re.search(r"^    if\s*:", block("jobs"), re.M)


def test_every_check_is_run_with_no_check_named():
    runs = re.findall(r"^\s*(?:- )?run:\s*(.*\S)\s*$", block("jobs"), re.M)
    assert "python3 checks.py" in runs
    assert not any(re.search(r"checks\.py\s+\S", r) for r in runs)


def test_a_newer_run_on_the_same_branch_cancels_the_older_one():
    concurrency = block("concurrency")
    assert re.search(r"^  group: .*github\.workflow.*github\.ref", concurrency, re.M)
    assert re.search(r"^  cancel-in-progress: true\s*$", concurrency, re.M)


JUDGING = [".github/workflows/", "checks.py", ".claude/settings.json", "pytest.ini", "ruff.toml"]


def notice_step():
    """The step that runs the notice: the one whose run line calls judge_notice.py."""
    steps = re.split(r"^      - ", block("jobs"), flags=re.M)
    return next((s for s in steps if "judge_notice.py" in s), "")


def notice_paths():
    """The judging paths the notice step passes after the base."""
    run = re.search(r"run:\s*(.*\S)", notice_step())
    assert run, "no step runs judge_notice.py"
    return run.group(1).split()[3:]


def test_a_step_names_the_five_files_that_judge_a_pull_request_and_no_other():
    assert sorted(notice_paths()) == sorted(JUDGING)


def test_the_comment_at_the_top_names_the_same_judging_files_as_the_notice_step():
    header = "\n".join(line for line in text().splitlines() if line.startswith("#"))
    listed = re.search(r"\(this folder, ([^)]*)\)", header.replace("\n#  ", " "))
    assert listed, "the comment does not list the judging files"
    assert sorted([".github/workflows/", *(p.strip() for p in listed.group(1).split(","))]) == sorted(notice_paths())


def test_repo_md_names_the_same_judging_files_as_the_notice_step():
    workflows = next(line for line in REPO_MD.read_text().splitlines() if line.startswith("- **Workflows.**"))
    listed = re.search(r"that judge it \(([^)]*)\)", workflows)
    assert listed, "the Workflows line does not list the judging files"
    assert sorted(re.findall(r"`([^`]+)`", listed.group(1))) == sorted(notice_paths())


def test_the_notice_step_can_never_fail_the_run():
    assert re.search(r"^        continue-on-error: true\s*$", notice_step(), re.M)


REPO_MD = WORKFLOW.parent.parent.parent / "docs" / "agents" / "local" / "repo.md"


def test_repo_md_names_every_workflow_file_that_exists_and_no_other():
    ci = REPO_MD.read_text().split("## CI", 1)[1]
    named = set(re.findall(r"`\.github/workflows/([\w.-]+\.ya?ml)`", ci))
    present = {p.name for p in WORKFLOW.parent.iterdir() if p.suffix in (".yml", ".yaml")}
    assert present, "no workflow file"
    assert named == present


def test_repo_md_describes_the_quick_run_checks_py_has_and_github_never_uses():
    every_check = next(line for line in REPO_MD.read_text().splitlines() if line.startswith("- **Every check.**"))
    assert "`python3 checks.py --quick`" in every_check
    assert '"--quick"' in (WORKFLOW.parent.parent.parent / "checks.py").read_text()
    assert "--quick" not in text()


def test_repo_md_describes_the_picked_run_checks_py_has_and_github_never_uses():
    picked = next(line for line in REPO_MD.read_text().splitlines() if line.startswith("- **Picked run.**"))
    assert "`python3 checks.py --pick`" in picked and "never a full run" in picked
    assert '"--pick"' in (WORKFLOW.parent.parent.parent / "checks.py").read_text()
    assert "--pick" not in text()
