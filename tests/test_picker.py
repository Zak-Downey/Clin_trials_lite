"""What a change can reach: the walk files a set of changed files picks on a hand-made map (a table, one row per rule),
and the base those changed files are measured from, on small git repos made in a temporary folder with hand-made run logs.
"""

from __future__ import annotations

import json
import subprocess

import pytest

import picker

MAP = {
    "shared": ["app/shell.js"],
    "always": ["walks/test_guards.py"],
    "areas": [
        {"name": "Page A", "files": ["app/page_a.js"], "walks": ["walks/test_page_a.py"]},
        {"name": "Page B", "files": ["app/page_b*.js"], "walks": ["walks/test_page_b.py", "walks/test_both.py"]},
        {"name": "Page C", "files": ["app/page_c.js"], "walks": ["walks/test_page_c.py", "walks/test_both.py"]},
    ],
    "none": ["*.md", "tests/*"],
}
EVERY = ["walks/test_both.py", "walks/test_guards.py", "walks/test_page_a.py", "walks/test_page_b.py", "walks/test_page_c.py"]

ROWS = [
    ("a file of one area", ["app/page_a.js"],
     ["walks/test_guards.py", "walks/test_page_a.py"],
     ["Page A", "`app/page_a.js`"]),
    ("files of two areas", ["app/page_a.js", "app/page_b2.js"],
     ["walks/test_both.py", "walks/test_guards.py", "walks/test_page_a.py", "walks/test_page_b.py"],
     ["Page A", "`app/page_a.js`", "Page B", "`app/page_b2.js`"]),
    ("a deleted file of an area: it is in the changed files, and EVERY no longer matters to it", ["app/page_c.js"],
     ["walks/test_both.py", "walks/test_guards.py", "walks/test_page_c.py"], ["Page C", "`app/page_c.js`"]),
    ("a renamed file, counted under both names", ["app/page_a.js", "app/page_b.js"],
     ["walks/test_both.py", "walks/test_guards.py", "walks/test_page_a.py", "walks/test_page_b.py"],
     ["Page A", "`app/page_a.js`", "Page B", "`app/page_b.js`"]),
    ("a changed walk file runs itself", ["walks/test_page_c.py"],
     ["walks/test_guards.py", "walks/test_page_c.py"], ["`walks/test_page_c.py`"]),
    ("a deleted walk file is not run", ["walks/test_page_d.py", "README.md"],
     ["walks/test_guards.py"], ["only the walks that always run"]),
    ("only docs changed", ["README.md", "tests/test_x.py"],
     ["walks/test_guards.py"], ["only the walks that always run", "`README.md`", "reach no walk"]),
    ("nothing changed", [], ["walks/test_guards.py"], ["only the walks that always run", "nothing changed"]),
    ("a shared file", ["app/page_a.js", "app/shell.js"], EVERY, ["every walk", "`app/shell.js`", "shared"]),
    ("a file placed nowhere", ["lib/util.py"], EVERY, ["every walk", "`lib/util.py`", "nowhere"]),
    ("a new file the map does not place yet", ["app/page_d.js"], EVERY, ["every walk", "`app/page_d.js`", "nowhere"]),
    ("cannot tell what changed", None, EVERY, ["every walk", "cannot tell what changed"]),
]


@pytest.mark.parametrize("changed, walks, named", [row[1:] for row in ROWS], ids=[row[0] for row in ROWS])
def test_the_walks_a_change_picks_and_the_reason_names_what_is_behind_them(changed, walks, named):
    picked, reason = picker.walks(changed, MAP, EVERY)
    assert picked == walks
    for words in named:
        assert words in reason


@pytest.mark.parametrize("changed", [row[1] for row in ROWS], ids=[row[0] for row in ROWS])
def test_the_pick_is_never_empty_the_walks_that_always_run_are_in_every_answer(changed):
    assert "walks/test_guards.py" in picker.walks(changed, MAP, EVERY)[0]


def git(root, *args) -> str:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args], cwd=root,
                          capture_output=True, text=True, check=True).stdout.strip()


def commit(root, name, text="x") -> str:
    """Write a file, commit it, and give the commit's short hash, as the run log writes it."""
    (root / name).parent.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(text)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", name)
    return git(root, "rev-parse", "--short", "HEAD")


def a_branch(tmp_path):
    """A repo whose main has one commit and whose branch has two more: (root, main's commit, the branch's two)."""
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / ".gitignore").write_text(".checks/\n")
    start = commit(tmp_path, "README.md")
    git(tmp_path, "checkout", "-q", "-b", "feature/thing")
    return tmp_path, start, commit(tmp_path, "app/page_a.js"), commit(tmp_path, "app/page_b.js")


def log(root, *runs):
    """Hand-made run log lines: each a green run of every check on a clean folder, unless the run says otherwise."""
    (root / ".checks").mkdir(exist_ok=True)
    with open(root / ".checks" / "runs.jsonl", "a") as file:
        for run in runs:
            file.write(json.dumps({"result": "green", "dirty": False, "every": True, "quick": False, **run}) + "\n")


def full(root, short) -> str:
    return git(root, "rev-parse", short)


def test_the_base_is_the_last_green_run_of_every_check_on_a_clean_folder_the_branch_contains(tmp_path):
    root, _, first, second = a_branch(tmp_path)
    log(root, {"tip": first}, {"tip": second})
    commit_, why = picker.base(root)
    assert commit_ == full(root, second)
    assert "last green run of every check" in why and second in why


def a_commit_the_branch_no_longer_contains(root) -> str:
    git(root, "checkout", "-q", "-b", "abandoned")
    gone = commit(root, "app/page_c.js")
    git(root, "checkout", "-q", "feature/thing")
    return gone


@pytest.mark.parametrize("later", [
    {"result": "red"},
    {"every": False},
    {"dirty": True},
    {"picked": True},
    {"tip": "gone"},
], ids=["a red run", "a run of one named check", "a run on a dirty folder", "a picked run",
        "a run at a commit the branch no longer contains"])
def test_a_run_that_is_not_a_whole_green_run_on_this_branch_does_not_move_the_base(tmp_path, later):
    root, _, first, second = a_branch(tmp_path)
    tip = a_commit_the_branch_no_longer_contains(root) if later.get("tip") == "gone" else second
    log(root, {"tip": first}, {**later, "tip": tip})
    assert picker.base(root)[0] == full(root, first)


def test_with_no_whole_green_run_the_base_is_where_the_branch_left_main(tmp_path):
    root, start, _, second = a_branch(tmp_path)
    git(root, "checkout", "-q", "main")
    commit(root, "app/later_on_main.js")
    git(root, "checkout", "-q", "feature/thing")
    log(root, {"tip": second, "result": "red"})
    commit_, why = picker.base(root)
    assert commit_ == full(root, start)
    assert "where the branch left main" in why


def test_with_neither_a_whole_green_run_nor_main_it_cannot_tell_and_says_why(tmp_path):
    git(tmp_path, "init", "-q", "-b", "trunk")
    commit(tmp_path, "README.md")
    commit_, why = picker.base(tmp_path)
    assert commit_ is None
    assert "no green run of every check" in why and "main" in why


def test_what_changed_since_the_base_counts_uncommitted_untracked_and_deleted_files_and_a_rename_under_both_names(tmp_path):
    root, _, _, second = a_branch(tmp_path)
    log(root, {"tip": second})
    git(root, "mv", "app/page_a.js", "app/page_z.js")
    git(root, "commit", "-q", "-m", "rename")
    (root / "app" / "page_b.js").write_text("changed, not committed")
    (root / "README.md").unlink()
    (root / "app" / "new.js").write_text("not yet told to git")
    files, why = picker.changed(root)
    assert files == ["README.md", "app/new.js", "app/page_a.js", "app/page_b.js", "app/page_z.js"]
    assert second in why


def test_nothing_changed_since_the_base_is_an_empty_list_and_cannot_tell_is_none(tmp_path):
    root, _, _, second = a_branch(tmp_path)
    log(root, {"tip": second})
    assert picker.changed(root)[0] == []
    git(root, "branch", "-q", "-m", "main", "trunk")
    (root / ".checks" / "runs.jsonl").unlink()
    files, why = picker.changed(root)
    assert files is None and "cannot tell" in why
