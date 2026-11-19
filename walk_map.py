"""The map of the pages: which source files belong to which area, which walk files cover each area, and which files every
page shares. A product keeps its own map as JSON (this repo's: MAP); this module reads one and says what is wrong with it.

A map holds four keys, each a list of paths or glob patterns (fnmatch, matched against paths from the repo root, so `*`
also crosses `/`):
    shared  files every page depends on: a change to one reaches every walk
    always  walk files that run in every picked run
    areas   a list of {"name", "files", "walks"}: an area's source files and the walk files that cover it
    none    files that reach no walk
and, for the unit picker (picker.unit):
    run_apart    Python files the unit tests run only as a separate program, whose runs the record of which test ran
                 which code cannot see: a change to one runs every unit test
    unit_always  unit test files a picked run gives when the record selects none, so that green never means nothing
                 ran; with none listed, such a run runs every unit test
Any other key (a note for the reader) is ignored.
"""

from __future__ import annotations

import fnmatch
import json
import pathlib
import subprocess

MAP = "docs/agents/local/walk-map.json"
WALKS = "walks/test_*.py"  # what the walk runner runs: a walk file


def read(root, path=MAP) -> dict:
    return json.loads((pathlib.Path(root) / path).read_text())


def matches(path: str, patterns) -> bool:
    """Whether a repo path is one of the paths or patterns."""
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def repo_files(root) -> list[str]:
    """The files git tracks that are still there, and the new files it does not ignore."""
    listed = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=root,
                            capture_output=True, text=True, check=True).stdout.splitlines()
    return sorted(name for name in set(listed) if (pathlib.Path(root) / name).is_file())


def problems(the_map: dict, root, walks=WALKS, files=None) -> list[str]:
    """What is wrong with a map, one line a fault, each naming the file or area and the fault; empty when nothing is.
    `files` are the repo's files (default: repo_files(root))."""
    files = repo_files(root) if files is None else files
    areas = the_map.get("areas", [])
    covering = the_map.get("always", []) + [walk for area in areas for walk in area.get("walks", [])]
    placing = the_map.get("shared", []) + the_map.get("none", []) + [f for area in areas for f in area.get("files", [])]
    found = []
    for name in files:
        if fnmatch.fnmatchcase(name, walks):
            if not matches(name, covering):
                found.append(f"{name}: a walk file in neither `always` nor an area")
        elif not matches(name, placing):
            found.append(f"{name}: placed by no `shared`, area or `none`")
    for pattern, where, walk in listed(the_map):
        if matches_any(pattern, files):
            continue
        literal = not any(c in pattern for c in "*?[")
        fault = "a walk file that does not exist" if walk and literal else "matches no file"
        found.append(f"{pattern} (in {where}): {fault}")
    found += [f"area {area.get('name')}: has no walk" for area in areas if not area.get("walks")]
    return found


def listed(the_map: dict):
    """Each path or pattern the map lists, with where it is listed and whether it lists walk files."""
    for key in ("shared", "always", "none", "run_apart", "unit_always"):
        for pattern in the_map.get(key, []):
            yield pattern, f"`{key}`", key == "always"
    for area in the_map.get("areas", []):
        for key in ("files", "walks"):
            for pattern in area.get(key, []):
                yield pattern, f"area {area.get('name')}", key == "walks"


def matches_any(pattern: str, files) -> bool:
    return any(fnmatch.fnmatchcase(name, pattern) for name in files)
