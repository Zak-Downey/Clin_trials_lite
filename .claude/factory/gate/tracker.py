"""The Markdown tracker: tickets, acceptance boxes, features, and the header and box grammar."""
from __future__ import annotations

import os
import re

from gate.config import read, tracker_dir
from gate.refuse import refusal


TERMINAL = ("done", "wontfix")
PROOF_KINDS = ("test", "walk", "doc", "check", "shot")
KINDS = PROOF_KINDS + ("red", "needs-human")
_KIND_ALT = "|".join(KINDS)

HEADER_RE = {
    "status": re.compile(r"^\s*\**Status\**\s*:\**\s*(.*)$", re.I),
    "blocked": re.compile(r"^\s*\**Blocked by\**\s*:\**\s*(.*)$", re.I),
    "touches": re.compile(r"^\s*\**Touches\**\s*:\**\s*(.*)$", re.I),
    "kind": re.compile(r"^\s*\**Kind\**\s*:\**\s*(.*)$", re.I),
}
KIND_WORDS = ("foundational", "walk-tooling", "acceptance-walk", "exploration", "ready-for-human", "design")
# The kinds a `ticket-reviewer` reads before the merge; every other ticket's second read is the whole-branch review's.
REVIEWED_KINDS = ("foundational", "walk-tooling")
BOX_RE = re.compile(r"^\s*[-*]\s+\[([ xX])\]\s+(.*)$")
EVIDENCE_SPLIT = re.compile(r"\s(?:—|–|--)\s+(?=(?:%s)\s*:)" % _KIND_ALT)
EVIDENCE_ITEM = re.compile(r"^\s*(%s)\s*:\s*(.*)$" % _KIND_ALT, re.S)
RANGE_RE = re.compile(r"\b(\d{1,3})\s*(?:to|\.\.|-|–)\s*(\d{1,3})\b", re.I)


class Box:
    def __init__(self, line_no: int, ticked: bool, text: str, evidence: list):
        self.line_no = line_no
        self.ticked = ticked
        self.text = text
        self.evidence = evidence  # [(kind, pointer)]

    def proof(self) -> list:
        return [e for e in self.evidence if e[0] in PROOF_KINDS]

    def judgement(self) -> list:
        return [p for k, p in self.evidence if k == "needs-human" and p]

    def state(self) -> str:
        if self.ticked:
            return "proved" if self.proof() else "unproved"
        return "human" if self.judgement() else "open"


class Ticket:
    def __init__(self, path: str):
        self.path = path
        self.stem = os.path.splitext(os.path.basename(path))[0]
        match = re.match(r"^(\d+)", self.stem)
        self.number = int(match.group(1)) if match else -1
        self.label = match.group(1) if match else self.stem
        self.title = self.stem
        self.status = ""
        self.blocked_raw = ""
        self.touches = []
        self.touches_declared = False
        self.kind = ""
        self.boxes = []
        self._parse()

    def _parse(self) -> None:
        in_head = True
        for line_no, line in enumerate(read(self.path).split("\n"), 1):
            if line.startswith("# ") and self.title == self.stem:
                self.title = line[2:].strip()
                continue
            if re.match(r"^##\s+Comments\b", line, re.I):
                in_head = False
            if not in_head:
                continue
            for key, pattern in HEADER_RE.items():
                match = pattern.match(line)
                if not match:
                    continue
                value = match.group(1).strip()
                if key == "status" and not self.status:
                    word = re.match(r"[`*\s]*([A-Za-z-]+)", value)
                    self.status = word.group(1).lower() if word else ""
                elif key == "blocked" and not self.blocked_raw:
                    self.blocked_raw = value
                elif key == "kind" and not self.kind:
                    word = re.match(r"[`*\s]*([A-Za-z-]+)", value)
                    self.kind = word.group(1).lower() if word else ""
                elif key == "touches" and not self.touches_declared:
                    self.touches_declared = True
                    named = [t.strip().strip("`").rstrip("/") for t in value.split(",") if t.strip().strip("`")]
                    self.touches = [] if [n.lower() for n in named] in (["none"], ["nothing"]) else named
            box = BOX_RE.match(line)
            if box:
                self.boxes.append(parse_box(line_no, box.group(1) != " ", box.group(2)))


def split_outside_brackets(text: str, separator: str) -> list:
    """Splits on the separator, but not inside round brackets: a title's own
    aside, `(browser half; the API half is tested)`, stays in one piece."""
    pieces = []
    depth = 0
    current = ""
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")" and depth:
            depth -= 1
        if char == separator and depth == 0:
            pieces.append(current)
            current = ""
        else:
            current += char
    pieces.append(current)
    return pieces


def split_evidence(body: str) -> list:
    """Splits the box text from its evidence at the first dash-and-kind that is not
    inside backticks: a box may quote the grammar it asks for (`fixed — test: ...`)."""
    for match in EVIDENCE_SPLIT.finditer(body):
        if body.count("`", 0, match.start()) % 2 == 0:
            return [body[:match.start()], body[match.end():]]
    return [body]


def parse_box(line_no: int, ticked: bool, body: str) -> Box:
    parts = split_evidence(body)
    text = parts[0].strip()
    evidence = []
    if len(parts) == 2:
        kind = None
        for piece in split_outside_brackets(parts[1], ";"):
            item = EVIDENCE_ITEM.match(piece)
            if item:
                kind = item.group(1)
                pointer = item.group(2).strip()
            elif kind == "needs-human" and evidence:
                # a judgement is prose and may hold a semicolon of its own
                evidence[-1] = (kind, evidence[-1][1] + ";" + piece.rstrip())
                continue
            else:
                pointer = piece.strip()
            if kind and (pointer or item):
                evidence.append((kind, pointer))
    return Box(line_no, ticked, text, evidence)


def parse_blockers(raw: str, tickets: dict):
    """Returns (ticket numbers, numbers named that are not tickets)."""
    text = re.sub(r"\([^)]*\)", " ", raw or "")
    if not text.strip() or re.match(r"^\s*(none|nothing|-)\b", text, re.I):
        return [], []
    numbers = set()
    for low, high in RANGE_RE.findall(text):
        for n in range(int(low), int(high) + 1):
            if n in tickets:
                numbers.add(n)
    text = RANGE_RE.sub(" ", text)
    unknown = []
    for found in re.findall(r"\b\d{1,3}\b", text):
        n = int(found)
        if n in tickets:
            numbers.add(n)
        else:
            unknown.append(found)
    return sorted(numbers), unknown


class Feature:
    def __init__(self, root: str, config: dict, name: str):
        self.root = root
        self.config = config
        self.name = name
        self.dir = os.path.join(root, tracker_dir(config), name)
        self.legacy = name in config.get("legacy_features", [])
        self.tickets = {}
        self.problems = []
        issues = os.path.join(self.dir, "issues")
        if not os.path.isdir(issues):
            raise SystemExit(refusal("tickets-exist", "no tickets at %s" % os.path.relpath(issues, root), "ticket files under that folder"))
        for filename in sorted(os.listdir(issues)):
            if not filename.endswith(".md"):
                continue
            ticket = Ticket(os.path.join(issues, filename))
            if ticket.number < 0:
                self.problems.append("%s: file name does not start with a ticket number" % filename)
                continue
            if ticket.number in self.tickets:
                self.problems.append("%s: ticket number %s is used twice" % (filename, ticket.label))
                continue
            self.tickets[ticket.number] = ticket
        self.blockers = {}
        for number, ticket in self.tickets.items():
            blocking, unknown = parse_blockers(ticket.blocked_raw, self.tickets)
            self.blockers[number] = [b for b in blocking if b != number]
            for missing in unknown:
                self.problems.append("%s: blocked by %s, which is not a ticket of this feature" % (ticket.label, missing))
            if not ticket.status:
                self.problems.append("%s: no Status line" % ticket.label)

        for cycle in self._cycles():
            self.problems.append("blocking cycle: %s" % " -> ".join(self.tickets[n].label for n in cycle))

    def _cycles(self) -> list:
        found = []
        state = {}

        def visit(number: int, path: list) -> None:
            state[number] = "open"
            for blocker in self.blockers.get(number, []):
                if state.get(blocker) == "open":
                    found.append(path[path.index(blocker):] + [blocker] if blocker in path else [number, blocker, number])
                elif blocker not in state:
                    visit(blocker, path + [blocker])
            state[number] = "closed"

        for number in sorted(self.tickets):
            if number not in state:
                visit(number, [number])
        return found

    def open_blockers(self, number: int) -> list:
        return [b for b in self.blockers[number] if self.tickets[b].status not in TERMINAL]

    def get(self, label: str) -> Ticket:
        try:
            return self.tickets[int(label)]
        except (KeyError, ValueError):
            raise SystemExit(refusal("known-ticket", "no ticket %s in %s" % (label, self.name), "a ticket number of %s" % self.name))


def list_features(root: str, config: dict) -> list:
    tracker = os.path.join(root, tracker_dir(config))
    if not os.path.isdir(tracker):
        return []
    return sorted(d for d in os.listdir(tracker) if os.path.isdir(os.path.join(tracker, d, "issues")))


def short(text: str, limit: int = 160) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit - 1] + "\u2026"


def table_cells(line: str) -> list:
    """The cells of one Markdown table row; `\\|` is a pipe inside a cell, not a separator."""
    return [c.replace("\\|", "|").strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def set_status(path: str, word: str) -> None:
    """Rewrite the first `Status:` line above `## Comments` (bold or plain) to the given word."""
    lines = read(path).split("\n")
    for index, line in enumerate(lines):
        if re.match(r"^##\s+Comments\b", line, re.I):
            break
        found = re.match(r"^(\**)Status:(\**)\s*.*$", line)
        if found:
            lines[index] = "%sStatus:%s %s" % (found.group(1), found.group(2), word)
            break
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
