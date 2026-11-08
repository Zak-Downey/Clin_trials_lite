"""Evidence: resolving a box's pointers, the red-run and review audits, and the ticket and boxes commands."""
from __future__ import annotations

import ast
import os
import re

from gate.config import read, red_marker_regex
from gate.git import branch_head, integration_ref, merge_commit_for, newest_merge_commit_for, rule_in_force, run_git
from gate.log import review_wave_checklist
from gate.mutate import mutant_problems
from gate.refuse import refuse
from gate.release import design_mark_problems
from gate.tracker import PROOF_KINDS, tracker_dir


_JS_TITLE = re.compile(r"\b(?:test|it|describe)(?:\.\w+)*\(\s*(['\"`])(.*?)\1")


def test_titles(path: str, text: str) -> str:
    """The titles a test file declares: a Python test's docstring first line, or
    the first string of a JS test( / it( / describe( call. Fixture prose, negative
    examples and comments in the file are not titles and are not returned."""
    titles = []
    if path.endswith(".py"):
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError):
            return ""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                doc = ast.get_docstring(node)
                if doc:
                    titles.append(doc.split("\n")[0].strip())
    else:
        titles = [m.group(2) for m in _JS_TITLE.finditer(text)]
    return "\n".join(titles)


class Resolver:
    """Finds test and walk titles in the folders the config names. A `test:`
    title is looked up among the files' declared titles only; a `walk:` title
    in the whole text of the walk folder."""

    def __init__(self, root: str, config: dict):
        self.root = root
        self.config = config
        self._texts = {}

    def _text(self, kind: str) -> str:
        if kind not in self._texts:
            chunks = []
            for folder in self.config.get("evidence", {}).get(kind, []):
                base = os.path.join(self.root, folder)
                for directory, subdirs, files in os.walk(base):
                    subdirs[:] = [d for d in subdirs if d not in ("node_modules", ".git", "__pycache__")]  # factory-allow: skips installed dependencies
                    for filename in files:
                        path = os.path.join(directory, filename)
                        try:
                            if os.path.getsize(path) < 2000000:
                                text = read(path)
                                chunks.append(test_titles(path, text) if kind == "test" else text)
                        except OSError:
                            pass
            self._texts[kind] = "\n".join(chunks)
        return self._texts[kind]

    def problem(self, kind: str, pointer: str):
        """None if the pointer resolves, else what is wrong with it."""
        needle = pointer.strip().strip("`'\"").strip()
        needle = re.sub(r"(\.\.\.|…)$", "", needle).strip()
        if not needle and kind in PROOF_KINDS:
            return "%s evidence is empty" % kind
        if kind in ("test", "walk"):
            if not self.config.get("evidence", {}).get(kind):
                return None  # this repo names no folder to look in
            bare = re.sub(r"\s*\([^()]*\)\s*$", "", needle).strip()  # without a closing aside in brackets
            haystack = self._text(kind)
            if kind == "test":
                haystack = haystack.lower()
            for candidate in (needle, bare):
                if kind == "test":
                    candidate = candidate.lower()
                if len(candidate) >= 3 and candidate in haystack:
                    return None
            if len(bare) < 3:
                return "%s title is too short to find" % kind
            return "no %s titled `%s`" % (kind, bare)
        if kind == "doc":
            path = needle.split("#")[0].split(" ")[0]
            return None if os.path.exists(os.path.join(self.root, path)) else "no file `%s`" % path
        if kind == "check":
            names = [c.get("name") for c in self.config.get("checks", [])]
            return None if needle.split(" ")[0] in names else "no check named `%s` in factory.json" % needle
        return None


class BaseResolver(Resolver):
    """The same lookup over the files as they stand at a git ref (the integration tip)."""

    def __init__(self, root: str, config: dict, ref: str):
        super().__init__(root, config)
        self.ref = ref

    def _text(self, kind: str) -> str:
        if kind not in self._texts:
            chunks = []
            for folder in self.config.get("evidence", {}).get(kind, []):
                names = run_git(self.root, "ls-tree", "-r", "--name-only", self.ref, "--", folder) or ""
                for name in names.split("\n"):
                    if not name or any(part in ("node_modules", "__pycache__") for part in name.split("/")):  # factory-allow: skips installed dependencies
                        continue
                    text = run_git(self.root, "show", "%s:%s" % (self.ref, name))
                    if text is not None and len(text) < 2000000:
                        chunks.append(test_titles(name, text) if kind == "test" else text)
            self._texts[kind] = "\n".join(chunks)
        return self._texts[kind]


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def has_anchor(text: str, anchor: str) -> bool:
    """A heading whose slug is the anchor, or a line starting with the anchor's text."""
    wanted = slug(anchor)
    spaced = anchor.lower().replace("-", " ").strip()
    for line in text.split("\n"):
        bare = re.sub(r"^[\s#>*_`-]+", "", line).lower()
        if line.lstrip().startswith("#") and slug(line) == wanted:
            return True
        if wanted and (bare.startswith(anchor.lower()) or bare.startswith(spaced) or slug(bare).startswith(wanted + "-") or slug(bare) == wanted):
            return True
    return False


class RedAudit:
    """What is new on the ticket's branch against the integration tip needs proof it can fail:
    a new `test:`/`walk:` title carries a `red:` run, and a `doc:` names something that was not there."""

    def __init__(self, feature: Feature, ticket: Ticket, resolver: Resolver):
        self.feature, self.ticket, self.resolver = feature, ticket, resolver
        self.root = feature.root
        self.base = integration_ref(self.root, feature.name)
        self.head = branch_head(self.root)
        self.merged = False
        self.era = self.head
        protected = feature.config.get("protected_branches", [])
        first = merge_commit_for(self.root, self.base, ticket.label, self.feature, protected) if self.base and ticket.status.strip().lower() == "done" else None
        if first:
            # A done ticket is judged as it stood at its newest merge, first or follow-up, from the first merge's base:
            # the first merge's doc: files are still new, and a follow-up's red runs are on the branch. A follow-up
            # still staged (MERGE_HEAD) is the newest merge and is judged in full, not as an old one.
            parent = run_git(self.root, "rev-parse", "%s^1" % first)
            staged = self.head != "HEAD"
            # A HEAD that is not on the integration line is a follow-up branch (cut from its tip, in a worktree):
            # judged as a staged follow-up is, from the first merge's base to HEAD, not as merged.
            on_branch = not staged and not self.git_ok("merge-base", "--is-ancestor", "HEAD", self.base)
            newest = self.head if staged else "HEAD" if on_branch else newest_merge_commit_for(self.root, self.base, ticket.label, self.feature, protected)
            if parent and newest:
                self.base, self.head, self.merged, self.era = parent, newest, not (staged or on_branch), first
        self.old = BaseResolver(self.root, resolver.config, self.base) if self.base else None
        self.red_dir = "%s/%s/red/" % (tracker_dir(feature.config), feature.name)
        self.problems = []

    def git_ok(self, *args) -> bool:
        return run_git(self.root, *args) is not None

    def is_new(self, kind: str, pointer: str) -> bool:
        return self.resolver.problem(kind, pointer) is None and self.old.problem(kind, pointer) is not None

    def passing_commit(self, kind: str, pointer: str) -> str:
        """The first commit on the branch holding the title: the commit at which the check passes."""
        needle = re.sub(r"\s*\([^()]*\)\s*$", "", pointer.strip().strip("`'\"")).strip()
        folders = self.resolver.config.get("evidence", {}).get(kind, [])
        commits = (run_git(self.root, "log", "--reverse", "--format=%H", "%s..%s" % (self.base, self.head)) or "").split()
        for commit in commits:
            if self.git_ok("grep", "-q", "-i", "-F", "-e", needle, commit, "--", *folders):
                return commit
        return run_git(self.root, "rev-parse", self.head) or ""

    def red_text(self, where: str, pointer: str):
        """(text, tip commit) of a cited run file, or None after a problem is recorded."""
        path = os.path.normpath(pointer.strip().strip("`")).replace(os.sep, "/")
        if "/" not in pointer.strip():
            path = self.red_dir + path
        if not path.startswith(self.red_dir):
            self.problems.append("%s: `red: %s` is not under %s" % (where, pointer.strip(), self.red_dir))
            return None
        full = os.path.join(self.root, path)
        if not os.path.isfile(full):
            self.problems.append("%s: run file `%s` does not exist" % (where, path))
            return None
        text = read(full)
        first = TIP_LINE.match(text.split("\n")[0]) if text.strip() else None
        if not first:
            self.problems.append("%s: the first line of `%s` must record the tip it was run at (`# tip <hash>`)" % (where, path))
            return None
        tip = run_git(self.root, "rev-parse", "--verify", "-q", "%s^{commit}" % first.group(1))
        if not tip:
            self.problems.append("%s: tip %s in `%s` is not a commit of this repository" % (where, first.group(1), path))
            return None
        if not self.git_ok("merge-base", "--is-ancestor", tip, self.head):
            self.problems.append("%s: `%s` was run at %s, which is not on this branch" % (where, path, first.group(1)))
            return None
        return text, tip

    def box(self, box: Box, where: str, short: str) -> None:
        reds = [p for k, p in box.evidence if k == "red"]
        runs = []
        for pointer in reds:
            got = self.red_text(where, pointer)
            if got:
                runs.append((pointer, got[0], got[1]))
        for kind, pointer in box.proof():
            if kind == "doc":
                self.doc(where, pointer)
            elif kind in ("test", "walk") and self.is_new(kind, pointer):
                self.new_check(kind, pointer, reds, runs, where)

    def new_check(self, kind: str, pointer: str, reds: list, runs: list, where: str) -> None:
        if not reds:
            self.problems.append("%s: `%s: %s` is new on this branch and has no `red:` file showing it fail (docs/agents/evidence.md#red)" % (where, kind, pointer))
            return
        markers = red_markers(self.resolver.config, kind)
        shown = [(p, t, tip) for p, t, tip in runs if shows_failing(t, pointer, markers, kind)]
        if not shown:
            if runs:
                self.problems.append("%s: the `red:` file does not show `%s` failing (its title beside one of: %s)" % (where, pointer, marker_text(markers)))
            return
        passing = self.passing_commit(kind, pointer)
        for p, t, tip in shown:
            if tip != passing and self.git_ok("merge-base", "--is-ancestor", tip, passing):
                return
        self.problems.append("%s: every `red:` run of `%s` was made after the check passed: its tip is the commit that made it pass (%s) or later; a red run is made before it" % (where, pointer, passing[:7]))

    def branch_text(self, path: str) -> str:
        """The doc as the branch has it: at the merge commit for a done ticket (a later edit on the integration
        branch is not the ticket's), else in the working tree (the branch, or a staged merge)."""
        if self.merged:
            return run_git(self.root, "show", "%s:%s" % (self.head, path)) or ""
        return read(os.path.join(self.root, path))

    def doc(self, where: str, pointer: str) -> None:
        if self.resolver.problem("doc", pointer):
            return  # audit_ticket reports a missing file
        needle = pointer.strip().strip("`'\"").strip()
        path, _, anchor = needle.partition("#")
        path = path.split(" ")[0]
        rule = "doc must be able to fail (docs/agents/evidence.md#red)"
        existed = run_git(self.root, "show", "%s:%s" % (self.base, path))
        if existed is None:
            return
        if not anchor:
            self.problems.append("%s: `doc: %s` is a file that already existed at the integration tip and names no new anchor: %s" % (where, path, rule))
            return
        anchor = anchor.split(" ")[0]
        if has_anchor(existed, anchor):
            self.problems.append("%s: `doc: %s#%s` names an anchor that already existed at the integration tip: %s" % (where, path, anchor, rule))
        elif not has_anchor(self.branch_text(path), anchor):
            self.problems.append("%s: `doc: %s#%s` names an anchor the file does not have: %s" % (where, path, anchor, rule))

    def in_force(self) -> bool:
        """A ticket merged before this audit existed is not judged by it: the audit must be in the gate it merged with."""
        return rule_in_force(self.root, self.era, "red-audit")

    def run(self) -> list:
        if not self.base or (self.merged and not self.in_force()):
            return []
        for box in self.ticket.boxes:
            if not box.ticked:
                continue
            where = "%s:%d" % (os.path.relpath(self.ticket.path, self.root), box.line_no)
            self.box(box, where, box.text[:70])
        return self.problems


def audit_ticket(ticket: Ticket, resolver: Resolver) -> list:
    """Problems that stop a ticket being done."""
    found = []
    if not ticket.boxes:
        found.append("%s: no acceptance boxes" % ticket.label)
    for box in ticket.boxes:
        where = "%s:%d" % (os.path.relpath(ticket.path, resolver.root), box.line_no)
        short = box.text[:70] + ("..." if len(box.text) > 70 else "")
        state = box.state()
        if state == "open":
            found.append("%s open box (no evidence, not needs-human): %s" % (where, short))
        elif state == "unproved":
            found.append("%s ticked without evidence: %s" % (where, short))
        for kind, pointer in box.proof():
            problem = resolver.problem(kind, pointer)
            if problem:
                found.append("%s evidence does not resolve (%s): %s" % (where, problem, short))
    return found


def box_counts(tickets: list) -> dict:
    counts = {"proved": 0, "human": 0, "open": 0, "unproved": 0}
    for ticket in tickets:
        for box in ticket.boxes:
            counts[box.state()] += 1
    return counts


DASH = r"(?:\u2014|\u2013|--|-)"
TIP_LINE = re.compile(r"^#\s*tip\s+([0-9a-f]{7,40})\b(.*)$", re.I)


class Finding:
    def __init__(self, section: str, number: int, body: str, status: str):
        self.section = section  # "blocking" or "notes"
        self.number = number
        self.body = body
        self.status = status

    def name(self) -> str:
        return ("blocking finding %d" if self.section == "blocking" else "note %d") % self.number


def parse_review(text: str):
    """Returns (tip, findings). A finding is a numbered or bulleted line under
    `## Blocking` or `## Notes`; its status is what follows the last ` | `."""
    tip = None
    found = re.search(r"Tip reviewed:\s*`?([0-9a-f]{7,40})\b", text, re.I)
    if found:
        tip = found.group(1)
    findings = []
    section = None
    counts = {}
    for line in text.split("\n"):
        heading = re.match(r"^##\s+(.*?)\s*$", line)
        if heading:
            name = heading.group(1).lower()
            section = "blocking" if name.startswith("blocking") else "notes" if name.startswith("notes") else None
            continue
        item = re.match(r"^\s*(?:(\d+)[.)]|[-*])\s+(.*)$", line)
        if section and item:
            counts[section] = counts.get(section, 0) + 1
            number = int(item.group(1)) if item.group(1) else counts[section]
            body, bar, status = item.group(2).rpartition("|")
            findings.append(Finding(section, number, (body if bar else item.group(2)).strip(), status.strip() if bar else ""))
    return tip, findings


def ticket_engines(ticket: Ticket, resolver: Resolver) -> list:
    """The engines the ticket's walks run under: the names in `browser` options and
    in the lists a walk loops over. A ticket with no walk covers one engine."""
    engines = []
    folders = resolver.config.get("evidence", {}).get("walk", [])
    for kind, pointer in [e for box in ticket.boxes for e in box.proof()]:
        if kind != "walk":
            continue
        needle = re.sub(r"\s*\([^()]*\)\s*$", "", pointer.strip().strip("`'\"")).strip().lower()
        for folder in folders:
            for directory, _, files in os.walk(os.path.join(resolver.root, folder)):
                for filename in files:
                    try:
                        text = read(os.path.join(directory, filename))
                    except OSError:
                        continue
                    if len(needle) < 3 or needle not in text.lower():
                        continue
                    for line in text.split("\n"):
                        if "browser" in line:
                            engines += re.findall(r"['\"](chromium|webkit|firefox)['\"]", line)  # factory-allow: the engine names a walk file spells
    unique = sorted(set(engines))
    return unique or ["chromium"]  # factory-allow: the engine a walk runs in when it names none


def red_markers(config: dict, kind: str) -> list:
    """The red marker of every check that proves `kind`, each compiled as config compiles it."""
    found = [red_marker_regex(c) for c in config.get("checks", []) if kind in c.get("proves", []) and c.get("red_marker")]
    return found or [red_marker_regex({})]


def marker_text(markers: list) -> str:
    return ", ".join(m.pattern for m in markers)


def shows_failing(text: str, title: str, markers: list, kind: str) -> bool:
    """The title sits beside a failure marker: on the same line, or on the line after
    a line that starts with one (unittest prints `FAIL: name`, then the docstring)."""
    needle = re.sub(r"\s*\([^()]*\)\s*$", "", title.strip().strip("`'\"")).strip().lower()
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if needle not in line.lower():
            continue
        if any(m.search(line) for m in markers):
            return True
        before = lines[index - 1] if index else ""
        if any(m.match(before.lstrip()) for m in markers) and not re.match(r"\s*(ok|not ok|\u2714|\u2716)", line):
            return True
    return False


class ReviewAudit:
    def __init__(self, feature: Feature, ticket: Ticket, resolver: Resolver):
        self.feature, self.ticket, self.resolver = feature, ticket, resolver
        self.root = feature.root
        self.red_dir = "%s/%s/red/" % (tracker_dir(feature.config), feature.name)
        self.problems = []
        self.tip = None
        self.blocking = False

    def commit(self, name: str):
        return run_git(self.root, "rev-parse", "--verify", "%s^{commit}" % name) if re.match(r"^[0-9a-f]{7,40}$", name, re.I) else None

    def ancestor(self, older: str, newer: str) -> bool:
        return run_git(self.root, "merge-base", "--is-ancestor", older, newer) is not None

    def red_file(self, finding: Finding, pointer: str, engines=None):
        """The text of a committed run file under red/, or None after a problem is recorded."""
        path = pointer.strip().strip("`")
        where = finding.name()
        if "/" not in path:
            path = self.red_dir + path
        norm = os.path.normpath(path).replace(os.sep, "/")
        if not norm.startswith(self.red_dir):
            self.problems.append("%s: `%s` is not under %s" % (where, pointer, self.red_dir))
            return None
        full = os.path.join(self.root, norm)
        if not os.path.isfile(full):
            self.problems.append("%s: run file `%s` does not exist" % (where, norm))
            return None
        text = read(full)
        if not text.strip():
            self.problems.append("%s: run file `%s` is empty" % (where, norm))
            return None
        first = TIP_LINE.match(text.split("\n")[0])
        if not first:
            self.problems.append("%s: the first line of `%s` must record the tip it was run at (`# tip <hash>`)" % (where, norm))
            return None
        if engines and not any(re.search(r"\b%s\b" % re.escape(e), first.group(2)) for e in engines):
            self.problems.append("%s: the first line of `%s` does not name the engine (%s)" % (where, norm, ", ".join(engines)))
            return None
        recorded = self.commit(first.group(1))
        if not recorded:
            self.problems.append("%s: tip %s in `%s` is not a commit of this repository" % (where, first.group(1), norm))
            return None
        reviewed = self.commit(self.tip) if self.tip else None
        if not reviewed:
            self.problems.append("%s: the review names no tip (`Tip reviewed: <hash>`) to compare `%s` with" % (where, norm))
            return None
        if not self.ancestor(recorded, reviewed):
            self.problems.append("%s: `%s` was run at %s, after the review tip %s" % (where, norm, first.group(1), self.tip))
            return None
        if not self.ancestor(recorded, branch_head(self.root)):
            self.problems.append("%s: `%s` was run at %s, which is not on this branch" % (where, norm, first.group(1)))
            return None
        return text

    def fixed(self, finding: Finding) -> None:
        where = finding.name()
        match = re.match(r"^fixed\s*%s\s*(test|walk|doc)\s*:\s*(.*)$" % DASH, finding.status, re.I | re.S)
        if not match:
            self.problems.append("%s is marked fixed with no check: write `fixed \u2014 test: <title> \u2014 red: <file>`" % where)
            return
        kind = match.group(1).lower()
        rest = re.split(r"\s%s\s+red\s*:\s*" % DASH, match.group(2), maxsplit=1)
        pointer = rest[0].strip()
        if kind == "doc":
            problem = self.resolver.problem("doc", pointer)
            if problem:
                self.problems.append("%s is marked fixed by a document, but %s" % (where, problem))
            return
        problem = self.resolver.problem(kind, pointer)
        if problem:
            self.problems.append("%s is marked fixed with a check that does not resolve (%s)" % (where, problem))
            return
        if len(rest) < 2 or not rest[1].strip():
            self.problems.append("%s is marked fixed by `%s: %s` with no `red:` file showing it fail at the review tip" % (where, kind, pointer))
            return
        text = self.red_file(finding, rest[1])
        if text is not None and not shows_failing(text, pointer, red_markers(self.resolver.config, kind), kind):
            self.problems.append("%s: `%s` does not show `%s` failing (its title beside one of: %s)" % (
                where, rest[1].strip(), pointer, marker_text(red_markers(self.resolver.config, kind))))

    def unreachable(self, finding: Finding, engines: list) -> None:
        where = finding.name()
        runs = [r.strip() for r in re.findall(r"run\s*:\s*([^;]+)", finding.status)]
        label = "%d engines (%s)" % (len(engines), ", ".join(engines)) if len(engines) > 1 else "1 engine"
        if len(runs) < len(engines):
            self.problems.append("%s is marked unreachable: the ticket covers %s but names %d run file(s), one `run:` per engine" % (where, label, len(runs)))
            return
        words = " ".join(re.sub(r"[`*_]", "", finding.body).split()[:3]).lower()
        named = set()
        before = len(self.problems)
        for pointer in runs:
            text = self.red_file(finding, pointer, engines if len(engines) > 1 else None)
            if text is None:
                continue
            lines = text.split("\n")
            body = " ".join("\n".join(lines[1:]).split()).lower()
            if words not in body:
                self.problems.append("%s: `%s` does not name the finding's own step (%s)" % (where, pointer, words))
            else:
                named.update(e for e in engines if re.search(r"\b%s\b" % e, lines[0]))
        if len(engines) > 1 and len(self.problems) == before:
            for engine in engines:
                if engine not in named:
                    self.problems.append("%s names no %s run" % (where, engine))

    def run(self) -> list:
        """The ticket's review, and each follow-up review (`NN-followup.md`, `NN-followup-<n>.md`) beside it."""
        folder = os.path.join(self.feature.dir, "reviews")
        names = ["%s.md" % self.ticket.label] + sorted(n for n in (os.listdir(folder) if os.path.isdir(folder) else [])
                                                      if re.match(r"^%s-followup(?:-\d+)?\.md$" % re.escape(self.ticket.label), n))
        printed = False
        for name in names:
            if os.path.isfile(os.path.join(folder, name)):
                self.read_one(os.path.join(folder, name))
                printed = True
        if printed and not self.problems and not self.blocking:
            print("review: no blocking findings")
        return ["review %s: %s" % (self.ticket.label, p) for p in self.problems]

    def read_one(self, path: str) -> None:
        self.tip, findings = parse_review(read(path))
        self.blocking = self.blocking or any(f.section == "blocking" for f in findings)
        engines = None
        for finding in findings:
            status = finding.status
            word = re.match(r"^\s*([A-Za-z-]+)", status)
            word = word.group(1).lower() if word else ""
            if word == "open":
                if finding.section == "blocking":
                    self.problems.append("%s is still open" % finding.name())
            elif word == "fixed":
                self.fixed(finding)
            elif word == "left":
                if finding.section == "blocking":
                    self.problems.append("%s is marked left: a blocking finding is fixed or shown unreachable, never left" % finding.name())
                elif not re.sub(r"^left\s*:?\s*", "", status, flags=re.I).strip():
                    self.problems.append("%s is marked left with no reason" % finding.name())
            elif word == "unreachable":
                engines = engines or ticket_engines(self.ticket, self.resolver)
                self.unreachable(finding, engines)
            else:
                self.problems.append("%s ends with no status: end the line with `| open`, `| fixed \u2014 ...`, `| left: ...` or `| unreachable \u2014 ...`" % finding.name())


def cmd_boxes(feature: Feature, resolver: Resolver, only=None) -> int:
    if only:
        tickets = [feature.get(only)]
        users = []
    else:
        everything = [feature.tickets[n] for n in sorted(feature.tickets)]
        # ready-for-human tickets are the user's own: their boxes are theirs to tick
        users = [t for t in everything if t.status == "ready-for-human"]
        tickets = [t for t in everything if t.status not in ("ready-for-human", "wontfix")]
    by_ticket = [(ticket, audit_ticket(ticket, resolver)) for ticket in tickets]
    problems = [p for _, found in by_ticket for p in found]
    counts = box_counts(tickets)
    print("boxes in %s%s: %d proved, %d for a person to judge, %d open, %d ticked without evidence" % (
        feature.name, " ticket " + tickets[0].label if only else "", counts["proved"], counts["human"], counts["open"], counts["unproved"]))
    for ticket, _ in by_ticket:
        mine = box_counts([ticket])
        print("  ticket %s: %d proved, %d for a person to judge, %d open, %d ticked without evidence" % (
            ticket.label, mine["proved"], mine["human"], mine["open"], mine["unproved"]))
    if users:
        print("not audited (the user's own tickets): %s" % ", ".join(t.label for t in users))
    if feature.legacy and not only:
        for ticket, found in by_ticket:
            if found:
                print("legacy: ticket %s has %d problem(s); `gate.py boxes %s %s` lists them" % (ticket.label, len(found), feature.name, ticket.label))
        if problems:
            print("(%s is listed under legacy_features in factory.json: reported, not failed)" % feature.name)
        return 0
    for problem in problems[:40]:
        print(problem)
    if len(problems) > 40:
        print("... and %d more; audit one ticket at a time: gate.py boxes %s <NN>" % (len(problems) - 40, feature.name))
    if feature.legacy and problems:
        print("(%s is listed under legacy_features in factory.json: reported, not failed)" % feature.name)
        return 0
    if not problems and not only and not counts["open"] and not counts["unproved"]:
        for line in review_wave_checklist(feature.name, tracker_dir(feature.config)):
            print(line)
    return 1 if problems else 0


def follow_up_review_path(feature: Feature, ticket: Ticket) -> str:
    """The review file a follow-up of this ticket writes: `NN-followup.md`, then `NN-followup-2.md`, and on."""
    folder = os.path.join(feature.dir, "reviews")
    have = [n for n in (os.listdir(folder) if os.path.isdir(folder) else []) if re.match(r"^%s-followup(?:-\d+)?\.md$" % re.escape(ticket.label), n)]
    name = "%s-followup.md" % ticket.label if not have else "%s-followup-%d.md" % (ticket.label, len(have) + 1)
    return "%s/%s/reviews/%s" % (tracker_dir(feature.config), feature.name, name)


def cmd_ticket(feature: Feature, resolver: Resolver, label: str) -> int:
    ticket = feature.get(label)
    problems = audit_ticket(ticket, resolver)
    problems += ReviewAudit(feature, ticket, resolver).run()
    red = RedAudit(feature, ticket, resolver)
    problems += red.run()
    if ticket.status.strip().lower() == "done":
        print("a follow-up's review file: %s" % follow_up_review_path(feature, ticket))
    problems += design_mark_problems(feature, ticket, red)
    problems += mutant_problems(feature, ticket, red)
    waiting = feature.open_blockers(ticket.number)
    if waiting:
        problems.append("%s: blocked by %s, not yet done" % (ticket.label, ", ".join(feature.tickets[b].label for b in waiting)))
    for problem in problems:
        print(problem)
    if problems:
        return refuse("ticket-gate", "ticket %s may NOT be marked done: %d problem(s), listed above" % (ticket.label, len(problems)), "each problem fixed, then gate.py ticket %s %s again" % (feature.name, ticket.label))
    counts = box_counts([ticket])
    print("ticket %s may be marked done: %d boxes proved, %d for a person to judge" % (ticket.label, counts["proved"], counts["human"]))
    return 0
