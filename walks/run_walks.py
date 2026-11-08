"""Run the walk suite the way the gate reads it.

    .venv/bin/python walks/run_walks.py [pytest args]

Runs `pytest walks` across four workers (one browser each) into a file under
.scratch/<WALK_FEATURE>/walks/, prints the failures, re-runs each failed walk
alone once, and ends with a `## Result` section: one line per walk that failed or erred,
`red alone` or `red under load, green alone`. Exit 1 when any walk failed alone.
"""

from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from walks import helper  # noqa: E402


def tip() -> str:
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def pytest(args, output):
    with open(output, "w") as out:
        return subprocess.run(
            [sys.executable, "-m", "pytest", "walks", "-q", "-p", "no:cacheprovider", "-rfE", *args],
            cwd=ROOT, stdout=out, stderr=subprocess.STDOUT,
        ).returncode


def red_walks(text: str) -> list[str]:
    """The walks a run reported red: failed, or erred in setup (an app or registry that did not start)."""
    return list(dict.fromkeys(re.findall(r"^(?:FAILED|ERROR) (\S+)", text, re.M)))


def exit_code(code: int, result: list[str]) -> int:
    """1 when a walk is red alone; the run's own code when it was red with nothing re-run to show for it; else 0."""
    if any("red alone" in line for line in result):
        return 1
    return code if not result else 0


def main(argv) -> int:
    helper.SHOTS.mkdir(parents=True, exist_ok=True)
    output = helper.SHOTS / "walks-run.txt"
    print(f"# tip {tip()}")
    code = pytest(["-n", "4", *argv], output)
    text = output.read_text()
    print(f"Walk output written to {output} (exit {code})")
    failed = red_walks(text)
    print("\n".join(text.splitlines()[-25:]))
    result = []
    for nodeid in failed:
        alone = helper.SHOTS / f"alone-{helper.shot_name(nodeid)}.txt"
        if pytest([nodeid], alone) == 0:
            result.append(f"{nodeid} -- red under load, green alone ({alone})")
        else:
            result.append(f"{nodeid} -- red alone ({alone})")
    print("\n## Result")
    for line in result:
        print(line)
    return exit_code(code, result)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
