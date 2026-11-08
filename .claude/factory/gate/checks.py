"""Lint, the configured checks and the red-run command (`gate.py lint`, `checks`, `red`)."""
from __future__ import annotations

import concurrent.futures
import json
import os
import re
import subprocess
import tempfile
import time

from gate.config import allowed, forbid_files, read
from gate.evidence import TIP_LINE
from gate.git import run_git
from gate.refuse import refuse
from gate.tracker import Feature, tracker_dir


def cmd_lint(root: str, config: dict) -> list:
    found = []
    for rule in config.get("forbid", []):
        try:
            pattern = re.compile(rule["pattern"])
        except (KeyError, re.error) as error:
            found.append("forbid rule %s is broken: %s" % (rule.get("name", "?"), error))
            continue
        for path in forbid_files(root, rule):
            if not os.path.isfile(path) or "node_modules" in path.split(os.sep):  # factory-allow: skips an installed-dependencies folder
                continue
            try:
                lines = read(path).split("\n")
            except OSError:
                continue
            for line_no, line in enumerate(lines, 1):
                if pattern.search(line) and not allowed(line):
                    found.append("%s:%d %s: %s" % (os.path.relpath(path, root), line_no, rule.get("name", "forbidden"), rule.get("why", "")))
    return found


WALK_OUTPUT_RE = re.compile(r"Walk output written to (\S+) \(exit")
WALK_RESULT_RE = re.compile(r"^(.+?) \u203a (.+): (red under load, green alone|red alone) \((?:retry|output): (.*)\)$")


def walk_results(check_output: str) -> list:
    """(file, title, verdict, path) for each line of the `## Result` section of the walk runner's output file,
    found through the path the runner prints (see Runner contract in docs/agents/evidence.md)."""
    found = WALK_OUTPUT_RE.search(check_output)
    if not found or not os.path.isfile(found.group(1)):
        return []
    text = read(found.group(1))
    if "\n## Result" not in text:
        return []
    return [m.groups() for m in (WALK_RESULT_RE.match(l) for l in text.split("\n## Result", 1)[1].split("\n")) if m]


def durations_path(root: str):
    common = run_git(root, "rev-parse", "--git-common-dir")
    if common is None:
        return None
    if not os.path.isabs(common):
        common = os.path.join(root, common)
    return os.path.join(common, "factory", "check-durations.jsonl")


def record_duration(root: str, name: str, seconds: int, green: bool) -> None:
    """One line per check run, in the git directory (never part of the tree), for `gate.py stats`."""
    path = durations_path(root)
    if not path:
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "check": name, "seconds": seconds, "green": green}) + "\n")
    except OSError:
        pass


def run_one(root: str, check: dict, out_dir: str) -> tuple:
    """One check's command, its output in its own file; returns (name, output path, exit code or 'timed out', seconds)."""
    name = check.get("name", "check")
    out_path = os.path.join(out_dir, re.sub(r"\W+", "-", name) + ".txt")
    started = time.time()
    with open(out_path, "w", encoding="utf-8") as out:
        try:
            code = subprocess.run(check["command"], shell=True, cwd=root, stdout=out, stderr=subprocess.STDOUT, timeout=check.get("timeout_s")).returncode
        except subprocess.TimeoutExpired:
            code = "timed out"
    return name, out_path, code, int(time.time() - started)


def run_checks(root: str, config: dict, only=None, flakes=None, reds=None) -> list:
    failures = []
    checks = [c for c in config.get("checks", []) if only is None or c.get("name") == only]
    if not checks:
        print("checks: none configured in docs/agents/local/factory.json")
        return ["no checks are configured, so nothing shows this tree is green"]
    out_dir = tempfile.mkdtemp(prefix="factory-gate-")
    # Every check runs at once, each in its own process, so the wait is the slowest suite and not the sum.
    # Each writes to its own file, and the results are read back in the configured order.
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(checks)) as pool:
        results = list(pool.map(lambda check: run_one(root, check, out_dir), checks))
    for check, (name, out_path, code, seconds) in zip(checks, results):
        record_duration(root, name, seconds, code == 0)
        if code == 0:
            print("check %s: green in %ds (output: %s)" % (name, seconds, out_path))
        else:
            print("check %s: RED, exit %s, after %ds. Read %s" % (name, code, seconds, out_path))
            failures.append("check %s is red (%s)" % (name, out_path))
            if reds is not None:
                reds.append((name, out_path, check.get("red_marker", "")))
        for file, title, verdict, path in walk_results(read(out_path)):
            if verdict == "red alone":
                print("RED %s: %s \u203a %s (%s)" % (name, file, title, path))
            else:
                print("FLAKE %s: %s \u203a %s (retry: %s)" % (name, file, title, path))
                if flakes is not None:
                    flakes.append((file, title))
    return failures


def cmd_checks(root: str, config: dict, only=None) -> int:
    if only is not None and only not in [c.get("name") for c in config.get("checks", [])]:
        return refuse("known-check", "no check named %s in factory.json" % only, "one of: %s" % (", ".join(c.get("name", "?") for c in config.get("checks", [])) or "none"), 2)
    problems = cmd_lint(root, config)
    for problem in problems:
        print("lint: %s" % problem)
    problems += run_checks(root, config, only)
    print("checks: %s" % ("all green" if not problems else "%d problem(s)" % len(problems)))
    return 1 if problems else 0


def cmd_red(root: str, config: dict, feature_name: str, label: str, check_name: str) -> int:
    """Run one check now and keep its output, `# tip <hash>` first, as the red run a box cites."""
    check = next((c for c in config.get("checks", []) if c.get("name") == check_name), None)
    if check is None:
        return refuse("known-check", "no check named %s in factory.json" % check_name, "one of: %s" % (", ".join(c.get("name", "?") for c in config.get("checks", [])) or "none"), 2)
    feature = Feature(root, config, feature_name)
    ticket = feature.get(label)
    tip = run_git(root, "rev-parse", "HEAD")
    if not tip:
        return refuse("red-tip", "there is no git commit to record as the tip", "a commit in the repo", 2)
    try:
        done = subprocess.run(check["command"], shell=True, cwd=root, capture_output=True, text=True, timeout=check.get("timeout_s"))
        code, output = done.returncode, done.stdout + done.stderr
    except subprocess.TimeoutExpired:
        code, output = "timed out", ""
    lines = output.split("\n")
    if lines and TIP_LINE.match(lines[0]):
        lines = lines[1:]  # the runner's own tip line: ours replaces it
    folder = os.path.join(root, tracker_dir(config), feature_name, "red")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "%s-%s-%s.txt" % (ticket.label, re.sub(r"\W+", "-", check_name), tip[:7]))
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("# tip %s\n%s" % (tip, "\n".join(lines)))
    rel = os.path.relpath(path, root)
    print("red: %s written (check %s exit %s, tip %s)" % (rel, check_name, code, tip[:7]))
    if code == 0:
        print("red: the check passed, so this is not red evidence: break the code first, then run this again")
    else:
        print("cite it as `red: %s` on the box of each new check it shows failing" % rel)
    return 0
