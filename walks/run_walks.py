"""Run the walk suite the way the gate reads it.

    .venv/bin/python walks/run_walks.py [pytest args]

Runs `pytest walks` across four workers (one browser each) into a file under
.scratch/<WALK_FEATURE>/walks/, prints the failures, re-runs each failed walk
alone once, and ends with a `## Result` section: one line per walk that failed,
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
            [sys.executable, "-m", "pytest", "walks", "-q", "-p", "no:cacheprovider", "-rf", *args],
            cwd=ROOT, stdout=out, stderr=subprocess.STDOUT,
        ).returncode


def main(argv) -> int:
    helper.SHOTS.mkdir(parents=True, exist_ok=True)
    output = helper.SHOTS / "walks-run.txt"
    print(f"# tip {tip()}")
    code = pytest(["-n", "4", *argv], output)
    text = output.read_text()
    print(f"Walk output written to {output} (exit {code})")
    failed = re.findall(r"^FAILED (\S+)", text, re.M)
    print("\n".join(text.splitlines()[-25:]))
    result = []
    for nodeid in dict.fromkeys(failed):
        alone = helper.SHOTS / f"alone-{helper.shot_name(nodeid)}.txt"
        if pytest([nodeid], alone) == 0:
            result.append(f"{nodeid} -- red under load, green alone ({alone})")
        else:
            result.append(f"{nodeid} -- red alone ({alone})")
    print("\n## Result")
    for line in result:
        print(line)
    return 1 if any("red alone" in line for line in result) else code if not failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
