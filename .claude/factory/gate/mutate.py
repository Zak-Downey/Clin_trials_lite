"""Mutation testing of a ticket's changed files, and the ticket gate's reading of its report (`gate.py mutate`)."""
from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import time

from gate.config import read
from gate.git import integration_ref, rule_in_force, run_git
from gate.refuse import refuse
from gate.tracker import Feature, short, tracker_dir


DEFAULT_MUTATE_PATHS = []  # none until factory.json "mutate_paths" names them: the gate has no code of its own to mutate
CODE_SUFFIXES = (".py", ".js", ".mjs", ".cjs", ".html", ".css", ".sh", ".command")
SURVIVED = ("Survived", "NoCoverage")
EXEMPTION_RE = re.compile(r"(?://|/\*)\s?Stryker disable\b")  # factory-allow: the directive's spelling, which the report format fixes; capital S, case-sensitive
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def is_test_path(path: str) -> bool:
    parts = path.split("/")
    """A unit test file. The walks are not: they are code the mutation runner never mutates, so they are in the reviewer's hand sample."""
    return any(p in ("test", "tests") for p in parts[:-1]) or bool(re.search(r"\.test\.[cm]?js$", parts[-1]))


def path_matches(path: str, patterns: list) -> bool:
    return any(path == p or (p.endswith("/") and path.startswith(p)) or fnmatch.fnmatch(path, p) for p in patterns)


def changed_lines(root: str, base: str, head: str, path: str) -> list:
    """The line numbers `path` gained or changed between base...head (a new file: every line)."""
    out = run_git(root, "diff", "-U0", "%s...%s" % (base, head), "--", path) or ""
    lines = []
    for line in out.split("\n"):
        hunk = HUNK_RE.match(line)
        if hunk:
            start, count = int(hunk.group(1)), int(hunk.group(2) if hunk.group(2) is not None else 1)
            lines += range(start, start + count)
    return lines


def line_ranges(lines: list) -> str:
    runs, text = [], []
    for n in sorted(set(lines)):
        if runs and n == runs[-1][1] + 1:
            runs[-1][1] = n
        else:
            runs.append([n, n])
    for a, b in runs:
        text.append(str(a) if a == b else "%d-%d" % (a, b))
    return ", ".join(text)


class MutationScope:
    """What the ticket changed: the files the runner mutates, and the changed code it does not."""

    def __init__(self, root: str, config: dict, base: str, head: str):
        self.root, self.base, self.head = root, base, head
        tracker = tracker_dir(config) + "/"
        paths = config.get("mutate_paths", DEFAULT_MUTATE_PATHS)
        out = run_git(root, "diff", "--name-only", "--diff-filter=d", "%s...%s" % (base, head)) or ""
        self.changed = [f for f in out.split("\n") if f and not f.startswith(tracker) and not is_test_path(f)]
        skipped = config.get("mutate_except", [])  # files too slow for the ten-minute ceiling: the hand sample covers them
        self.mutated = [f for f in self.changed if f.endswith(".js") and path_matches(f, paths) and not path_matches(f, skipped)]
        self.excepted = [f for f in self.changed if f.endswith(".js") and path_matches(f, paths) and path_matches(f, skipped)]
        self.unmutated = [f for f in self.changed if f.endswith(CODE_SUFFIXES) and f not in self.mutated]

    def lines(self, path: str) -> list:
        return changed_lines(self.root, self.base, self.head, path)

    def exemptions(self) -> list:
        found = []
        for path in self.changed:
            full = os.path.join(self.root, path)
            if not path.endswith(".js") or not os.path.isfile(full):
                continue
            for n, line in enumerate(read(full).split("\n"), 1):
                if EXEMPTION_RE.search(line):
                    found.append("exemption: %s:%d  %s" % (path, n, line.strip()))
        return found


def survivors_of(report: dict, scope: MutationScope) -> tuple:
    """(in changed lines, elsewhere in changed files) as printable lines, from the runner's JSON report (the shape `mutate_report` in schema.json names)."""
    inside, elsewhere = [], []
    for path, entry in sorted((report.get("files") or {}).items()):
        path = path.replace(os.sep, "/")
        changed = set(scope.lines(path)) if path in scope.mutated else set()
        for m in entry.get("mutants", []):
            if m.get("status") not in SURVIVED:
                continue
            start, end = m["location"]["start"]["line"], m["location"]["end"]["line"]
            text = "%s:%d %s" % (path, start, m.get("mutatorName", "?"))
            if m.get("replacement"):
                text += " -> %s" % short(str(m["replacement"]), 60)
            (inside if changed & set(range(start, end + 1)) else elsewhere).append(text)
    return inside, elsewhere


def mutants_report_path(feature: Feature, label: str) -> str:
    return os.path.join(feature.dir, "reviews", "%s-mutants.json" % label)


def report_stale(feature: Feature, report: dict, head: str) -> str:
    """Why the report is not for this branch's tip ("" when it is): nothing outside the tracker changed since."""
    root = feature.root
    tip = (report.get("gate") or {}).get("tip", "")
    full = run_git(root, "rev-parse", "--verify", "-q", "%s^{commit}" % tip) if tip else None
    if not full:
        return "the mutants report names no commit of this repository as its tip"
    if not run_git(root, "merge-base", "--is-ancestor", full, head) is not None:
        return "the mutants report was made at %s, which is not on this branch" % tip[:7]
    tracker = tracker_dir(feature.config) + "/"
    moved = [f for f in (run_git(root, "diff", "--name-only", full, head) or "").split("\n") if f and not f.startswith(tracker)]
    if moved:
        return "the mutants report is for %s, and %s has changed since" % (full[:7], moved[0])
    return ""


def mutant_problems(feature: Feature, ticket: Ticket, red) -> list:
    """The ticket gate's reading of the mutants report: required when a changed file is under mutate_paths,
    stale when anything outside the tracker changed after it was made, refused on a survivor in a changed line."""
    if not red.base:
        return []
    if red.merged and not rule_in_force(feature.root, red.era, "mutants"):
        return []  # merged before this check existed
    scope = MutationScope(feature.root, feature.config, red.base, red.head)
    if not scope.mutated:
        return []
    where = os.path.relpath(mutants_report_path(feature, ticket.label), feature.root)
    again = "run `gate.py mutate %s %s` again" % (feature.name, ticket.label)
    if not os.path.isfile(os.path.join(feature.root, where)):
        return ["%s: no mutants report, and %s changed under mutate_paths: run `gate.py mutate %s %s`" % (where, scope.mutated[0], feature.name, ticket.label)]
    try:
        report = json.loads(read(os.path.join(feature.root, where)))
    except ValueError:
        return ["%s: not JSON: %s" % (where, again)]
    stale = report_stale(feature, report, red.head)
    if stale:
        return ["%s: %s: %s" % (where, stale, again)]
    inside, elsewhere = survivors_of(report, scope)
    for text in elsewhere:
        print("survivor elsewhere in a changed file: %s" % text)
    for line in scope.exemptions():
        print(line)
    return ["%s: survivor in a changed line: %s" % (where, text) for text in inside]


def cmd_mutate(root: str, config: dict, feature_name: str, label: str) -> int:
    feature = Feature(root, config, feature_name)
    ticket = feature.get(label)
    base = integration_ref(root, feature_name)
    head = run_git(root, "rev-parse", "HEAD")
    if not base or not head:
        return refuse("mutate-base", "there is no integration branch feature/%s or no commit to record" % feature_name, "the branch feature/%s and a commit on this one" % feature_name, 2)
    tracker = tracker_dir(config) + "/"
    dirty = [l[3:] for l in (run_git(root, "status", "--porcelain") or "").split("\n") if l and not l[3:].startswith(tracker)]
    if dirty:
        return refuse("mutate-clean", "uncommitted changes outside %s (%s)" % (tracker, dirty[0]), "the work committed, so the report is for a commit", 2)
    scope = MutationScope(root, config, base, head)
    print("changed files: %s" % (", ".join(scope.changed) or "none"))
    if scope.mutated:
        if not config.get("mutate_command") or not config.get("mutate_report"):
            return refuse("mutate-config", "mutate_paths is set and mutate_command or mutate_report is not", "both keys in factory.json (gate.py config shows them)", 2)
        command = config["mutate_command"].replace("{files}", ",".join(scope.mutated))
        produced = os.path.join(root, config["mutate_report"])
        if os.path.exists(produced):
            os.remove(produced)
        print("mutating: %s" % ", ".join(scope.mutated))
        started = time.time()
        subprocess.run(command, shell=True, cwd=root, timeout=config.get("mutate_timeout_s"))
        if not os.path.isfile(produced):
            return refuse("mutate-report", "the mutation run left no report at %s" % os.path.relpath(produced, root), "mutate_command writing its report to mutate_report", 2)
        report = json.loads(read(produced))
        report["gate"] = {"tip": head, "base": base, "files": scope.mutated, "seconds": round(time.time() - started)}
        target = mutants_report_path(feature, ticket.label)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=1)
        print("report: %s (tip %s, %ds)" % (os.path.relpath(target, root), head[:7], report["gate"]["seconds"]))
        inside, elsewhere = survivors_of(report, scope)
        for text in inside:
            print("survivor in a changed line: %s" % text)
        for text in elsewhere:
            print("survivor elsewhere in a changed file: %s" % text)
        print("survivors: %d in changed lines, %d elsewhere" % (len(inside), len(elsewhere)))
    elif scope.excepted:
        print("excepted from mutation (mutate_except): %s: no mutation run, no report needed; the hand sample covers it" % ", ".join(scope.excepted))
    else:
        print("nothing under mutate_paths changed: no mutation run, no report needed")
    for line in scope.exemptions():
        print(line)
    for path in scope.unmutated:
        print("not mutated: %s:%s" % (path, line_ranges(scope.lines(path))))
    return 0
