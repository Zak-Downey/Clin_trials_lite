"""The map of the pages: what the reader says is wrong with a map, on small repos made here, and on this repo's own map.

Every repo below is a real git repo in a temporary folder with a hand-made map.
"""

from __future__ import annotations

import pathlib
import subprocess

import walk_map

FILES = ["app/shell.js", "app/page_a.js", "app/page_b.js", "walks/helper.py", "walks/test_guards.py",
         "walks/test_page_a.py", "walks/test_page_b.py", "README.md"]


def a_map(**changes):
    the_map = {
        "shared": ["app/shell.js", "walks/helper.py"],
        "always": ["walks/test_guards.py"],
        "areas": [
            {"name": "Page A", "files": ["app/page_a.js"], "walks": ["walks/test_page_a.py"]},
            {"name": "Page B", "files": ["app/page_b.js"], "walks": ["walks/test_page_b.py"]},
        ],
        "none": ["*.md"],
    }
    the_map.update(changes)
    return the_map


def a_repo(tmp_path, files=FILES):
    for name in files:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    return tmp_path


def test_a_map_that_places_every_file_and_walk_has_no_problems(tmp_path):
    assert walk_map.problems(a_map(), a_repo(tmp_path)) == []


def test_a_walk_file_in_neither_always_nor_an_area_is_reported_by_name(tmp_path):
    root = a_repo(tmp_path, FILES + ["walks/test_page_c.py"])
    assert walk_map.problems(a_map(), root) == [
        "walks/test_page_c.py: a walk file in neither `always` nor an area"]


def test_a_file_that_shared_an_area_and_none_do_not_place_is_reported_by_name(tmp_path):
    root = a_repo(tmp_path, FILES + ["app/page_c.js"])
    assert walk_map.problems(a_map(), root) == ["app/page_c.js: placed by no `shared`, area or `none`"]


def test_a_new_file_git_has_not_been_told_of_is_reported_too(tmp_path):
    root = a_repo(tmp_path)
    (root / "app" / "page_c.js").write_text("")
    assert walk_map.problems(a_map(), root) == ["app/page_c.js: placed by no `shared`, area or `none`"]


def test_a_pattern_that_matches_no_file_is_reported_with_where_it_is_listed(tmp_path):
    the_map = a_map(none=["*.md", "docs/*"])
    the_map["areas"][1]["files"].append("app/page_b_*.js")
    assert walk_map.problems(the_map, a_repo(tmp_path)) == [
        "docs/* (in `none`): matches no file",
        "app/page_b_*.js (in area Page B): matches no file",
    ]


def test_a_listed_walk_file_that_does_not_exist_is_reported_by_name(tmp_path):
    the_map = a_map(always=["walks/test_guards.py", "walks/test_gone.py"])
    the_map["areas"][0]["walks"].append("walks/test_page_a_old.py")
    assert walk_map.problems(the_map, a_repo(tmp_path)) == [
        "walks/test_gone.py (in `always`): a walk file that does not exist",
        "walks/test_page_a_old.py (in area Page A): a walk file that does not exist",
    ]


def test_an_area_with_no_walk_is_reported_by_name(tmp_path):
    the_map = a_map()
    the_map["areas"].append({"name": "Page C", "files": ["app/page_b.js"], "walks": []})
    assert walk_map.problems(the_map, a_repo(tmp_path)) == ["area Page C: has no walk"]


ROOT = pathlib.Path(walk_map.__file__).resolve().parent


def test_this_repo_s_map_places_every_file_and_every_walk_file():
    assert walk_map.problems(walk_map.read(ROOT), ROOT) == []


def test_this_repo_s_map_is_red_when_a_walk_file_is_taken_out_of_it():
    the_map = walk_map.read(ROOT)
    the_map["always"] = [walk for walk in the_map["always"] if walk != "walks/test_walk_guards.py"]
    assert "walks/test_walk_guards.py: a walk file in neither `always` nor an area" in walk_map.problems(the_map, ROOT)


def test_this_repo_s_map_is_red_when_a_new_file_under_webapp_has_no_place():
    files = walk_map.repo_files(ROOT)
    for new in ("webapp/api_new_page.py", "webapp/static/views/new_page.js"):
        assert f"{new}: placed by no `shared`, area or `none`" in walk_map.problems(walk_map.read(ROOT), ROOT, files=files + [new])
