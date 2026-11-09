"""The ready gate, its records stamp, the hand-over checklist and `close`."""
from __future__ import annotations

import contextlib
import glob
import io
import json
import os
import re
import time

from gate import audit as audit_module
from gate.audit import feature_numbers, guard_refusals, record_paths_ok
from gate.checks import cmd_lint, run_checks
from gate.config import LEDGER_PATH, read
from gate.dashboard import cmd_dashboard, count_flakes, feature_names, output_path
from gate.pricing import KINDS, number, priced_cost, read_prices
from gate.records import read_records
from gate.evidence import audit_ticket, box_counts
from gate.github import REMOTE, cmd_github
from gate.git import read_stamp, run_git, stamp_path
from gate.ledger import ledger_check, ledger_escape_rows
from gate.refuse import refuse
from gate.log import close_out_checklist, log_times, parse_log_time, read_log
from gate.tokens import TOKENS_PATH, write_tokens
from gate.tracker import short, table_cells, tracker_dir


FLAKES_PATH = os.path.join("docs", "agents", "local", "flakes.jsonl")

FLAKE_LIMIT = 3

def fixed_in_re(tracker: str):
    """A ticket (`ticket 07`) or a bug spec folder (`<tracker>/<slug>/`, not a file inside one) in the ledger row's last cell."""
    return re.compile(r"\bticket\s+\d{1,3}\b|(?<![\w./-])%s/[\w-]+/?(?=[\s,;)`.]|$)" % re.escape(tracker), re.I)


def flake_resolved(root: str, title: str, tracker: str) -> bool:
    ledger = os.path.join(root, LEDGER_PATH)
    if not os.path.isfile(ledger):
        return False
    for row in read(ledger).split("\n"):
        if row.lstrip().startswith("|") and title in row:
            cells = table_cells(row)
            if fixed_in_re(tracker).search(cells[-1]):
                return True
    return False


def record_flakes(root: str, names: str, head, flakes: list, tracker: str) -> list:
    """Append each flake of this run to the tracked flakes file, print the count per title, and
    return a problem for a title at three that no ledger row ties to a ticket or bug spec."""
    if not flakes:
        return []
    path = os.path.join(root, FLAKES_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        for file, title in flakes:
            handle.write(json.dumps({"date": time.strftime("%Y-%m-%d"), "feature": names, "file": file, "title": title, "tip": head or ""}, ensure_ascii=False) + "\n")
    counts = {}
    for entry in read_records(path)[0]:
        counts[entry.get("title")] = counts.get(entry.get("title"), 0) + 1
    problems = []
    for file, title in dict.fromkeys(flakes):
        print("flake: %s \u203a %s has flaked %d time(s) in %s (commit it)" % (file, title, counts.get(title, 0), FLAKES_PATH))
        if counts.get(title, 0) >= FLAKE_LIMIT and not flake_resolved(root, title, tracker):
            problems.append("walk %s \u203a %s has flaked %d times and no ledger row naming that title has a ticket (`ticket NN`) or a bug spec folder (`%s/<slug>/`) in its last cell: write the ticket or the bug spec, then add it to the ledger row (%s). UNRESOLVED alone is not enough" % (file, title, counts[title], tracker, LEDGER_PATH))
    return problems


def cmd_ready(features: list, resolver: Resolver) -> int:
    root, config = features[0].root, features[0].config
    names = ", ".join(f.name for f in features)
    problems = []
    dirty = run_git(root, "status", "--porcelain")
    if dirty is None:
        problems.append("not a git repository")
    elif dirty:
        problems.append("working tree is not clean (%d path(s)): commit first, the gate stamps a commit" % len(dirty.split("\n")))
    for feature in features:
        tag = "%s " % feature.name if len(features) > 1 else ""
        problems += [tag + p for p in feature.problems]
        box_problems = []
        for number in sorted(feature.tickets):
            ticket = feature.tickets[number]
            if ticket.status in ("wontfix", "ready-for-human"):
                continue  # ready-for-human is the user's own ticket: it goes in the hand-over
            if ticket.status != "done":
                problems.append("%sticket %s is %s, not done" % (tag, ticket.label, ticket.status or "without a status"))
                continue
            waiting = feature.open_blockers(number)
            if waiting:
                problems.append("%sticket %s is done but its blocker %s is not" % (tag, ticket.label, ", ".join(feature.tickets[b].label for b in waiting)))
            box_problems += audit_ticket(ticket, resolver)
        if feature.legacy:
            for problem in box_problems:
                print("legacy (reported, not failed): %s" % problem)
        else:
            problems += box_problems
    problems += ["lint: " + p for p in cmd_lint(root, config)]
    problems += ["ledger: " + p for p in ledger_check(root)]
    if problems:
        for problem in problems:
            print(problem)
        return refuse("ready-problems", "%d problem(s) are listed above and the checks were not run" % len(problems), "each problem fixed, then ready again")
    flakes = []
    failures = run_checks(root, config, flakes=flakes)
    head = run_git(root, "rev-parse", "HEAD")
    failures += record_flakes(root, names, head, flakes, tracker_dir(config))
    if failures:
        for failure in failures:
            print(failure)
        return refuse("ready-checks", "a check is red (above)" if any(f.startswith("check ") for f in failures) else "a walk has flaked three times (above)", "every check green and no walk flaking, then ready again")
    path = stamp_path(root)
    if not head or not path:
        return refuse("ready-stamp", "the tip could not be stamped", "a commit checked out in a git repository")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("%s\n%s\n%s\n" % (head, names, time.strftime("%Y-%m-%dT%H:%M:%S")))
    counts = box_counts([t for f in features for t in f.tickets.values()])
    print("READY: %s at %s. %d boxes proved, %d for a person to judge. `gh pr ready` will now pass for this tip." % (names, head[:7], counts["proved"], counts["human"]))
    left = ["%s %s" % (f.name, t.label) for f in features for t in f.tickets.values() if t.status == "ready-for-human"]
    if left:
        print("Left to the user (ready-for-human), not checked here: %s" % ", ".join(left))
    print("Next: python3 .claude/factory/gate.py handover %s" % " ".join(f.name for f in features))
    for line in close_out_checklist([f.name for f in features], head, tracker_dir(config)):
        print(line)
    return 0


def unchecked_standins(root: str, config: dict) -> list:
    path = os.path.join(root, config.get("standins_doc", ""))
    if not os.path.isfile(path):
        return []
    rows = []
    in_section = False
    for line in read(path).split("\n"):
        if line.startswith("#"):
            in_section = "stand-in" in line.lower()
            continue
        if not in_section or not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or set(cells[0]) <= set("-: ") or cells[0].lower().startswith("stand-in"):
            continue
        if cells[2].lower().startswith("none"):
            rows.append("%s (stands in for: %s). %s" % (cells[0], cells[1], cells[2]))
    return rows


RULE_QUEUE_PATH = os.path.join("docs", "agents", "local", "rules.md")


def todo_walks(root: str, config: dict) -> list:
    """(title, file) of each walk declared with a `todo` option: the nearest `walk('title'` above it."""
    found = []
    for folder in config.get("evidence", {}).get("walk", []):
        for path in sorted(glob.glob(os.path.join(root, folder, "**", "*.js"), recursive=True)):
            text = read(path)
            for match in re.finditer(r"\btodo\s*:", text):
                starts = list(re.finditer(r"^\s*walk\(\s*(['\"`])(.+?)\1", text[:match.start()], re.M))
                if starts:
                    found.append((starts[-1].group(2), os.path.relpath(path, root)))
    return found


def open_list_items(spec_text: str) -> list:
    """The items of a spec's `## Open list`: each item's full text (first line, then continuations)."""
    if "## Open list" not in spec_text:
        return []
    body = spec_text.split("## Open list", 1)[1].split("\n", 1)[-1]
    body = re.split(r"^#{1,6}\s", body, maxsplit=1, flags=re.M)[0]
    items = []
    for line in body.split("\n"):
        if re.match(r"^\d+\.\s", line):
            items.append(line)
        elif items and line.strip():
            items[-1] += "\n" + line
    return items


def brief_numbers(text: str) -> set:
    """The brief items a line cites: `brief finding 8`, `brief findings 16 and 6`, `brief findings 7 (rule bloat) and 11`, `brief 26`."""
    one = r"\d+(?:\s*\([^()]*\))?"
    found = set()
    for match in re.finditer(r"\bbrief(?:\s+findings?)?\s+(%s(?:\s*(?:,\s*and|,|and)\s*%s)*)" % (one, one), text, re.I):
        found.update(int(n) for n in re.findall(r"(?<![\w(])\d+", re.sub(r"\([^()]*\)", "", match.group(1))))
    return found


def brief_items(feature: Feature):
    """([(number, leading bold phrase)], path) of the brief the spec's `Brief:` line names, or None."""
    spec = read(os.path.join(feature.dir, "spec.md"))
    line = re.search(r"^\**Brief:\**(.*)$", spec, re.M)
    if not line:
        return None
    named = re.search(r"`([^`]+)`", line.group(1))
    path = os.path.join(feature.dir, named.group(1) if named else "brief.md")
    if not os.path.isfile(path):
        return [], path
    items = [(int(m.group(1)), m.group(2).strip()) for m in re.finditer(r"^(\d+)\.\s+\*\*(.+?)\*\*", read(path), re.M)]
    return items, path


def design_decisions(features: list) -> list:
    """(feature, ticket, Open list item) for each merged `Kind: design` ticket of a review-fix feature."""
    found = []
    for feature in features:
        if not feature.name.endswith("-review"):
            continue
        items = open_list_items(read(os.path.join(feature.dir, "spec.md")))
        for number in sorted(feature.tickets):
            ticket = feature.tickets[number]
            if ticket.kind != "design" or ticket.status != "done":
                continue
            named = [i for i in items if ticket.stem in i or re.search(r"\bticket\s+0*%d\b" % ticket.number, i, re.I)]
            found.append((feature, ticket, named[0].split("\n")[0] if named else None))
    return found


def rule_queue(root: str) -> list:
    """(id, rule, escape ids) of each queue row not adopted and not retired; [] when the file is absent."""
    path = os.path.join(root, RULE_QUEUE_PATH)
    if not os.path.isfile(path):
        return []
    header = None
    rows = []
    empty = ("", "-", "none", "no", "n/a")
    for line in read(path).split("\n"):
        if not line.strip().startswith("|"):
            continue
        cells = table_cells(line)
        if set("".join(cells)) <= set("-: "):
            continue
        lower = [c.lower() for c in cells]
        if header is None:
            if lower and lower[0] == "id":
                header = lower
            continue

        def cell(prefix):
            for i, name in enumerate(header):
                if name.startswith(prefix) and i < len(cells):
                    return cells[i]
            return ""
        if cell("adopted").lower() in empty and cell("retired").lower() in empty:
            rows.append((cells[0], cell("rule"), cell("escape")))
    return rows


def cmd_handover(features: list) -> int:
    root = features[0].root
    several = len(features) > 1
    print("# Hand-over: %s" % ", ".join(f.name for f in features))
    stamp = read_stamp(root)
    print()
    if stamp:
        wanted = ", ".join(f.name for f in features)
        print("Tips: built %s, stamped %s%s%s." % ((stamp[3] or "(not recorded)")[:7], stamp[0][:7],
              "" if stamp[0] == run_git(root, "rev-parse", "HEAD") else "; HEAD has moved since, so the stamp no longer matches",
              "" if stamp[1] == wanted else "; the stamp names %s, not %s" % (stamp[1] or "no feature", wanted)))
    else:
        print("Tips: no ready stamp in this worktree.")
    page = output_path(root, None)
    if page:
        print()
        print("Dashboard: %s" % page)
    decisions = design_decisions(features)
    print()
    print("## Merged design decisions (%d)" % len(decisions))
    print()
    print("These changed what the user sees and merged during the build.")
    print()
    for feature, ticket, item in decisions:
        print("- **%s %s** %s" % (feature.name, ticket.label, ticket.title))
        print("  - Open list: %s" % (short(item) if item else "none (the Open list does not name it)"))
    if not decisions:
        print("None.")
    print()
    print("Everything an agent could check is green. What is left is yours.")
    judged = []
    own = []
    for feature in features:
        for number in sorted(feature.tickets):
            ticket = feature.tickets[number]
            if ticket.status == "wontfix":
                continue
            if ticket.status == "ready-for-human":
                own.append(ticket)
                continue
            for box in ticket.boxes:
                for what in box.judgement():
                    judged.append((feature, ticket, box, what))
    print()
    print("## To judge (%d)" % len(judged))
    print()
    for feature, ticket, box, what in judged:
        label = "%s %s" % (feature.name, ticket.label) if several else ticket.label
        print("- **%s, %s** %s" % (label, "checked, judgement left" if box.ticked else "not checkable by an agent", what))
        print("  - Box: %s" % box.text)
    if not judged:
        print("Nothing.")
    print()
    print("## Your tickets (%d)" % len(own))
    print()
    for ticket in own:
        print("- **%s** (`%s`)" % (ticket.title, os.path.relpath(ticket.path, root)))
        for box in ticket.boxes:
            print("  - [%s] %s" % ("x" if box.ticked else " ", box.text))
    if not own:
        print("None.")
    gaps = unchecked_standins(root, features[0].config)
    print()
    print("## Stand-ins nothing checks (%d)" % len(gaps))
    print()
    print("Every green above was earned against these stand-ins, and nothing confirms they still behave like the real thing.")
    print()
    for gap in gaps:
        print("- %s" % gap)
    if not gaps:
        print("None listed.")
    walks = todo_walks(root, features[0].config)
    rows = ledger_escape_rows(root)
    unresolved_any = [r for r in rows if any("UNRESOLVED" in c for c in r)]
    open_defects = unresolved_any
    print()
    print("## Open defects (%d)" % len(open_defects))
    print()
    print("Every ledger escape row containing UNRESOLVED. A row whose last cell names a ticket or bug spec is marked, so a fixed row that still mentions the word is visible as such.")
    print()
    for row in open_defects:
        shown = [title for title, _ in walks if any(title in c for c in row)]
        print("- %s: %s" % (row[0], short(row[2])))
        print("  - Walk: %s" % (", ".join(shown) if shown else "no todo walk carries it"))
        fix = fixed_in_re(tracker_dir(features[0].config)).search(row[-1])
        if fix:
            print("  - The row's last cell names %s: it may be fixed; judge whether UNRESOLVED still holds" % fix.group(0))
    if not open_defects:
        print("None.")
    print()
    print("## Todo walks (%d)" % len(walks))
    print()
    for title, file in walks:
        tied = [r for r in unresolved_any if any(title in c for c in r)]
        print("- %s (%s): %s" % (title, file, "tied to the ledger row of %s" % tied[0][0] if tied else "UNTIED (the walk runner fails on this)"))
    if not walks:
        print("None.")
    lists = []
    for feature in features:
        spec = os.path.join(feature.dir, "spec.md")
        if os.path.isfile(spec):
            items = open_list_items(read(spec))
            if items:
                lists.append((os.path.relpath(spec, root), items))
    print()
    print("## Open list (%d)" % sum(len(i) for _, i in lists))
    print()
    for path, items in lists:
        print("- %s (%d)" % (path, len(items)))
        for item in items:
            print("  - %s" % short(item.split("\n")[0]))
    if not lists:
        print("None.")
    queue = rule_queue(root)
    print()
    print("## Proposed rules (%d)" % len(queue))
    print()
    if not os.path.isfile(os.path.join(root, RULE_QUEUE_PATH)):
        print("There is no rule queue file (%s) yet: zero rows." % RULE_QUEUE_PATH)
    for rid, rule, escape in queue:
        print("- %s: %s (escape %s)" % (rid, short(rule), escape or "none named"))
    if not queue and os.path.isfile(os.path.join(root, RULE_QUEUE_PATH)):
        print("None.")
    names = set(f.name for f in features)
    counts, this_build = {}, {}
    flakes_file = os.path.join(root, FLAKES_PATH)
    for entry in read_records(flakes_file)[0]:
        title = entry.get("title")
        counts[title] = counts.get(title, 0) + 1
        if names & set(feature_names(entry.get("feature", ""))):
            this_build[title] = this_build.get(title, 0) + 1
    print()
    print("## Flakes this build (%d)" % len(this_build))
    print()
    for title, count in this_build.items():
        line = "- %s: %d this build, %d in all" % (title, count, counts[title])
        if counts[title] >= FLAKE_LIMIT:
            fixed_re = fixed_in_re(tracker_dir(features[0].config))
            fixed = [fixed_re.search(r[-1]).group(0) for r in rows if title in " ".join(r) and fixed_re.search(r[-1])]
            line += "; " + ("the ledger names %s" % fixed[0] if fixed else "no ledger row names a ticket or bug spec")
        print(line)
    if not this_build:
        print("None.")
    brief = brief_items(features[0])
    print()
    if brief is None:
        print("## The brief's claims (0)")
        print()
        print("The spec has no Brief: line.")
    else:
        items, brief_path = brief
        spec_items = open_list_items(read(os.path.join(features[0].dir, "spec.md")))
        print("## The brief's claims (%d)" % len(items))
        print()
        print("From %s." % os.path.relpath(brief_path, root))
        print()
        for number, phrase in items:
            citing = []
            for tn in sorted(features[0].tickets):
                ticket = features[0].tickets[tn]
                text = "\n".join(l for l in read(ticket.path).split("\n") if "Source:" in l)
                if number in brief_numbers(text):
                    citing.append("ticket %s" % ticket.label)
            for item in spec_items:
                if number in brief_numbers(item):
                    citing.append("Open list item %s" % re.match(r"(\d+)", item).group(1))
            print("%d. %s: %s" % (number, phrase, ", ".join(citing) if citing else "uncited"))
    return 0


AUDIT_SKIPPED = "audit skipped: not in this kit"


def audit_step(root: str, config: dict, names: list, report=None) -> bool:
    """Ticket 13's `audit`, called when it exists. A missing audit is a pass that says so (AUDIT_SKIPPED),
    in `close`'s Facts and in the records stamp's output; it is never silent."""
    audit = getattr(audit_module, "cmd_audit", None)
    if audit is None:
        print(AUDIT_SKIPPED)
        return True
    return audit(root, config, names, report) == 0


def worktree_removals(root: str) -> list:
    out = run_git(root, "worktree", "list", "--porcelain") or ""
    paths = [l[len("worktree "):] for l in out.split("\n") if l.startswith("worktree ")]
    return ['git worktree remove "%s"' % p for p in paths[1:] if "/.claude/worktrees/" in p]


def insert_build_row(root: str, row: str) -> None:
    path = os.path.join(root, LEDGER_PATH)
    lines = read(path).split("\n") if os.path.isfile(path) else ["# Ledger", ""]
    heading = next((i for i, l in enumerate(lines) if re.match(r"^##\s+Builds\s*$", l)), None)
    if heading is None:
        lines += ["", "## Builds", "", row, ""]
    else:
        stop = next((i for i in range(heading + 1, len(lines)) if re.match(r"^##\s", lines[i])), len(lines))
        table = [i for i in range(heading + 1, stop) if lines[i].startswith("|")]
        lines.insert(table[-1] + 1 if table else heading + 1, row)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def has_github_remote(root: str) -> bool:
    return bool(REMOTE.search(run_git(root, "remote", "get-url", "origin") or ""))


def soft_step(word: str, step) -> None:
    """Run a reporting step of `close`: a failure prints one line and never changes the exit code."""
    try:
        code = step()
    except Exception as err:
        code, reason = 1, str(err).split("\n")[0] or type(err).__name__
    else:
        reason = "exit %s" % code
    if code:
        print("%s: failed (%s); close carries on" % (word, reason))


def tokens_facts(records: list, prices, reason: str = "no reason given") -> list:
    """The Facts lines for the tokens record: the total, and with prices the cost and the count of models with no price.
    With no record written there is no figure: `not read (<reason>)` and no Cost line, never a zero."""
    if not records:
        return ["- Tokens: not read (%s)" % reason]
    lines = ["- Tokens: %d" % sum(number(r.get(k)) for r in records for k in KINDS)]
    if isinstance(prices, dict) and prices:
        priced = read_prices({"prices": prices})
        costs = [priced_cost(r, priced) for r in records]
        unpriced = {r.get("model") for r, c in zip(records, costs) if c is None}
        lines.append("- Cost: $%.2f (%d model(s) unpriced)" % (sum(c for c in costs if c is not None), len(unpriced)))
    return lines


def cmd_close(root: str, config: dict, features: list, collect: bool) -> int:
    names = [f.name for f in features]
    head = run_git(root, "rev-parse", "HEAD")
    stamp = read_stamp(root)
    dirty = run_git(root, "status", "--porcelain")
    if not stamp or stamp[0] != head or stamp[1] != ", ".join(names):
        return refuse("close-stamped", "this tip (%s) is not stamped for %s (the stamp is %s)" % ((head or "?")[:7], ", ".join(names), ("for %s at %s" % (stamp[1], stamp[0][:7])) if stamp else "absent"), "`python3 .claude/factory/gate.py ready %s` passing at this tip" % " ".join(names))
    if stamp[3]:
        return refuse("close-once", "%s is already closed (stamped as %s, built %s) and a second close would write the records twice" % (", ".join(names), stamp[0][:7], stamp[3][:7]), "nothing: the records are written")
    if dirty:
        return refuse("close-clean", "the working tree is not clean and close writes the records after the built tip", "everything else committed")
    if not audit_step(root, config, names):
        return refuse("close-audit", "the audit found violations (above)", "each violation fixed, then close again")
    roles = [r for r in ("scorer", "observer") if os.path.isfile(os.path.join(root, ".claude", "agents", r + ".md"))]
    if roles and not collect:
        for role in roles:
            print("dispatch: %s %s --tip %s" % (role, " ".join(names), head))
        print("close: nothing written yet. When they have reported, run `python3 .claude/factory/gate.py close %s --collect`." % " ".join(names))
        return 0
    for missing in ("scorer", "observer"):
        if missing not in roles:
            print("%s: no role file in this kit; nothing to collect" % missing)
    today = time.strftime("%Y-%m-%d")
    totals = {"done": 0, "all": 0, "user": 0, "proved": 0, "human": 0, "roles": {}, "reviews": 0, "blocking": 0, "mergers": 0}
    os.makedirs(os.path.dirname(os.path.join(root, FLAKES_PATH)), exist_ok=True)
    refusals = guard_refusals(root)
    rows = []
    for feature in features:
        entries = read_log(root, feature.name)
        roles_here = {}
        for entry in entries:
            if entry["verb"] == "dispatch":
                roles_here[entry["args"][1]] = roles_here.get(entry["args"][1], 0) + 1
        counts = box_counts(list(feature.tickets.values()))
        numbers = feature_numbers(feature)
        stamps = log_times(root, feature.name)
        first, last = (parse_log_time(stamps[0]), parse_log_time(stamps[-1])) if stamps else (None, None)
        hours = round((last - first) / 3600.0, 1) if first and last else 0
        row = {"date": today, "feature": feature.name, "tip": head, "tickets": len(feature.tickets), "reviews": numbers["reviews"],
               "blocking": numbers["blocking"], "mutants_tried": numbers["mutants_tried"], "mutants_survived": numbers["mutants_survived"],
               "boxes_proved": counts["proved"], "boxes_human": counts["human"], "subagents": roles_here, "guard_refusals": refusals, "hours": hours}
        rows.append(row)
        with open(os.path.join(root, "docs", "agents", "local", "builds.jsonl"), "a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
        by_role = ", ".join("%s %d" % (r, n) for r, n in sorted(roles_here.items())) or "none logged"
        survived = "%d of %d mutants survived" % (numbers["mutants_survived"], numbers["mutants_tried"])
        insert_build_row(root, "| %s | %s to %s | %d | %d reviews: %d blocking / %d notes / %s | Not counted by the gate | Not counted by the gate | Not counted by the gate | %s | %d | %d |" % (
            feature.name, stamps[0] if stamps else "unknown", stamps[-1] if stamps else "unknown", len(feature.tickets), numbers["reviews"],
            numbers["blocking"], numbers["notes"], survived, by_role, roles_here.get("merger", 0), refusals))
        totals["all"] += len(feature.tickets)
        totals["done"] += len([t for t in feature.tickets.values() if t.status == "done"])
        totals["user"] += len([t for t in feature.tickets.values() if t.status == "ready-for-human"])
        totals["proved"] += counts["proved"]
        totals["human"] += counts["human"]
        for role, n in roles_here.items():
            totals["roles"][role] = totals["roles"].get(role, 0) + n
    token_reason = "nothing written"
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured):
            token_records = write_tokens(root, config, names)
    except Exception as err:
        token_records = []
        captured = io.StringIO(captured.getvalue() + "tokens: failed (%s); the tokens record is unchanged\n" % (str(err).split("\n")[0] or type(err).__name__))
    print(captured.getvalue(), end="")
    written_for = {r.get("feature") for r in token_records}
    token_records = [r for r in read_records(os.path.join(root, TOKENS_PATH))[0] if r.get("feature") in names]  # the page's figures: every line of the named features
    older = [n for n in names if n not in written_for and any(r.get("feature") == n for r in token_records)]
    lines = [l for l in captured.getvalue().split("\n") if l.startswith("tokens: ")]
    if lines:
        token_reason = (lines[-1] if not token_records and lines[-1].startswith("tokens: failed") else lines[0])[len("tokens: "):]
    flaked = count_flakes(read_records(os.path.join(root, FLAKES_PATH))[0], names)
    print("## Facts")
    print("")
    print("- Built tip: %s" % head)
    print("- Stamped: %s (%s)" % (stamp[2], stamp[1]))
    print("- Tickets: %d done of %d (%d for the user)" % (totals["done"], totals["all"], totals["user"]))
    print("- Boxes: %d proved, %d for a person to judge" % (totals["proved"], totals["human"]))
    print("- Suites: %s, green on the built tip at the stamp" % ", ".join(c["name"] for c in config.get("checks", [])))
    print("- Subagents: %s" % (", ".join("%s %d" % (r, n) for r, n in sorted(totals["roles"].items())) or "none logged"))
    for fact in tokens_facts(token_records, config.get("prices"), token_reason):
        print(fact)
    if older:
        print("- Older figures: %s (lines kept from an earlier read)" % ", ".join(older))
    print("- Audit: %s" % ("skipped (not in this kit)" if not hasattr(audit_module, "cmd_audit") else "passed"))
    print("- Guard refusals: %d" % refusals)
    print("- Flakes: %d" % flaked)
    print("- Hand-over: python3 .claude/factory/gate.py handover %s (%s as built, the close commit as stamped)" % (" ".join(names), head[:7]))
    print("")
    if has_github_remote(root):
        soft_step("github", lambda: cmd_github(root, config, None, None))
    soft_step("dashboard", lambda: cmd_dashboard(root, config, None, False))
    removes = worktree_removals(root)
    print("Records written: docs/agents/local/builds.jsonl and the Builds row of docs/agents/local/ledger.md. Remove the worktrees:")
    for command in removes:
        print(command)
    if not removes:
        print("(no ticket worktrees)")
    return 0


def cmd_ready_records(features: list, close_ref: str) -> int:
    """Re-stamps the close commit Y when it is one commit on the built tip X that touches records alone
    and the report names X."""
    root, config = features[0].root, features[0].config
    names = ", ".join(f.name for f in features)
    stamp = read_stamp(root)
    built = (stamp[3] or stamp[0]) if stamp else None
    y = run_git(root, "rev-parse", "--verify", "-q", "%s^{commit}" % close_ref)
    head = run_git(root, "rev-parse", "HEAD")
    problems = []
    if not built:
        problems.append("no built tip is stamped: run `gate.py ready %s` on the built tip, then `close`" % names)
    if not y:
        problems.append("%s is not a commit" % close_ref)
    elif y != head:
        problems.append("%s is not the checked-out tip" % close_ref)
    if run_git(root, "status", "--porcelain"):
        problems.append("working tree is not clean")
    if problems:
        for problem in problems:
            print(problem)
        return refuse("records-tip", "%d problem(s) are listed above" % len(problems), "each problem fixed, then ready --records again")
    parents = (run_git(root, "rev-list", "--parents", "-n1", y) or "").split()[1:]
    if parents != [built]:
        problems.append("the close commit's parent is not the built tip %s (a close is one commit on it)" % built[:7])
    changed = [n for n in (run_git(root, "diff", "--name-only", "--no-renames", "%s..%s" % (built, y)) or "").split("\n") if n]
    for name in changed:
        if not record_paths_ok(name, tracker_dir(config)):
            problems.append("%s changed after the built tip and is not a record path: a code change is the next feature, not this close" % name)
    report = os.path.join(features[0].dir, "report.md")
    if not os.path.isfile(report):
        problems.append("%s does not exist" % os.path.relpath(report, root))
    else:
        found = re.search(r"Built tip:\s*`?([0-9a-f]{7,40})", read(report), re.I)
        if not found:
            problems.append("%s does not name a built tip (the Facts block's `Built tip:` line)" % os.path.relpath(report, root))
        elif not built.startswith(found.group(1)):
            problems.append("%s names built tip %s, not %s" % (os.path.relpath(report, root), found.group(1)[:7], built[:7]))
        elif not audit_step(root, config, [f.name for f in features], report):
            problems.append("the audit of the report refused it")
    if problems:
        for problem in problems:
            print(problem)
        return refuse("records-report", "%d problem(s) are listed above" % len(problems), "each problem fixed, then ready --records again")
    path = stamp_path(root)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("%s\n%s\n%s\nbuilt %s\n" % (y, names, time.strftime("%Y-%m-%dT%H:%M:%S"), built))
    print("READY: %s at %s (records stamp); built tip %s.%s `gh pr ready` will now pass for this tip." % (
        names, y[:7], built[:7], " (audit skipped: not built yet)." if not hasattr(audit_module, "cmd_audit") else ""))
    return 0
