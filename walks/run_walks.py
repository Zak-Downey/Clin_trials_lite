"""Run the walk suite and say which red walks are real.

    .venv/bin/python walks/run_walks.py [pytest args]

Runs `pytest walks` across four workers (one browser each) into a file under
.scratch/<WALK_FEATURE>/walks/, prints the failures, re-runs each failed walk
alone once, and ends with a `## Result` section: one line per walk that failed or erred,
`red alone` or `red under load, green alone`, also appended to the output file. At most ALONE_CAP walks are re-run; the rest are
listed as red, not re-run. The first run ends early once MASS_FAILURE walks are red, and the section says so.
Each run appends one line to FLAKY_RECORD beside the output file: the time, the commit and the walks that were red
under load and green alone (an empty list when none was). Exit 1 when any walk failed alone, or, with FLAKY_IS_RED
on, when any walk was flaky.
"""

from __future__ import annotations

import datetime
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from walks import helper  # noqa: E402 (imported once the repo root is on sys.path, above)


def tip() -> str:
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def pytest_command(args, targets):
    """The pytest command line: the targets, then the arguments. A re-run of one walk passes its node id as the only target."""
    return [sys.executable, "-m", "pytest", *targets, "-q", "-p", "no:cacheprovider", "-rfE", *args]


def pytest(args, output, targets=("walks",), cwd=ROOT):
    with open(output, "w") as out:
        return subprocess.run(
            pytest_command(args, targets),
            cwd=cwd, stdout=out, stderr=subprocess.STDOUT,
        ).returncode


def red_walks(text: str) -> list[str]:
    """The walks a run reported red: failed, or erred in setup (an app or registry that did not start)."""
    return list(dict.fromkeys(re.findall(r"^(?:FAILED|ERROR) (\S+)", text, re.M)))


ALONE_CAP = 10  # red walks re-run alone; the rest are listed red, so a mass failure still names every walk inside the timeout
MASS_FAILURE = 20  # the first run stops once this many walks are red: a mass failure, where each walk left would only
# wait out its timeouts and push the run past its time limit before any walk is named


FLAKY_IS_RED = False  # True: a walk red with the others and green alone makes the run exit 1, as one red alone does
FLAKY_RECORD = "flaky.jsonl"  # beside walks-run.txt: one line per run, {"at", "tip", "flaky": [node ids]}; [] when none


def record_flaky(folder: pathlib.Path, flaky: list[str]) -> None:
    """Append this run's flaky walks (red with the others, green alone) to the record, with the commit and the time."""
    line = {"at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "tip": tip(), "flaky": flaky}
    with open(folder / FLAKY_RECORD, "a") as record:
        record.write(json.dumps(line) + "\n")


def split_args(argv):
    """(targets, options): an argument that names an existing file or node id is a target; the rest are pytest options."""
    targets = tuple(a for a in argv if not a.startswith("-") and pathlib.Path(a.split("::")[0]).exists())
    return targets, [a for a in argv if a not in targets]


def result_line(nodeid: str, verdict: str, where: str) -> str:
    """`<file> \u203a <title>: <verdict> (retry: <path>)`."""
    file, _, title = nodeid.partition("::")
    return f"{file} \u203a {title}: {verdict} (retry: {where})"


def exit_code(code: int, result: list[str]) -> int:
    """1 when a walk is red alone, or green alone with FLAKY_IS_RED on; the run's own code when it was red with nothing re-run to show for it; else 0."""
    if any("red alone" in line for line in result):
        return 1
    if FLAKY_IS_RED and any("green alone" in line for line in result):
        return 1
    return code if not result else 0


def main(argv, targets=None, cwd=ROOT, shots=None) -> int:
    shots = shots or helper.SHOTS
    shots.mkdir(parents=True, exist_ok=True)
    output = shots / "walks-run.txt"
    given, options = split_args(argv)
    targets = given or targets or ("walks",)
    print(f"# tip {tip()}")
    code = pytest(["-n", "4", f"--maxfail={MASS_FAILURE}", *options], output, targets, cwd)
    text = output.read_text()
    print(f"Walk output written to {output} (exit {code})")
    failed = red_walks(text)
    print("\n".join(text.splitlines()[-25:]))
    result, flaky = [], []
    for number, nodeid in enumerate(failed):
        if number >= ALONE_CAP:
            result.append(result_line(nodeid, "red alone", f"not re-run, over the cap of {ALONE_CAP}; see {output}"))
            continue
        file, _, _ = nodeid.partition("::")
        alone = shots / f"alone-{pathlib.Path(file).stem}-{helper.shot_name(nodeid)}.txt"
        if pytest(options, alone, (nodeid,), cwd) == 0:
            result.append(result_line(nodeid, "red under load, green alone", alone))
            flaky.append(nodeid)
        else:
            result.append(result_line(nodeid, "red alone", alone))
    if len(failed) >= MASS_FAILURE:
        result.append(f"The first run ended early, at {MASS_FAILURE} red walks; the walks after them were not run.")
    section = "\n## Result\n" + "".join(f"{line}\n" for line in result)
    with open(output, "a") as handle:
        handle.write(section)
    print(section, end="")
    record_flaky(shots, flaky)
    return exit_code(code, result)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
