"""Write a notice to the run's summary when a pull request changes what judges it or removes a test.

    python3 judge_notice.py BASE PATH [PATH ...]

BASE is the commit the pull request is compared against; each PATH is a file that judges the pull request, or a
folder (ending in /) whose every file does. The notice lists the judging files changed since BASE and the number
of tests removed: lines that define a test (`def test_...`) taken out of files named test_*.py, less those put
in, never below nought. A deleted test file counts every test it had; a renamed test counts as neither. A renamed
file counts as its old path removed and its new path added (git's rename detection is off), so a judging file renamed
away is listed under its old name, and a test file renamed to a name not collected counts its tests removed.

It is a notice, never a failure: it always exits 0. It writes nothing when nothing judging changed and no test was
removed, and nothing when BASE is empty (a run started by hand has no pull request to compare against).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

TEST_FILE = re.compile(r"(^|/)test_[^/]*\.py$")
TEST_DEF = re.compile(r"^\s*(async\s+)?def\s+test_")


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def judges(path, judging):
    return any(path.startswith(j) if j.endswith("/") else path == j for j in judging)


def changed_files(base):
    return [line for line in git("diff", "--no-renames", "--name-only", f"{base}...HEAD").splitlines() if line]


def tests_removed(base):
    removed = added = 0
    current = None
    for line in git("diff", "--no-renames", "--no-color", "--unified=0", f"{base}...HEAD").splitlines():
        if line.startswith("diff --git "):
            current = line.split(" b/", 1)[-1]
            continue
        if line.startswith(("--- ", "+++ ")):
            continue
        if current is None or not TEST_FILE.search(current):
            continue
        if line.startswith("-") and TEST_DEF.match(line[1:]):
            removed += 1
        elif line.startswith("+") and TEST_DEF.match(line[1:]):
            added += 1
    return max(removed - added, 0)


def notice(base, judging):
    """The notice's text, or "" when there is nothing to say."""
    if not base:
        return ""
    changed = [path for path in changed_files(base) if judges(path, judging)]
    removed = tests_removed(base)
    if not changed and not removed:
        return ""
    lines = [
        "## This pull request changes what judges it",
        "",
        "This is a notice, not a failure: such a change can be right, and the owner decides.",
        "",
    ]
    if changed:
        lines += ["Files that judge the pull request and are changed by it:", ""]
        lines += [f"- `{path}`" for path in changed]
        lines.append("")
    lines.append(f"Tests removed: {removed} (lines defining a test taken out of test_*.py files, less those put in)")
    return "\n".join(lines) + "\n"


def main(argv):
    try:
        text = notice(argv[1] if len(argv) > 1 else "", argv[2:])
        if text:
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
                summary.write(text)
            print(text)
    except Exception as error:  # a notice never fails the run
        print(f"The notice could not be written: {error}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
