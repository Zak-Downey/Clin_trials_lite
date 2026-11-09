"""The after-the-fact audit: the build log and the git history against the loop's rules (`gate.py audit`)."""
from __future__ import annotations

import fnmatch
import glob
import os
import re
import time

from gate.config import allowed, read
from gate.evidence import box_counts, parse_review
from gate.git import integration_ref, owns_merge, read_stamp, rule_in_force, run_git, run_text
from gate.log import ABORT_WORDS, LOG_TIME, is_follow_up, log_path, parse_log_time, read_log
from gate.release import SPEC_PATH_RE, user_facing
from gate.tracker import Feature, HEADER_RE, REVIEWED_KINDS, table_cells, tracker_dir


def record_paths_ok(path: str, tracker: str) -> bool:
    return (fnmatch.fnmatch(path, "docs/agents/local/*.jsonl") and path.count("/") == 3
            or path in ("docs/agents/local/ledger.md", "docs/agents/local/rules.md", "docs/agents/local/github-storage.json")
            or path.startswith(tracker + "/"))


def feature_numbers(feature: Feature) -> dict:
    """What the feature's review files say: reviews, blocking, notes, mutants tried and survived."""
    counts = {"reviews": 0, "blocking": 0, "notes": 0, "mutants_tried": 0, "mutants_survived": 0}
    for path in sorted(glob.glob(os.path.join(feature.dir, "reviews", "*.md"))):
        if not re.match(r"^\d+\.md$", os.path.basename(path)):
            continue
        text = read(path)
        counts["reviews"] += 1
        _, findings = parse_review(text)
        counts["blocking"] += len([f for f in findings if f.section == "blocking"])
        counts["notes"] += len([f for f in findings if f.section == "notes"])
        found = re.search(r"Mutation sample:\s*(\d+)\s+tried,\s*(\d+)\s+caught", text, re.I)
        if found:
            counts["mutants_tried"] += int(found.group(1))
            counts["mutants_survived"] += int(found.group(1)) - int(found.group(2))
    return counts


def guard_refusals(root: str) -> int:
    common = run_git(root, "rev-parse", "--git-common-dir")
    if common and not os.path.isabs(common):
        common = os.path.join(root, common)
    path = os.path.join(common or root, "factory", "guard.log")
    return len([l for l in read(path).split("\n") if l.strip()]) if os.path.isfile(path) else 0


MERGE_SUBJECT_RE = re.compile(r"^Merge ticket (\d+)\b")
REPORT_HASH_RE = re.compile(r"(?<![0-9A-Za-z])[0-9a-f]{7,40}(?![0-9A-Za-z])")
CLOSED_WORDS = ("fixed", "unreachable")


def log_epoch(text: str):
    """A log time as epoch seconds; a minute-only time (the first `gate.py merge` form) is its first second."""
    return parse_log_time(text)


def build_range(root: str, config: dict, ref: str, feature: Feature) -> list:
    """The `git log` arguments that limit the integration line to this feature's own commits: those after the one
    that added its spec.md. A feature whose spec has no such commit is limited to what the protected branches lack."""
    rel = os.path.relpath(os.path.join(feature.dir, "spec.md"), root)
    added = (run_git(root, "log", "--first-parent", "--diff-filter=A", "--format=%H", ref, "--", rel) or "").split("\n")
    added = [a for a in added if a]
    if added:
        return [ref, "^%s" % added[-1]]
    return [ref] + ["^%s" % b for b in config.get("protected_branches", []) if run_git(root, "rev-parse", "--verify", "-q", "refs/heads/%s^{commit}" % b)]


def integration_merges(root: str, feature: Feature, limit: list) -> list:
    """(number, commit, parents, epoch, subject) of every `Merge ticket NN` on the integration line that is the ticket's own in `feature`, oldest first."""
    out = run_git(root, "log", "--first-parent", "--reverse", "--format=%H%x09%ct%x09%P%x09%s", *limit) or ""
    found = []
    for line in out.split("\n"):
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        commit, epoch, parents, subject = parts[0], parts[1], parts[2].split(), "\t".join(parts[3:])
        match = MERGE_SUBJECT_RE.match(subject)
        if match and len(parents) == 2 and owns_merge(root, commit, match.group(1).zfill(2), feature, " follow-up:" in subject):
            found.append((match.group(1).zfill(2), commit, parents, int(epoch), subject))
    return found


def first_parent_commits(root: str, limit: list) -> list:
    """(commit, epoch, parent count) of every commit on the integration line, oldest first."""
    out = run_git(root, "log", "--first-parent", "--reverse", "--format=%H%x09%ct%x09%P", *limit) or ""
    found = []
    for line in out.split("\n"):
        parts = line.split("\t")
        if len(parts) >= 3:
            found.append((parts[0], int(parts[1]), len(parts[2].split())))
    return found


def returned_to_triage(root: str, ref: str, ticket: Ticket) -> bool:
    """Whether the ticket's Status went back to needs-triage after it had been anything else."""
    rel = os.path.relpath(ticket.path, root)
    seen_other = False
    for commit in (run_git(root, "log", "--reverse", "--format=%H", ref, "--", rel) or "").split("\n"):
        if not commit:
            continue
        text = run_git(root, "show", "%s:%s" % (commit, rel)) or ""
        status = None
        for line in text.split("\n"):
            if re.match(r"^##\s+Comments\b", line, re.I):
                break
            found = HEADER_RE["status"].match(line)
            if found:
                status = re.sub(r"[^a-z-]", "", found.group(1).strip().split(" ")[0].lower())
                break
        if status == "needs-triage" and seen_other:
            return True
        if status and status != "needs-triage":
            seen_other = True
    return False


def grammar_era(root: str, feature_name: str):
    """The time the log's grammar began: its first ISO line (no `- ` prefix, as `gate.py log` writes), but only
    when dash-prefixed prose came before it. A log that was ISO from its first line has no era to excuse anything."""
    path = log_path(root, feature_name)
    if not path or not os.path.isfile(path):
        return None
    prose = False
    for line in read(path).split("\n"):
        if re.match(r"^-\s+\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}", line):
            prose = True
            continue
        found = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?)\s", line)
        if found:
            return parse_log_time(found.group(1)) if prose else None
    return None


def attempt_resumes(entries: list, label: str) -> list:
    """The `resume NN implementer` lines that are attempts. A resume after a reviewer's report or an aborted merge
    is a round of the loop (orchestrator.md#audit); only one that follows the implementer's own report is a second try."""
    found = []
    last = None
    for entry in entries:
        if entry["verb"] not in ("dispatch", "report", "resume", "merge-end") or entry["args"][0] != label:
            continue
        verb, args = entry["verb"], entry["args"]
        if verb == "report":
            last = "report" if args[1] == "implementer" else "round" if args[1] == "ticket-reviewer" else last
        elif verb == "merge-end":
            last = "round" if args[1] in ABORT_WORDS else last
        elif verb == "resume" and args[1] == "implementer":
            if last == "report":
                found.append(entry)
            last = None
        elif verb == "dispatch" and args[1] == "implementer":
            last = None
    return found


def release_epoch(root: str, ref: str, feature: Feature):
    """The commit time of the first commit on the integration line whose spec reads `Status: ready-for-agent`."""
    rel = os.path.relpath(os.path.join(feature.dir, "spec.md"), root)
    out = run_git(root, "log", "--first-parent", "--reverse", "--format=%H%x09%ct", ref, "--", rel) or ""
    for line in out.split("\n"):
        commit, _, epoch = line.partition("\t")
        if not commit:
            continue
        text = run_git(root, "show", "%s:%s" % (commit, rel)) or ""
        status = re.search(r"^\**Status:\**\s*`?([A-Za-z-]+)", text, re.M)
        if status and status.group(1).lower() != "needs-triage":
            return int(epoch)
    return None


def computed_measures(features: list) -> dict:
    """What the gate can count from the tracker, the log and the guard log, for the report to be checked against."""
    tickets = [t for f in features for t in f.tickets.values()]
    boxes = box_counts(tickets)
    root = features[0].root
    numbers = {"reviews": 0, "blocking": 0, "notes": 0, "mutants_tried": 0, "mutants_survived": 0}
    for feature in features:
        for key, value in feature_numbers(feature).items():
            numbers[key] += value
    numbers.update({
        "tickets": len(tickets),
        "tickets_done": len([t for t in tickets if t.status == "done"]),
        "tickets_user": len([t for t in tickets if t.status == "ready-for-human"]),
        "boxes_proved": boxes["proved"],
        "boxes_human": boxes["human"],
        "guard_refusals": guard_refusals(root),
        "subagents": sum(len([e for e in read_log(root, f.name) if e["verb"] == "dispatch"]) for f in features),
    })
    return numbers


def measure_key(label: str):
    """Which computed number a report's table label names, or None when the gate does not count it."""
    words = label.lower()
    if "mutant" in words:
        return "mutants_survived" if "surviv" in words else "mutants_tried"
    if "blocking" in words:
        return "blocking"
    if "review" in words:
        return "reviews"
    if "note" in words:
        return "notes"
    if "proved" in words:
        return "boxes_proved"
    if "box" in words and re.search(r"person|human|judge", words):
        return "boxes_human"
    if "guard" in words:
        return "guard_refusals"
    if "subagent" in words:
        return "subagents"
    if "ticket" in words:
        return "tickets_done" if "done" in words else "tickets"
    return None


def report_table_rows(text: str) -> list:
    """(label, value cell) of each row of every `| Measure | Value |` table in the report."""
    rows = []
    lines = text.split("\n")
    at = 0
    while at < len(lines):
        cells = [c.lower() for c in table_cells(lines[at])] if lines[at].lstrip().startswith("|") else []
        if cells[:2] == ["measure", "value"]:
            at += 1
            while at < len(lines) and lines[at].lstrip().startswith("|"):
                row = table_cells(lines[at])
                if len(row) >= 2 and not re.match(r"^[\s:-]*$", row[0] + row[1]):
                    rows.append((row[0], row[1]))
                at += 1
        else:
            at += 1
    return rows


class Audit:
    """Each rule of the loop as one printed line: `ok`, a violation, or `expected and did not find`. A line the
    rule needs that the log does not hold is never read as compliance. Lines for events that happened before the
    grammar began (before the log's first `dispatch` line) are printed and not counted."""

    def __init__(self, root: str, config: dict, names: list, report=None):
        self.root, self.config, self.names, self.report = root, config, names, report
        self.violations = 0
        self.legacy = 0

    def say(self, rule: str, text: str = "") -> None:
        print("ok: %s%s" % (rule, ": " + text if text else ""))

    def bad(self, rule: str, text: str) -> None:
        self.violations += 1
        print("violation: %s: %s" % (rule, text))

    def missing(self, rule: str, line: str, era, when) -> None:
        if era is not None and when is not None and when < era:
            self.legacy += 1
            print("expected and did not find: %s: %s (before the log grammar began; not counted)" % (rule, line))
        else:
            self.violations += 1
            print("expected and did not find: %s: %s" % (rule, line))

    def run(self) -> int:
        features = []
        for name in self.names:
            feature = Feature(self.root, self.config, name)
            features.append(feature)
            self.feature(feature)
        self.stamps()
        if self.report:
            self.report_rules(features)
        if self.violations:
            print("AUDIT: %d violation(s)%s" % (self.violations, ", %d expected line(s) from before the grammar not counted" % self.legacy if self.legacy else ""))
            return 1
        print("AUDIT: clean%s" % (" (%d expected line(s) from before the grammar not counted)" % self.legacy if self.legacy else ""))
        return 0

    def feature(self, feature: Feature) -> None:
        root, config = self.root, self.config
        name = feature.name
        ref = integration_ref(root, name)
        entries = read_log(root, name)
        dispatches = [e for e in entries if e["verb"] == "dispatch"]
        era = grammar_era(root, name)
        if ref:
            limit = build_range(root, config, ref, feature)
            merges = integration_merges(root, feature, limit)
        else:
            print("ok: %s: merge commits: skipped, there is no integration branch feature/%s to read them from" % (name, name))
            limit, merges, ref = [], [], "HEAD"
        merged_at = {}
        merged_parents = {}
        for number, commit, parents, epoch, subject in merges:
            merged_at.setdefault(number, epoch)
            merged_parents.setdefault(number, parents)

        # Every merge commit: a log pair; a review file before it on its branch when the ticket's Kind is one a
        # ticket-reviewer reads (REVIEWED_KINDS); and every review that does exist has its blocking findings closed.
        rule = "%s: merge reviews and log pairs" % name
        before = self.violations + self.legacy
        for number, commit, parents, epoch, subject in merges:
            where = "merge %s (ticket %s)" % (commit[:7], number)
            ticket = next((t for t in feature.tickets.values() if t.label == number), None)
            if ticket is None:
                self.bad(rule, "%s is not a ticket of %s" % (where, name))
                continue
            rel = "%s/%s/reviews/%s.md" % (tracker_dir(config), name, number)
            texts = {}
            if re.match(r"^Merge ticket \d+ follow-up:", subject) and rule_in_force(root, commit, "follow-up"):
                # A follow-up merge expects its own review file, `NN-followup.md` or `NN-followup-<n>.md`, on its branch.
                folder = os.path.dirname(rel)
                listed = (run_git(root, "ls-tree", "--name-only", parents[1], folder + "/") or "").split("\n")
                for path in sorted(l for l in listed if re.match(r"^%s/%s-followup(?:-\d+)?\.md$" % (re.escape(folder), re.escape(number)), l)):
                    texts[path] = run_git(root, "show", "%s:%s" % (parents[1], path))
                rel = "%s/%s-followup.md (or %s-followup-<n>.md)" % (folder, number, number)
            else:
                texts[rel] = run_git(root, "show", "%s:%s" % (parents[1], rel))
            texts = {k: v for k, v in texts.items() if v is not None}
            if not texts and ticket.kind in REVIEWED_KINDS:
                self.bad(rule, "%s has no %s on its branch before it (a `Kind: %s` ticket is reviewed before it merges)" % (where, rel, ticket.kind))
            for text in texts.values():
                _, findings = parse_review(text)
                for finding in findings:
                    word = re.match(r"^\s*([A-Za-z-]+)", finding.status)
                    word = word.group(1).lower() if word else ""
                    if finding.section == "blocking" and word not in CLOSED_WORDS:
                        self.bad(rule, "%s: %s was not closed (status `%s`)" % (where, finding.name(), finding.status or "none"))
            end = next((i for i, e in enumerate(entries) if e["verb"] == "merge-end" and e["args"][0] == number
                        and len(e["args"][1]) >= 7 and commit.startswith(e["args"][1])), None)
            start = next((i for i in range(end, -1, -1) if entries[i]["verb"] == "merge-start" and entries[i]["args"][0] == number), None) if end is not None else None
            if end is None:
                self.missing(rule, "merge-end %s %s" % (number, commit[:7]), era, epoch)
            elif start is None:
                self.missing(rule, "merge-start %s before its merge-end" % number, era, epoch)
        if self.violations + self.legacy == before:
            self.say(rule, "%d merge commit(s) read" % len(merges))

        # Merges did not overlap; nothing landed in the integration worktree while one was open.
        rule = "%s: merges did not overlap" % name
        before = self.violations
        open_merge = None
        windows = []
        aborted = {}
        for at, entry in enumerate(entries):
            if entry["verb"] != "merge-abort":
                continue
            number, when = entry["args"][0], entry["args"][1]
            found = next((i for i in range(at) if entries[i]["verb"] == "merge-start" and entries[i]["args"][0] == number and entries[i]["time"] == when), None)
            if found is None:
                self.bad(rule, "merge-abort %s %s names no merge-start %s at that time" % (number, when, number))
                continue
            later = next((i for i in range(found + 1, len(entries)) if entries[i]["verb"] == "merge-start"), len(entries))
            if any(entries[i]["verb"] == "merge-end" and entries[i]["args"][0] == number for i in range(found + 1, later)):
                self.bad(rule, "merge-abort %s %s names a merge-start that was ended by a merge-end before the next merge-start" % (number, when))
                continue
            aborted[found] = " ".join(entry["args"][2:]).strip('"')
        for at, entry in enumerate(entries):
            if at in aborted:
                continue
            if entry["verb"] == "merge-start":
                if open_merge:
                    self.bad(rule, "merge-start %s at %s while the merge of %s (started %s) had no merge-end" % (entry["args"][0], entry["time"], open_merge["args"][0], open_merge["time"]))
                open_merge = entry
            elif entry["verb"] == "merge-end":
                if open_merge and open_merge["args"][0] == entry["args"][0]:
                    windows.append((open_merge, entry))
                    open_merge = None
                elif not open_merge:
                    self.bad(rule, "merge-end %s at %s has no merge-start open" % (entry["args"][0], entry["time"]))
        if open_merge:
            self.bad(rule, "merge-start %s at %s has no merge-end (a merge still open, or the merger died)" % (open_merge["args"][0], open_merge["time"]))
        if self.violations == before:
            self.say(rule, "; ".join("merge-start %s %s aborted (logged later): %s" % (entries[i]["args"][0], entries[i]["time"], reason) for i, reason in sorted(aborted.items())))
        rule = "%s: no commit landed during a merge" % name
        before = self.violations
        commits = first_parent_commits(root, limit) if limit else []
        for start, end in windows:
            low, high = log_epoch(start["time"]), log_epoch(end["time"])
            if low is None or high is None:
                continue
            if start["time"].count(":") < 2:
                low += 59
            # The merge's own first parent was in place before the merge began (a clean tree is required), so a
            # commit in the same second as merge-start is not a commit during it. One made later is.
            own_parents = {parents[0] for number, commit, parents, epoch, subject in merges if number == start["args"][0]}
            for commit, epoch, parent_count in commits:
                if commit in own_parents and epoch <= low:
                    continue
                if parent_count < 2 and low <= epoch <= high:
                    self.bad(rule, "commit %s (at %s) landed between merge-start %s %s and merge-end %s %s" % (
                        commit[:7], time.strftime(LOG_TIME, time.localtime(epoch)), start["args"][0], start["time"], end["args"][0], end["time"]))
        if self.violations == before:
            self.say(rule)

        # Dispatch once; a second attempt is a resume; a third went back through needs-triage.
        rule = "%s: dispatched once" % name
        before = self.violations + self.legacy
        branches = [b.split("/", 1)[1] for b in (run_git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads/ticket/") or "").split("\n") if "/" in b]
        for number, ticket in sorted(feature.tickets.items()):
            has_branch = any(ticket.stem == b or ticket.stem.startswith(b + "-") or b.startswith(ticket.stem + "--") for b in branches if re.match(r"^\d+-", b))
            if not has_branch and ticket.label not in merged_at:
                continue
            ours = [e for e in dispatches if e["args"][0] == ticket.label and e["args"][1] == "implementer" and not is_follow_up(e)]
            follow_ups = [e for e in dispatches if e["args"][0] == ticket.label and e["args"][1] == "implementer" and is_follow_up(e)]
            resumes = attempt_resumes(entries, ticket.label)
            if not ours:
                # The dispatch happened before the ticket's first commit, not at its merge.
                parents = merged_parents.get(ticket.label)
                firsts = (run_git(root, "log", "--format=%ct", "%s..%s" % (parents[0], parents[1])) or "").split() if parents else []
                self.missing(rule, "dispatch %s implementer" % ticket.label, era, min(int(c) for c in firsts) if firsts else merged_at.get(ticket.label))
                continue
            if len(ours) > 1:
                self.bad(rule, "ticket %s has %d dispatch lines for its implementer: a second attempt is `resume %s implementer`" % (ticket.label, len(ours), ticket.label))
            attempts = len(ours) + len(resumes) + len(follow_ups)
            if attempts >= 3 and not returned_to_triage(root, ref, ticket):
                self.bad(rule, "ticket %s was attempted %d times (1 dispatch, %d resume, %d follow-up) and its Status never went back to needs-triage (an attempt is a dispatch plus any `resume %s implementer` after the implementer's own report; a resume after a reviewer's report or a merge abort is a round; a follow-up dispatch is an attempt because it is an escape past the review)" % (ticket.label, attempts, len(resumes), len(follow_ups), ticket.label))
        if self.violations + self.legacy == before:
            self.say(rule)

        # The foundational ticket's read precedes the dispatch of what it blocks.
        rule = "%s: foundation read before dependents" % name
        before = self.violations + self.legacy
        for number, ticket in sorted(feature.tickets.items()):
            if ticket.kind != "foundational":
                continue
            dependents = [n for n, blockers in feature.blockers.items() if number in blockers]
            first = next((i for i, e in enumerate(entries) if e["verb"] == "dispatch" and int(e["args"][0]) in dependents), None)
            read_at = next((i for i, e in enumerate(entries) if e["verb"] == "foundation-read" and e["args"][0] == ticket.label), None)
            if first is None:
                continue
            if read_at is None:
                self.missing(rule, "foundation-read %s (before the dispatch of ticket %s)" % (ticket.label, entries[first]["args"][0]), era, merged_at.get(ticket.label))
            elif read_at > first:
                self.bad(rule, "foundation-read %s at %s is after the dispatch of ticket %s at %s" % (ticket.label, entries[read_at]["time"], entries[first]["args"][0], entries[first]["time"]))
        if self.violations + self.legacy == before:
            self.say(rule)

        # A user-facing spec: the exploration and acceptance-walk tickets were dispatched and reported.
        rule = "%s: exploration and acceptance walk run" % name
        before = self.violations + self.legacy
        spec = read(os.path.join(feature.dir, "spec.md"))
        paths = set(SPEC_PATH_RE.findall(spec))
        for ticket in feature.tickets.values():
            paths.update(ticket.touches)
        if any(user_facing(config, p) for p in paths):
            for kind in ("acceptance-walk", "exploration"):
                for number, ticket in sorted(feature.tickets.items()):
                    if ticket.kind != kind:
                        continue
                    for verb in ("dispatch", "report"):
                        if not any(e["verb"] == verb and e["args"][0] == ticket.label for e in entries):
                            self.missing(rule, "%s %s (the %s ticket)" % (verb, ticket.label, kind), era, merged_at.get(ticket.label))
        else:
            self.say(rule, "not applicable (the spec touches no user-facing path)")
            before = -1
        if before != -1 and self.violations + self.legacy == before:
            self.say(rule)

        # spec-against-brief precedes the release.
        rule = "%s: spec against brief before release" % name
        if re.search(r"^\**Brief:\**", spec, re.M):
            released = release_epoch(root, ref, feature)
            read_line = next((e for e in entries if e["verb"] == "spec-against-brief"), None)
            if released is None:
                self.say(rule, "not applicable (not released)")
            elif read_line is None:
                self.missing(rule, "spec-against-brief", era, released)
            elif (log_epoch(read_line["time"]) or 0) > released:
                self.bad(rule, "spec-against-brief at %s is after the release commit (%s)" % (read_line["time"], time.strftime(LOG_TIME, time.localtime(released))))
            else:
                self.say(rule)
        else:
            self.say(rule, "not applicable (the spec has no Brief: line)")

        # A merged design ticket has an Open list item logged by `open` before its merge.
        rule = "%s: design decisions logged" % name
        before = self.violations + self.legacy
        opens = [e for e in entries if e["verb"] == "open"]
        decided = [e for e in entries if e["verb"] == "decided"]
        notes = []
        designs = [t for t in feature.tickets.values() if t.kind == "design" and t.label in merged_at]
        for entry in decided:
            if not designs:
                self.bad(rule, "decided %s %s: the feature has no merged Kind: design ticket" % (entry["args"][0], entry["args"][1][:7]))
            elif not any(self.decided_commit(feature, t, entry, merges) for t in designs):
                self.bad(rule, "decided %s %s %s" % (entry["args"][0], entry["args"][1][:7], self.decided_why(feature, designs[0], entry, merges)))
        for number, ticket in sorted(feature.tickets.items()):
            if ticket.kind != "design" or ticket.label not in merged_at:
                continue
            named = [e for e in opens if ticket.stem in e["text"] or re.search(r"\bticket\s+0*%d\b" % ticket.number, e["text"], re.I)]
            if any((log_epoch(e["time"]) or 0) <= merged_at[ticket.label] for e in named):
                continue
            late = next((c for c in (self.decided_commit(feature, ticket, e, merges) for e in decided) if c), None)
            if late:
                notes.append("ticket %s decided in %s (logged later)" % (ticket.label, late[:7]))
            else:
                self.missing(rule, "open <n> \"...ticket %s...\" before the merge of ticket %s" % (ticket.label, ticket.label), era, merged_at[ticket.label])
        if self.violations + self.legacy == before:
            self.say(rule, "; ".join(notes))

    def decided_why(self, feature, ticket, entry, merges) -> str:
        """Why `decided <n> <commit>` does not stand for the ticket, or "" when it does."""
        root, number, commit = self.root, entry["args"][0], entry["args"][1]
        full = run_git(root, "rev-parse", "--verify", "-q", "%s^{commit}" % commit)
        if not full:
            return "is not a commit here"
        merge = next((m[1] for m in merges if m[0] == ticket.label), None)
        if not merge or run_git(root, "merge-base", "--is-ancestor", full, merge) is None:
            return "is not an ancestor of the merge of ticket %s" % ticket.label
        rel = "%s/%s/spec.md" % (tracker_dir(self.config), feature.name)
        if rel not in (run_git(root, "show", "--name-only", "--format=", full) or "").split("\n"):
            return "does not change the spec"
        text = run_git(root, "show", "%s:%s" % (full, rel)) or ""
        heading = re.search(r"^##\s+Open list\b.*$", text, re.M | re.I)
        body = re.split(r"^##\s", text[heading.end():], maxsplit=1, flags=re.M)[0] if heading else ""
        item = re.search(r"^%d\.\s.*(?:\n(?![0-9]+\.\s).*)*" % int(number), body, re.M)
        if not item or not re.search(r"\bticket\s+0*%d\b" % ticket.number, item.group(0), re.I):
            return "item %s does not name ticket %s in the Open list at that commit" % (number, ticket.label)
        return ""

    def decided_commit(self, feature, ticket, entry, merges):
        return entry["args"][1] if not self.decided_why(feature, ticket, entry, merges) else None

    def stamps(self) -> None:
        rule = "stamps"
        stamp = read_stamp(self.root)
        if not stamp:
            self.missing(rule, "the built-tip stamp (`gate.py ready %s` writes it)" % " ".join(self.names), None, None)
            return
        wanted = ", ".join(self.names)
        if stamp[1] != wanted:
            self.bad(rule, "the stamp is for %s, not %s: run `gate.py ready %s`" % (stamp[1] or "no feature", wanted, " ".join(self.names)))
            return
        head = run_git(self.root, "rev-parse", "HEAD")
        if stamp[0] != head and not self.records_pending(stamp, head):
            self.bad(rule, "the stamp is at %s, HEAD is %s: commits after the stamp need a new `ready`" % (stamp[0][:7], (head or "?")[:7]))
            return
        built = stamp[3] or stamp[0]
        if run_git(self.root, "rev-parse", "--verify", "-q", "%s^{commit}" % built) is None:
            self.bad(rule, "the stamped built tip %s is not a commit here" % built[:7])
        elif stamp[3]:
            parents = (run_git(self.root, "rev-list", "--parents", "-n1", stamp[0]) or "").split()[1:]
            if parents != [built]:
                self.bad(rule, "the records stamp %s has parent %s, not the built tip %s" % (stamp[0][:7], ", ".join(p[:7] for p in parents) or "none", built[:7]))
            else:
                self.say(rule, "built tip %s stamped; records stamp %s is its child" % (built[:7], stamp[0][:7]))
        else:
            self.say(rule, "built tip %s stamped (no records stamp yet)" % built[:7])

    def records_pending(self, stamp, head) -> bool:
        """`ready --records` audits the close commit before it writes the records stamp: the built-tip stamp is
        then the close commit's parent, a report is being audited, and the commit touches record paths alone (as `ready --records` requires)."""
        parents = (run_git(self.root, "rev-list", "--parents", "-n1", "HEAD") or "").split()[1:]
        if not (self.report and not stamp[3] and parents == [stamp[0]]):
            return False
        changed = (run_git(self.root, "diff", "--name-only", "--no-renames", "%s..HEAD" % stamp[0]) or "").split("\n")
        return all(record_paths_ok(n, tracker_dir(self.config)) for n in changed if n)

    def report_rules(self, features: list) -> None:
        root = self.root
        text = read(self.report)
        rule = "report %s" % os.path.relpath(self.report, root)
        before = self.violations
        stamp = read_stamp(root)
        if stamp and stamp[1] != ", ".join(self.names):
            stamp = None  # another feature's stamp; `stamps` has named it
        built = (stamp[3] or stamp[0]) if stamp else None
        named = re.search(r"Built tip:\s*`?([0-9a-f]{7,40})", text, re.I)
        if not named:
            self.bad(rule, "names no built tip (the Facts block's `Built tip:` line)")
        elif built and not built.startswith(named.group(1)):
            self.bad(rule, "names built tip %s, but the built-tip stamp is %s" % (named.group(1)[:7], built[:7]))
        seen = set()
        unallowed = "\n".join(l for l in text.split("\n") if not allowed(l))
        for found in REPORT_HASH_RE.finditer(unallowed):
            short = found.group(0)
            if short in seen or not re.search(r"\d", short):
                continue
            seen.add(short)
            commit = run_git(root, "rev-parse", "--verify", "-q", "%s^{commit}" % short)
            if commit is None:
                self.bad(rule, "names %s, which is not a commit here (a hash quoted from another repo goes on a line carrying `factory-allow: <why>`)" % short)
            elif run_text(root, "merge-base", "--is-ancestor", commit, "HEAD")[0] != 0:
                self.bad(rule, "names %s, which is not on this branch" % short)
        counts = computed_measures(features)
        rows = list(report_table_rows(text))
        for line in text.split("\n"):
            bullet = re.match(r"^\s*[-*]\s+(Tickets|Boxes):\s*(.*)$", line)
            if not bullet:
                continue
            if bullet.group(1) == "Tickets":
                parts = re.match(r"^(\d+) done of (\d+)(?: \((\d+) for the user\))?", bullet.group(2))
                said = [("Tickets: done", parts.group(1), "tickets_done"), ("Tickets: of", parts.group(2), "tickets"), ("Tickets: for the user", parts.group(3), "tickets_user")] if parts else []
            else:
                parts = re.match(r"^(\d+) proved, (\d+) for a person", bullet.group(2))
                said = [("Boxes: proved", parts.group(1), "boxes_proved"), ("Boxes: for a person", parts.group(2), "boxes_human")] if parts else []
            for label, value, key in said:
                if value is not None and int(value) != counts[key]:
                    self.bad(rule, "`%s` says %s, the gate computes %d" % (label, value, counts[key]))
        for label, cell in rows:
            key = measure_key(label)
            number = re.search(r"\d+", cell)
            if key is None or not number:
                continue
            if int(number.group(0)) != counts[key]:
                self.bad(rule, "`%s` says %s, the gate computes %d" % (label, number.group(0), counts[key]))
        if self.violations == before:
            self.say(rule)


def cmd_audit(root: str, config: dict, names: list, report=None) -> int:
    """Prints one line per rule of the loop and returns 1 when the build broke one. `report` is a report file to check too."""
    return Audit(root, config, names, report).run()
