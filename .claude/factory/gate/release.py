"""Moving a spec and its tickets to ready-for-agent (`gate.py release`)."""
from __future__ import annotations

import fnmatch
import os
import re

from gate.config import read
from gate.git import integration_ref, run_git
from gate.log import read_log
from gate.refuse import refuse
from gate.tracker import KIND_WORDS, set_status


def user_facing(config: dict, path: str) -> bool:
    path = path.strip().strip("`").rstrip("/")
    if not path or path == "*":
        return False
    def hit(globs):
        return any(fnmatch.fnmatch(path, g) or fnmatch.fnmatch(path + "/x", g) for g in globs)
    return hit(config.get("user_facing", [])) and not hit(config.get("user_facing_except", []))


def design_mark_problems(feature: Feature, ticket: Ticket, red) -> list:
    """A review-fix ticket whose diff touches a user-facing path is a design decision: it needs
    `Kind: design` and an Open list item in the fix spec naming it."""
    if not feature.name.endswith("-review") or not red.base:
        return []
    out = run_git(feature.root, "diff", "--name-only", "%s...%s" % (red.base, red.head))
    changed = [f for f in (out or "").split("\n") if f and user_facing(feature.config, f)]
    if not changed:
        return []
    where = os.path.relpath(ticket.path, feature.root)
    if ticket.kind != "design":
        return ["%s: its diff touches a user-facing path (%s) and the ticket is not marked `Kind: design` (docs/agents/tickets.md#kind)" % (where, changed[0])]
    spec = read(os.path.join(feature.dir, "spec.md"))
    open_list = spec.split("## Open list", 1)[1] if "## Open list" in spec else ""
    open_list = re.split(r"^#{1,6}\s", open_list.split("\n", 1)[1] if "\n" in open_list else "", 1, flags=re.M)[0]
    if not (ticket.stem in open_list or re.search(r"\bticket\s+0*%d\b" % ticket.number, open_list, re.I)):
        return ["%s: a design ticket needs an item in the spec's Open list naming it (`ticket %s`)" % (where, ticket.label)]
    return []


SPEC_PATH_RE = re.compile(r"[\w.*-]+(?:/[\w.*-]+)+")


def cmd_release(root: str, config: dict, feature: Feature) -> int:
    spec_path = os.path.join(feature.dir, "spec.md")
    if not os.path.isfile(spec_path):
        return refuse("release-spec", "%s has no spec.md" % feature.name, "a spec.md in the feature folder", 2)
    spec = read(spec_path)
    chain = re.match(r"^(.+)-review-(\d+|review)$", feature.name)
    if chain:
        root_feature = chain.group(1)
        return refuse("release-rounds",
                      "%s would be a second fix feature of %s; the whole-branch review's two rounds belong to %s and %s-review has had them" % (feature.name, root_feature, root_feature, root_feature),
                      "no new fix feature: what still blocks goes to the user's Open list (orchestrator.md#the-whole-branch-review)")
    status = re.search(r"^\**Status:\**\s*`?([A-Za-z-]+)", spec, re.M)
    problems = []
    if not status or status.group(1).lower() != "needs-triage":
        problems.append("%s is already released (spec Status is %s, not needs-triage)" % (feature.name, status.group(1) if status else "missing"))
        for p in problems:
            print(p)
        return refuse("release-status", "%d problem(s) are listed above" % len(problems), "a spec whose Status is needs-triage")
    problems += feature.problems
    for ticket in feature.tickets.values():
        if ticket.kind and ticket.kind not in KIND_WORDS:
            problems.append("%s: unknown Kind `%s` (one of: %s)" % (os.path.relpath(ticket.path, root), ticket.kind, ", ".join(KIND_WORDS)))
    branch = integration_ref(root, feature.name)
    if not branch:
        problems.append("there is no integration branch feature/%s to check against the protected branch" % feature.name)
    else:
        for protected in config.get("protected_branches", []):
            tip = run_git(root, "rev-parse", "--verify", "-q", "refs/heads/%s^{commit}" % protected)
            base = run_git(root, "merge-base", protected, branch) if tip else None
            if not tip:
                problems.append("the protected branch %s does not exist here, so feature/%s cannot be checked against its tip" % (protected, feature.name))
            elif base != tip:
                problems.append("feature/%s is not cut from the tip of %s: its merge-base with %s is %s, %s is at %s" % (feature.name, protected, protected, (base or "none")[:7], protected, tip[:7]))
    paths = set()
    for ticket in feature.tickets.values():
        paths.update(ticket.touches)
    paths.update(SPEC_PATH_RE.findall(spec))
    facing = sorted(p for p in paths if user_facing(config, p))
    kinds = [t.kind for t in feature.tickets.values()]
    if facing:
        for need in ("acceptance-walk", "exploration"):
            if need not in kinds:
                problems.append("the spec touches user-facing paths (%s) and no ticket is marked `Kind: %s` (docs/agents/tickets.md#kind)" % (facing[0], need))
    if "foundational" not in kinds:
        problems.append("no ticket is marked `Kind: foundational` (docs/agents/tickets.md#kind)")
    if re.search(r"^\**Brief:\**", spec, re.M) and not any(e["verb"] == "spec-against-brief" for e in read_log(root, feature.name)):
        problems.append("the spec has a Brief: line and the build log has no spec-against-brief entry (`gate.py log %s spec-against-brief <path>`)" % feature.name)
    if problems:
        for p in problems:
            print(p)
        return refuse("release-checks", "%d problem(s) are listed above" % len(problems), "each problem fixed, then release again")
    set_status(spec_path, "ready-for-agent")
    moved = 0
    for ticket in feature.tickets.values():
        if ticket.status == "needs-triage":
            set_status(ticket.path, "ready-for-agent")
            moved += 1
    print("released %s: the spec and %d ticket(s) are ready-for-agent" % (feature.name, moved))
    return 0
