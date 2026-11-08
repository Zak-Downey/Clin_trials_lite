"""What is ready, in flight, held, blocked or done (`gate.py frontier`)."""
from __future__ import annotations

import re

from gate.git import run_git, touches_clash, worktree_branches
from gate.log import empty_frontier_checklist, read_log
from gate.tracker import TERMINAL, Feature


def has_worktree(feature: Feature) -> list:
    """Tickets whose branch is checked out in some worktree. A branch belongs
    to a ticket when its last segment is the ticket file's name (without .md)
    or its leading words: ticket/07-update-status for 07-update-status-form.md.
    A branch named <ticket file name>--<part> is a part of that ticket's work,
    such as one exploratory walker's area."""
    branches = [b for b in worktree_branches(feature.root) if re.match(r"^\d+-", b)]
    found = []
    for number, ticket in feature.tickets.items():
        if any(ticket.stem == b or ticket.stem.startswith(b + "-") or b.startswith(ticket.stem + "--") for b in branches):
            found.append(number)
    return found


def in_flight(feature: Feature) -> list:
    """Tickets an agent is working: ready-for-agent, with a worktree."""
    return [n for n in has_worktree(feature) if feature.tickets[n].status == "ready-for-agent"]


def unpushed(feature: Feature):
    """(merge count, upstream tip) when the integration branch has an upstream and is ahead of it, else None."""
    branch = "feature/%s" % feature.name
    upstream = run_git(feature.root, "rev-parse", "--verify", "-q", "%s@{upstream}" % branch)
    if not upstream:
        return None
    ahead = run_git(feature.root, "rev-list", "--first-parent", "--count", "%s..%s" % (upstream, branch))
    if not ahead or int(ahead) == 0:
        return None
    merges = run_git(feature.root, "rev-list", "--first-parent", "--merges", "--count", "%s..%s" % (upstream, branch))
    return int(merges or 0), upstream


def foundation_hold(feature: Feature, number: int, entries: list):
    """Why the foundation read holds a ticket, or None: its Blocked by names a done foundational ticket
    whose read is not logged (`foundation-read`) or is logged and not yet reported (`report <NN> branch-reviewer`)."""
    for blocker in feature.blockers.get(number, []):
        base = feature.tickets[blocker]
        if base.kind != "foundational" or base.status != "done":
            continue
        read_at = next((i for i, e in enumerate(entries) if e["verb"] == "foundation-read" and e["args"][0] == base.label), None)
        if read_at is None:
            return "foundation %s read not dispatched" % base.label
        if not any(e["verb"] == "report" and e["args"][:2] == [base.label, "branch-reviewer"] for e in entries[read_at + 1:]):
            return "foundation %s read pending" % base.label
    return None


def cmd_frontier(feature: Feature) -> int:
    entries = read_log(feature.root, feature.name)
    tickets = feature.tickets
    flying = in_flight(feature)
    worktrees = has_worktree(feature)
    groups = {"done": [], "in flight": [], "ready": [], "held": [], "blocked": [], "waiting on a person": []}
    notes = []
    for number in sorted(tickets):
        ticket = tickets[number]
        if ticket.status in TERMINAL:
            groups["done"].append(ticket.label)
        elif number in flying:
            groups["in flight"].append(ticket.label)
        elif ticket.status == "ready-for-agent":
            waiting = feature.open_blockers(number)
            if waiting:
                groups["blocked"].append("%s (on %s)" % (ticket.label, ", ".join(tickets[b].label for b in waiting)))
                continue
            hold = foundation_hold(feature, number, entries)
            if hold:
                groups["held"].append("%s (%s)" % (ticket.label, hold))
                continue
            clash = None
            for other in flying:
                clash = touches_clash(ticket.touches, tickets[other].touches)
                if clash:
                    if clash == "*":
                        groups["held"].append("%s (one of it and in-flight %s is marked `*`, to run alone)" % (ticket.label, tickets[other].label))
                    else:
                        groups["held"].append("%s (touches %s, as does in-flight %s)" % (ticket.label, clash, tickets[other].label))
                    break
            if not clash:
                groups["ready"].append(ticket.label)
        else:
            waiting = feature.open_blockers(number)
            suffix = " (blocked on %s)" % ", ".join(tickets[b].label for b in waiting) if waiting else ""
            if number in worktrees:
                suffix += " (has a worktree: its commits are the work so far)"
            groups["waiting on a person"].append("%s %s%s" % (ticket.label, ticket.status or "no-status", suffix))
    ready = [tickets[int(label)] for label in groups["ready"]]
    for i, first in enumerate(ready):
        for second in ready[i + 1:]:
            clash = touches_clash(first.touches, second.touches)
            if clash:
                why = "one of %s and %s is marked `*`, to run alone" % (first.label, second.label) if clash == "*" else "%s and %s both touch %s" % (first.label, second.label, clash)
                notes.append("%s: dispatch one, then the other" % why)
        if not first.touches_declared:
            notes.append("%s has no Touches line: check by hand that it shares no hot file with a ticket in flight" % first.label)
    print("feature: %s" % feature.name)
    for name in ("ready", "held", "in flight", "blocked", "waiting on a person", "done"):
        if groups[name]:
            print("%s (%d): %s" % (name, len(groups[name]), "; ".join(groups[name])))
    for note in notes:
        print("note: %s" % note)
    for problem in feature.problems:
        print("problem: %s" % problem)
    ahead = unpushed(feature)
    if ahead:
        print("unpushed: %d merge(s) since %s" % (ahead[0], ahead[1][:7]))
    if not any(groups[g] for g in ("ready", "held", "in flight", "blocked")):
        print("frontier is empty: every ticket is done or waits on a person")
        if all(t.status in TERMINAL or t.status == "ready-for-human" for t in tickets.values()) and not feature.problems:
            for line in empty_frontier_checklist(feature.name):
                print(line)
    return 1 if feature.problems else 0
