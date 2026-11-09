"""The build log, its grammar, `open`, and the checklists printed when a phase ends."""
from __future__ import annotations

import os
import re
import time

from gate.config import read
from gate.git import run_git
from gate.refuse import refuse
from gate.tracker import tracker_dir


def log_path(root: str, feature_name: str):
    common = run_git(root, "rev-parse", "--git-common-dir")
    if common is None:
        return None
    if not os.path.isabs(common):
        common = os.path.join(root, common)
    return os.path.join(common, "factory", "build-log-%s.md" % re.sub(r"[^A-Za-z0-9._-]+", "-", feature_name))


def empty_frontier_checklist(feature_name: str) -> list:
    return [
        "When the frontier is empty, in this order (the exploration ticket has already run, so the defects a walker can find are fixed before the expensive review reads the code):",
        "1. Audit the boxes: python3 .claude/factory/gate.py boxes %s. An open box means a ticket closed too early: it goes back to an implementer." % feature_name,
        "2. Review the whole branch: `boxes` prints the dispatch list when it is clean.",
        "3. Run the ready gate: python3 .claude/factory/gate.py ready %s [<review-fix feature>]." % feature_name,
    ]


def review_wave_checklist(feature_name: str, tracker: str) -> list:
    folder = "%s/%s-review/findings/" % (tracker, feature_name)
    return [
        "Review the whole branch (no review runs in the main session). Findings folder: %s (with a pull request: %s/pr-<N>-review/findings/)." % (folder, tracker),
        "1. Wave one, at once: one branch-reviewer per area (by layer or ticket group), each reading the diff from the merge-base with main and writing %s<area>.md; and one standards-reviewer writing %sstandards.md. Each returns only the path. Then: gate.py log %s review-wave 1" % (folder, folder, feature_name),
        "2. Wave two: one branch-reviewer for the seams, given the whole diff and the area files. Then: gate.py log %s review-wave 2" % feature_name,
        "3. Reviewers commit nothing. One review-merger ranks and classes the findings (blocking, sweep, design, nit), writes the fix spec, its tickets and the Open list, and commits the findings files.",
        "4. Implementers work the fix tickets through the loop. The branch is then read again at most twice (findings/round-<n>.md); a round after a small fix is a scoped read of that diff only. The two rounds are the root feature's: there is no second fix feature (release refuses <feature>-review-2); what still blocks goes to the user's Open list.",
    ]


def close_out_checklist(names: list, head: str, tracker: str) -> list:
    joined = " ".join(names)
    first = names[0]
    return [
        "Close-out. The built tip is %s; nothing tracked may change under it except records:" % head[:7],
        "1. python3 .claude/factory/gate.py close %s: it refuses unless this tip is stamped, runs the audit, prints the dispatch lines for the scorer and the observer (run again with --collect when they have reported), writes every record in one pass, and prints the Facts block and the worktree remove commands." % joined,
        "2. Write %s/%s/report.md embedding the Facts block verbatim and restating none of it. Commit everything from step 1 and the report as one commit `Close %s` (Y)." % (tracker, first, first),
        "3. python3 .claude/factory/gate.py ready %s --records <Y>: re-stamps Y only when the diff from %s to Y touches records alone and the report names %s." % (joined, head[:7], head[:7]),
        "4. The hand-over names %s as built and Y as stamped. `gh pr ready` is allowed on Y." % head[:7],
    ]


LOG_TIME = "%Y-%m-%dT%H:%M:%S"
LOG_LINE_RE = re.compile(r"^(?:-\s+)?(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?)\s+(\S+)(?:\s+(.*))?$")
FOLLOW_UP = "--follow-up"
NN_RE = re.compile(r"^\d{1,3}$")
LOG_USAGE = {
    "dispatch": "dispatch <NN> <role> --agent <id> [--follow-up]",
    "report": "report <NN> <role>",
    "resume": "resume <NN> <role>",
    "foundation-read": "foundation-read <NN> --agent <id>",
    "review-wave": "review-wave <n>",
    "spec-against-brief": "spec-against-brief <path>",
    "merge-start": "merge-start <NN> <tip>",
    "merge-end": "merge-end <NN> <result>",
    "merge-abort": "merge-abort <NN> <start time> \"<reason>\"",
    "decided": "decided <n> <commit>",
    "open": "open <n> \"<item>\" (written by `gate.py open`)",
    "observation": "observation \"<text>\"",
    "note": "note \"<text>\"",
}


HASH_RE = re.compile(r"^[0-9a-f]{7,40}$")
ISO_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")
ABORT_WORDS = ("refused", "red", "conflict", "failed")


def log_args_ok(verb: str, words: list, strict: bool = False) -> bool:
    """Whether the words after a verb have the verb's shape. The writer is strict (a `merge-end` result must be a
    hash or an abort word); the reader is not, so a `merge-end 01 merged` written by hand is still read and paired."""
    if verb == "dispatch":
        if len(words) == 5 and words[4] == FOLLOW_UP:
            words = words[:4]
        return len(words) == 4 and bool(NN_RE.match(words[0])) and words[2] == "--agent" and not words[3].startswith("-")
    if verb == "foundation-read":
        return len(words) == 3 and bool(NN_RE.match(words[0])) and words[1] == "--agent"
    if verb in ("report", "resume"):
        return len(words) == 2 and bool(NN_RE.match(words[0]))
    if verb == "review-wave":
        return len(words) == 1 and words[0].isdigit()
    if verb == "spec-against-brief":
        return len(words) == 1
    if verb == "merge-start":
        return len(words) == 2 and bool(NN_RE.match(words[0]))
    if verb == "merge-end":
        return len(words) >= 2 and bool(NN_RE.match(words[0])) and (not strict or bool(HASH_RE.match(words[1])) or words[1] in ABORT_WORDS)
    if verb == "merge-abort":
        return len(words) >= 3 and bool(NN_RE.match(words[0])) and bool(ISO_TIME_RE.match(words[1]))
    if verb == "decided":
        return len(words) == 2 and words[0].isdigit() and bool(HASH_RE.match(words[1]))
    if verb == "open":
        return len(words) >= 2 and bool(NN_RE.match(words[0]))
    return verb in ("observation", "note") and len(words) >= 1


NN_VERBS = ("dispatch", "report", "resume", "foundation-read", "merge-start", "merge-end", "merge-abort")


def normal_words(verb: str, words: list) -> list:
    """The ticket number is two digits in every verb, so `3` and `03` are one ticket."""
    if verb in NN_VERBS and words and NN_RE.match(words[0]):
        return ["%02d" % int(words[0])] + words[1:]
    return words


def read_log(root: str, feature_name: str) -> list:
    """The grammar's lines, as {time, verb, args, text}. Anything else in the log (prose written before
    the grammar, or a line whose verb or arguments do not fit) is invisible here. Both the ISO time the
    writer now uses and the minute-only `- YYYY-MM-DD HH:MM` that `gate.py merge` first wrote are read."""
    path = log_path(root, feature_name)
    if not path or not os.path.isfile(path):
        return []
    entries = []
    for line in read(path).split("\n"):
        found = LOG_LINE_RE.match(line)
        if not found or found.group(2) not in LOG_USAGE:
            continue
        words = (found.group(3) or "").split()
        if log_args_ok(found.group(2), words):
            words = normal_words(found.group(2), words)
            entries.append({"time": found.group(1), "verb": found.group(2), "args": words, "text": " ".join(words)})
    return entries


def log_times(root: str, feature_name: str) -> list:
    """The timestamp of every dated line in the log, grammar or prose, as written."""
    path = log_path(root, feature_name)
    if not path or not os.path.isfile(path):
        return []
    times = []
    for line in read(path).split("\n"):
        found = re.match(r"^(?:-\s+)?(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?)\b", line)
        if found:
            times.append(found.group(1))
    return times


def parse_log_time(text: str):
    for form in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"):
        try:
            return time.mktime(time.strptime(text, form))
        except ValueError:
            continue
    return None


def is_follow_up(entry: dict) -> bool:
    """Whether a log entry is a `dispatch ... --follow-up` line: a fix after the ticket merged, the ticket's next attempt."""
    return entry["verb"] == "dispatch" and entry["args"][-1] == FOLLOW_UP


def agent_lines(root: str, feature_name: str) -> list:
    found = []
    for entry in read_log(root, feature_name):
        if entry["verb"] == "dispatch":
            found.append((entry["args"][0], entry["args"][1], entry["args"][3]))
        elif entry["verb"] == "foundation-read":
            found.append((entry["args"][0], "foundation-read", entry["args"][2]))
    return sorted(found)


def cmd_log(root: str, feature_name: str, words: list) -> int:
    """With a verb and its arguments: appends one line `<ISO time> <verb> <args>` to the build log.
    `--agents`: prints agent ids by ticket and role. Without: prints the log's tail.
    The log lives in the git directory, shared by every worktree and never part
    of the tree, so writing it cannot dirty a checkout or disturb a merge."""
    path = log_path(root, feature_name)
    if path is None:
        return refuse("git-repository", "the working directory is not a git repository", "gate.py run inside the repo")
    if words == ["--agents"]:
        lines = agent_lines(root, feature_name)
        for number, role, agent in lines:
            print("%s %s %s" % (number, role, agent))
        if not lines:
            print("no agent ids logged for %s" % feature_name)
        return 0
    if words:
        verb, rest = words[0], [w for w in " ".join(words[1:]).split()]
        if verb not in LOG_USAGE:
            print("gate: usage: log <feature> <verb> ...; verbs: %s" % "; ".join(LOG_USAGE.values()))
            return refuse("log-verb", "%s is not a log verb" % verb, "a verb from the usage line (`note \"<text>\"` is for anything else)", 2)
        if not log_args_ok(verb, rest, strict=True):
            if verb == "merge-end" and len(rest) >= 2 and NN_RE.match(rest[0]):
                return refuse("log-merge-end", "merge-end %s is not a result the audit reads" % rest[1], "a commit hash of 7 to 40 hex characters or one of %s: merge-end <NN> <hash>" % ", ".join(ABORT_WORDS), 2)
            return refuse("log-grammar", "the arguments after %s do not fit its grammar" % verb, LOG_USAGE[verb], 2)
        rest = normal_words(verb, rest)
        agent = rest[3] if verb == "dispatch" else rest[-1]
        if verb in ("dispatch", "foundation-read") and agent in [a for _, _, a in agent_lines(root, feature_name)]:
            return refuse("log-agent-id", "agent id %s is already in the %s log, and a second dispatch line would count its transcript twice" % (agent, feature_name), "`resume <NN> <role>`, the line for a resumed agent", 2)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("%s %s %s\n" % (time.strftime(LOG_TIME), verb, " ".join(rest)))
        return 0
    if not os.path.isfile(path):
        print("build log for %s: empty" % feature_name)
        return 0
    lines = read(path).rstrip("\n").split("\n")
    print("build log for %s (%d lines, last 40; whole file: %s)" % (feature_name, len(lines), path))
    for line in lines[-40:]:
        print(line)
    return 0


def cmd_open(root: str, config: dict, feature_name: str, text: str) -> int:
    """Appends a numbered item to the spec's `## Open list` (creating the section) and logs it."""
    spec = os.path.join(root, tracker_dir(config), feature_name, "spec.md")
    item = " ".join(text.split())
    if not item:
        print("gate: usage: open <feature> \"<item>\"")
        return 2
    lines = read(spec).rstrip("\n").split("\n")
    heading = next((i for i, line in enumerate(lines) if re.match(r"^##\s+Open list\b", line, re.I)), None)
    if heading is None:
        lines += ["", "## Open list", "", "1. " + item]
        number = 1
    else:
        stop = next((i for i in range(heading + 1, len(lines)) if re.match(r"^##\s", lines[i])), len(lines))
        last = None
        for i in range(heading + 1, stop):
            if re.match(r"^\d+\.\s", lines[i]):
                last = i
        number = int(re.match(r"^(\d+)\.", lines[last]).group(1)) + 1 if last is not None else 1
        at = stop
        while at > heading + 1 and not lines[at - 1].strip():
            at -= 1
        spaced = last is not None and last > 0 and not lines[last - 1].strip()
        lines[at:at] = ([""] if spaced or last is None else []) + ["%d. %s" % (number, item)]
    body = "\n".join(lines) + "\n"
    with open(spec, "w", encoding="utf-8") as handle:
        handle.write(body)
    cmd_log(root, feature_name, ["open", str(number), item])
    print("open: item %d added to %s" % (number, os.path.relpath(spec, root)))
    return 0
