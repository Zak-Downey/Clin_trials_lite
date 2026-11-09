"""By hand, outside the gate: does the stand-in still look like the real registry?

    python walks/fidelity_check.py

Fetches NCT03412565 live from ClinicalTrials.gov (the one network call in the
walk tooling, so nothing here runs in a suite and nothing goes red when it
breaks) and compares its structure with the captured fixture the stand-in serves:
every key path (list positions collapsed) and its value type. Exits 1 when a path
or type in the fixture is not in the live record, or the stand-in does not serve
the fixture. Paths only the live record has are listed, not failed: the registry
may add fields. Record the date in docs/agents/local/repo.md when it passes.
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import ctgov  # noqa: E402
from walks import helper, standin_registry  # noqa: E402


def shape(value, prefix="") -> dict[str, str]:
    """{key path: type name}, list positions collapsed to []."""
    found = {prefix or "$": type(value).__name__}
    if isinstance(value, dict):
        for key, inner in value.items():
            found.update(shape(inner, f"{prefix}.{key}"))
    elif isinstance(value, list):
        for inner in value:
            found.update(shape(inner, f"{prefix}[]"))
    return found


def compare(fixture: dict, live: dict) -> tuple[list[str], list[str]]:
    """(problems, extras): fixture paths missing or retyped live, and paths only live has."""
    ours, theirs = shape(fixture), shape(live)
    problems = []
    for path, kind in sorted(ours.items()):
        if path not in theirs:
            problems.append(f"missing live: {path}")
        elif theirs[path] != kind and "NoneType" not in (kind, theirs[path]):
            problems.append(f"type differs: {path} fixture {kind}, live {theirs[path]}")
    return problems, sorted(set(theirs) - set(ours))


def main() -> int:
    fixture = json.loads(standin_registry.FIXTURE.read_text(encoding="utf-8"))
    registry = helper.Registry()
    try:
        served = registry.fetch("NCT03412565")
    finally:
        registry.close()
    if served != fixture:
        print("The stand-in does not serve the captured fixture.")
        return 1
    live = ctgov.get("NCT03412565")
    problems, extras = compare(fixture, live)
    for line in problems:
        print(line)
    print(f"{len(extras)} paths only the live record has" + (": " + ", ".join(extras[:10]) if extras else ""))
    print("FAIL" if problems else "OK: the live record has every path and type the fixture has")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
