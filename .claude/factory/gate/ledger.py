"""The escapes ledger and `stats` (`gate.py ledger add`, `ledger check`, `stats`)."""
from __future__ import annotations

import glob
import json
import os
import re
import time

from gate.checks import durations_path
from gate.config import LEDGER_PATH, read
from gate.evidence import parse_review
from gate.git import run_git
from gate.log import agent_lines, log_times
from gate.refuse import refuse
from gate.tracker import short, table_cells, tracker_dir


def ledger_escape_rows(root: str) -> list:
    """The cells of each row of the ledger's Escapes table."""
    path = os.path.join(root, LEDGER_PATH)
    rows = []
    if not os.path.isfile(path):
        return rows
    in_escapes = False
    for line in read(path).split("\n"):
        if line.startswith("#"):
            in_escapes = line.lower().startswith("## escapes")
            continue
        if not in_escapes or not line.strip().startswith("|"):
            continue
        cells = table_cells(line)
        if len(cells) < 3 or set(cells[0]) <= set("-: ") or cells[0].lower() in ("date", "id"):
            continue
        if ESCAPE_ID_RE.match(cells[0]):
            cells = cells[1:]  # the id joins the row to its line in escapes.jsonl; the readers below count from the date
        rows.append(cells)
    return rows


ESCAPES_PATH = os.path.join("docs", "agents", "local", "escapes.jsonl")
ESCAPE_ID_RE = re.compile(r"^E-\d{3,}$")
ESCAPE_FIELDS = ("date", "feature", "id", "class", "found_by", "should_have_been", "fixed_in", "rule_id", "flake")
ESCAPE_CLASSES = ("blocking", "sweep", "design", "nit", "escape")
ESCAPE_GATES = ("user", "walk", "unit", "ticket-review", "foundation-review", "branch-review", "re-check", "exploration", "ready-gate", "none")
# Gates that run after a ticket's own review: a nit or sweep found by one of these (or the user) was misclassed.
LATER_GATES = ("user", "foundation-review", "branch-review", "re-check", "exploration", "ready-gate")


def read_escape_lines(root: str):
    """Returns (lines, problems): the parsed lines of escapes.jsonl and what is wrong with them."""
    path = os.path.join(root, ESCAPES_PATH)
    lines, problems = [], []
    if not os.path.isfile(path):
        return lines, problems
    for number, text in enumerate(read(path).split("\n"), 1):
        if not text.strip():
            continue
        try:
            record = json.loads(text)
        except ValueError:
            problems.append("%s line %d is not JSON" % (ESCAPES_PATH, number))
            continue
        if not isinstance(record, dict) or sorted(record) != sorted(ESCAPE_FIELDS):
            problems.append("%s line %d does not have exactly the fields %s" % (ESCAPES_PATH, number, ", ".join(ESCAPE_FIELDS)))
            continue
        if not ESCAPE_ID_RE.match(str(record["id"])):
            problems.append("%s line %d: id %r is not E-NNN" % (ESCAPES_PATH, number, record["id"]))
        if record["class"] not in ESCAPE_CLASSES:
            problems.append("%s line %d: class %r is not one of %s" % (ESCAPES_PATH, number, record["class"], ", ".join(ESCAPE_CLASSES)))
        for field in ("found_by", "should_have_been"):
            if record[field] not in ESCAPE_GATES:
                problems.append("%s line %d: %s %r is not one of %s" % (ESCAPES_PATH, number, field, record[field], ", ".join(ESCAPE_GATES)))
        lines.append(record)
    return lines, problems


def ledger_check(root: str) -> list:
    """What is wrong with the join of the ledger's prose rows and escapes.jsonl."""
    lines, problems = read_escape_lines(root)
    path = os.path.join(root, LEDGER_PATH)
    row_ids = []
    if os.path.isfile(path):
        in_escapes = False
        for text in read(path).split("\n"):
            if text.startswith("#"):
                in_escapes = text.lower().startswith("## escapes")
                continue
            if not in_escapes or not text.strip().startswith("|"):
                continue
            cells = table_cells(text)
            if len(cells) < 3 or (cells[0] and set(cells[0]) <= set("-: ")) or cells[0].lower() in ("date", "id"):
                continue
            if ESCAPE_ID_RE.match(cells[0]):
                row_ids.append(cells[0])
            else:
                problems.append("a prose row in %s has no id (first cell %r): `gate.py ledger add` prints the row with one" % (LEDGER_PATH, short(cells[0], 30)))
    line_ids = [l["id"] for l in lines]
    for found in sorted(set(i for i in row_ids if row_ids.count(i) > 1)):
        problems.append("%s is the id of more than one prose row" % found)
    for found in sorted(set(i for i in line_ids if line_ids.count(i) > 1)):
        problems.append("%s is the id of more than one line in %s" % (found, ESCAPES_PATH))
    for found in sorted(set(row_ids) - set(line_ids)):
        problems.append("%s has a prose row and no line in %s" % (found, ESCAPES_PATH))
    for found in sorted(set(line_ids) - set(row_ids)):
        problems.append("%s has a line in %s and no prose row in %s" % (found, ESCAPES_PATH, LEDGER_PATH))
    return problems


def cmd_ledger(root: str, words: list) -> int:
    usage = ("gate: usage: ledger check | ledger add --feature <f> --class <%s> --found-by <gate> --should-have-been <gate> "
             "--defect \"<text>\" [--date <YYYY-MM-DD>] [--fixed-in <text>] [--rule-id <id>] [--flake <title>] [--change \"<text>\"]; gates: %s"
             % ("|".join(ESCAPE_CLASSES), ", ".join(ESCAPE_GATES)))
    if words == ["check"]:
        problems = ledger_check(root)
        for problem in problems:
            print(problem)
        print("ledger: %s" % ("joined" if not problems else "%d problem(s)" % len(problems)))
        return 1 if problems else 0
    if not words or words[0] != "add" or len(words) % 2 == 0:
        print(usage)
        return 2
    flags = {}
    for flag, value in zip(words[1::2], words[2::2]):
        if flag not in ("--feature", "--class", "--found-by", "--should-have-been", "--defect", "--date", "--fixed-in", "--rule-id", "--flake", "--change") or flag in flags:
            print(usage)
            return 2
        flags[flag] = value
    missing = [f for f in ("--feature", "--class", "--found-by", "--should-have-been", "--defect") if not flags.get(f)]
    if missing:
        print(usage)
        return refuse("ledger-flags", "ledger add is missing %s" % ", ".join(missing), "those flags", 2)
    if flags["--class"] not in ESCAPE_CLASSES:
        return refuse("ledger-flags", "--class %r is not a class" % flags["--class"], "one of %s" % ", ".join(ESCAPE_CLASSES), 2)
    for flag in ("--found-by", "--should-have-been"):
        if flags[flag] not in ESCAPE_GATES:
            return refuse("ledger-flags", "%s %r is not a gate" % (flag, flags[flag]), "one of %s" % ", ".join(ESCAPE_GATES), 2)
    lines, _ = read_escape_lines(root)
    numbers = [int(l["id"][2:]) for l in lines if ESCAPE_ID_RE.match(str(l["id"]))]
    record = {"date": flags.get("--date") or time.strftime("%Y-%m-%d"), "feature": flags["--feature"], "id": "E-%03d" % (max(numbers or [0]) + 1),
              "class": flags["--class"], "found_by": flags["--found-by"], "should_have_been": flags["--should-have-been"],
              "fixed_in": flags.get("--fixed-in", ""), "rule_id": flags.get("--rule-id", ""), "flake": flags.get("--flake", "")}
    path = os.path.join(root, ESCAPES_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    cells = [record["id"], record["date"], record["feature"], flags["--defect"], record["found_by"], record["should_have_been"],
             flags.get("--change") or record["fixed_in"]]
    print("wrote %s to %s. Paste this row under ## Escapes in %s:" % (record["id"], ESCAPES_PATH, LEDGER_PATH))
    print("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
    return 0


# Which role's tokens answer for which gate (walks and unit have no subagent: their cost is the checks' durations).
ROLE_GATES = {"ticket-reviewer": ("ticket-review",), "branch-reviewer": ("branch-review", "re-check")}


def transcript_tokens(agent: str):
    """(total tokens, output tokens) of one subagent's transcript, each message counted once, or None
    when no transcript is found or none of it parses. The transcripts are the harness's, under
    `$GATE_PROJECTS_DIR` (default ~/.claude/projects): <project>/<session>/subagents/agent-<id>.jsonl."""
    base = os.environ.get("GATE_PROJECTS_DIR") or os.path.join(os.path.expanduser("~"), ".claude", "projects")
    for path in glob.glob(os.path.join(glob.escape(base), "*", "*", "subagents", "agent-%s.jsonl" % glob.escape(agent))):
        usage_by_message = {}
        try:
            for number, text in enumerate(read(path).split("\n")):
                try:
                    message = json.loads(text).get("message")
                    usage = message.get("usage")
                    parts = [int(usage.get(k) or 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")]
                except (ValueError, AttributeError, TypeError):
                    continue
                usage_by_message[message.get("id") or "line-%d" % number] = parts
        except OSError:
            continue
        if usage_by_message:
            return sum(sum(p) for p in usage_by_message.values()), sum(p[3] for p in usage_by_message.values())
    return None


def blocking_findings(root: str, build: str, numbers, folder: str, tracker: str):
    """(count, source) of blocking findings in the build's per-ticket reviews of those tickets (`reviews/NN.md`),
    or, with no numbers, in every findings file of `findings/` (the whole-branch reviewers')."""
    base = os.path.join(root, tracker, build, folder)
    if numbers is None:
        paths = sorted(glob.glob(os.path.join(glob.escape(base), "*.md")))
    else:
        paths = [os.path.join(base, "%s.md" % n) for n in numbers]
    paths = [p for p in paths if os.path.isfile(p)]
    count = sum(len([f for f in parse_review(read(p))[1] if f.section == "blocking"]) for p in paths)
    return count, "%d file(s) of %s/%s/%s" % (len(paths), tracker, build, folder)


CHECK_OF_GATE = {"walk": "walks", "unit": "unit"}


def check_seconds(root: str, check: str):
    """(runs, seconds) of the named check as `gate.py checks` recorded them, or None."""
    path = durations_path(root)
    if not path or not os.path.isfile(path):
        return None
    runs = seconds = 0
    for text in read(path).split("\n"):
        try:
            record = json.loads(text)
        except ValueError:
            continue
        if record.get("check") == check:
            runs += 1
            seconds += int(record.get("seconds") or 0)
    return (runs, seconds) if runs else None


def stats_escapes(root: str, builds: list, tracker: str) -> None:
    lines, problems = read_escape_lines(root)
    print()
    for problem in problems:
        print("escapes: %s" % problem)
    for feature in sorted(set(l["feature"] for l in lines)):
        counts = {}
        for l in lines:
            if l["feature"] == feature:
                counts[l["should_have_been"]] = counts.get(l["should_have_been"], 0) + 1
        print("escapes in %s by should-have-been gate: %s" % (feature, ", ".join("%s %d" % (g, counts[g]) for g in sorted(counts, key=lambda g: (-counts[g], g)))))
    if not lines:
        print("escapes: no lines in %s" % ESCAPES_PATH)
    misclassed = [l for l in lines if l["class"] in ("nit", "sweep") and l["found_by"] in LATER_GATES]
    print("misclassed (nit or sweep, found by a later gate or the user): %d%s" % (len(misclassed), " (%s)" % ", ".join(l["id"] for l in misclassed) if misclassed else ""))
    print()
    print("tokens per role per build (from subagent transcripts; a message counts once; total = input + cache writes + cache reads + output)")
    matched = 0
    per_gate = {}
    for build in builds:
        agents = [(n, r, a) for n, r, a in agent_lines(root, build) if r != "foundation-read"]
        matched += len(agents)
        by_role = {}
        for number, role, agent in agents:
            by_role.setdefault(role, []).append(transcript_tokens(agent))
        found = {"ticket-reviewer": blocking_findings(root, build, sorted(set(n for n, r, _ in agents if r == "ticket-reviewer")), "reviews", tracker),
                 "branch-reviewer": blocking_findings(root, build, None, "findings", tracker)}
        for role in sorted(by_role):
            read_ones = [t for t in by_role[role] if t]
            if not read_ones:
                print("  %s %s: not read (%d dispatch(es), no transcript parsed)" % (build, role, len(by_role[role])))
                continue
            total, output = sum(t[0] for t in read_ones), sum(t[1] for t in read_ones)
            text = "  %s %s: %d tokens (%d output) in %d transcript(s)" % (build, role, total, output, len(read_ones))
            if len(read_ones) < len(by_role[role]):
                text += ", %d not read" % (len(by_role[role]) - len(read_ones))
            if role in found:
                count, source = found[role]
                text += "; " + ("%d per blocking finding (%d blocking in %s)" % (total // count, count, source) if count else "0 blocking findings in %s: no division" % source)
            print(text)
            for gate in ROLE_GATES.get(role, ()):
                per_gate[(build, gate)] = per_gate.get((build, gate), 0) + total
    print("dispatches matched: %d (the log's `dispatch <NN> <role> --agent <id>` lines; earlier prose lines are not matched)" % matched)
    print()
    print("tokens per escape per gate (the role that runs the gate, over the build's escapes it should have found)")
    for build in builds:
        for gate in ESCAPE_GATES:
            roles = [r for r, gates in ROLE_GATES.items() if gate in gates]
            missed = len([l for l in lines if l["feature"] == build and l["should_have_been"] == gate])
            if not missed:
                continue
            tokens = per_gate.get((build, gate))
            if roles and tokens:
                # a role that covers two gates (branch-reviewer: branch-review and re-check) is divided by the escapes of both
                covered = sum(len([l for l in lines if l["feature"] == build and l["should_have_been"] == g]) for g in ROLE_GATES[roles[0]])
                print("  %s %s: %d tokens, %d escape(s), %d per escape" % (build, gate, tokens, covered, tokens // covered))
            elif roles:
                print("  %s %s: %d escape(s), tokens not read from transcripts" % (build, gate, missed))
            else:
                spent = check_seconds(root, CHECK_OF_GATE.get(gate, ""))
                if spent:
                    print("  %s %s: %d escape(s); check %s ran %d time(s), %ds in all (source: the git directory's factory/check-durations.jsonl, written by `gate.py checks`, every build together); %ds per escape" % (build, gate, missed, CHECK_OF_GATE[gate], spent[0], spent[1], spent[1] // missed))
                else:
                    print("  %s %s: %d escape(s), cost not read (no tokens: no subagent runs this gate; no check duration recorded for it)" % (build, gate, missed))


def cmd_stats(root: str, config: dict) -> int:
    common = run_git(root, "rev-parse", "--git-common-dir")
    if common and not os.path.isabs(common):
        common = os.path.join(root, common)
    folder = os.path.join(common or root, "factory")
    logs = sorted(glob.glob(os.path.join(folder, "build-log-*.md")))
    for path in logs:
        name = os.path.basename(path)[len("build-log-"):-len(".md")]
        times = log_times(root, name)
        lines = len([l for l in read(path).split("\n") if l.strip()])
        if times:
            print("build log %s: first %s, last %s (%d lines)" % (name, times[0], times[-1], lines))
        else:
            print("build log %s: no dated lines (%d lines)" % (name, lines))
    stats_escapes(root, [os.path.basename(p)[len("build-log-"):-len(".md")] for p in logs], tracker_dir(config))
    path = os.path.join(folder, "guard.log")
    if not os.path.isfile(path):
        print("guard: no refusals logged")
        return 0
    by_rule = {}
    for line in read(path).split("\n"):
        try:
            record = json.loads(line)
        except ValueError:
            continue
        key = (record.get("rule", "?"), record.get("agent", "?"))
        by_rule[key] = by_rule.get(key, 0) + 1
    print("guard refusals (rule, agent, count):")
    for (rule, agent), count in sorted(by_rule.items(), key=lambda item: -item[1]):
        print("  %-20s %-20s %d" % (rule, agent, count))
    return 0
