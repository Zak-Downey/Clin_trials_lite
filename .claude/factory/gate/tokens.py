"""The tokens record (`gate.py stats --write`): one line per agent run and model in
docs/agents/local/tokens.jsonl, `{date, feature, ticket, role, agent, model, input, output, cache_read, cache_write}`.
The transcript shape it reads is stated in `gate.ledger.read_usage`."""
from __future__ import annotations

import bisect
import json
import os

from gate.config import read
from gate.ledger import projects_root, read_usage, transcript_path
from gate.log import agent_lines, log_times, parse_log_time
from gate.tracker import list_features

TOKENS_PATH = os.path.join("docs", "agents", "local", "tokens.jsonl")


def log_window(root: str, feature: str):
    """(first, last) of the build log's dated lines in epoch seconds, a last line without seconds taken to its minute's end, or None."""
    times = log_times(root, feature)
    start = parse_log_time(times[0]) if times else None
    end = parse_log_time(times[-1]) if times else None
    if start is None or end is None:
        return None
    return start, end + (59 if len(times[-1]) <= 16 else 0)


def line_epochs(root: str, feature: str):
    """(sorted epoch seconds of every dated line of the feature's build log, the window's end), or ([], None)."""
    epochs = sorted(t for t in (parse_log_time(x) for x in log_times(root, feature)) if t is not None)
    window = log_window(root, feature)
    return (epochs, window[1]) if window and epochs else ([], None)


def latest_owner(lines: dict, at: float):
    """The feature whose build log has the latest line at or before `at`, among the logs whose first-to-last window holds `at`,
    or None; a tie goes to the first name in sort order. A message after a fix round's last line is its parent's again."""
    best = None
    for name in sorted(lines):
        epochs, end = lines[name]
        i = bisect.bisect_right(epochs, at)
        if i and at <= end and (best is None or epochs[i - 1] > best[0]):
            best = (epochs[i - 1], name)
    return best[1] if best else None


def feature_records(root: str, feature: str, starts: dict = None):
    """(records, read count, not-found ids, notices): the feature's token lines, or none and a notice saying why.
    `starts` is every feature's `line_epochs`: an orchestrator message counts for the feature whose log has the
    latest line at or before it, so a fix round's window inside its parent's is counted once."""
    agents = agent_lines(root, feature)
    if not agents:
        return [], 0, [], ["no agent ids in the build log for %s; nothing written" % feature]
    if not os.path.isdir(projects_root()):
        return [], 0, [], ["no transcripts root at %s; nothing written" % projects_root()]
    window = log_window(root, feature)
    starts = dict(starts or {})
    starts[feature] = line_epochs(root, feature)
    date = log_times(root, feature)[0][:10]
    records, missing, sessions, read_count = [], [], [], 0
    for ticket, role, agent in agents:
        path = transcript_path(agent)
        usage = read_usage(path) if path else None
        if not usage:
            missing.append(agent)
            continue
        read_count += 1
        session = os.path.dirname(os.path.dirname(path))
        if session not in sessions:
            sessions.append(session)
        for model in sorted(usage):
            records.append(dict(date=date, feature=feature, ticket=ticket, role=role, agent=agent, model=model, **usage[model]))
    notices = []
    if sessions and window:
        session = sessions[0]
        name = os.path.basename(session)
        usage = None
        if not os.path.isfile(session + ".jsonl"):
            notices.append("orchestrator: %s.jsonl is not beside the subagents folder" % name)
        else:
            usage = read_usage(session + ".jsonl", window, lambda at: latest_owner(starts, at) == feature)
            if not usage:
                notices.append("orchestrator: no messages of %s.jsonl inside the build log's window" % name)
        for model in sorted(usage or {}):
            records.append(dict(date=date, feature=feature, ticket="-", role="orchestrator", agent=name, model=model, **usage[model]))
        if len(sessions) > 1:
            notices.append("orchestrator of %s not counted (agents ran in %d sessions; %s counted)" % (
                ", ".join(os.path.basename(x) for x in sessions[1:]), len(sessions), name))
    return records, read_count, missing, notices


def write_tokens(root: str, config: dict, features: list) -> list:
    """Replace the tokens record's lines for the named, already known, features; every other line is kept as it was.
    A feature that yields no lines leaves its old lines alone: the transcripts may be gone, the record is not.
    Prints what it did and returns the records it wrote (those of the replaced features), for `close` to total."""
    path = os.path.join(root, TOKENS_PATH)
    existing = [l for l in read(path).split("\n") if l.strip()] if os.path.isfile(path) else []
    starts = {name: line_epochs(root, name) for name in sorted(set(list_features(root, config)) | set(features))}
    written = []
    replaced = set()
    for feature in features:
        records, read_count, missing, notices = feature_records(root, feature, starts)
        if not records and not read_count:
            print("tokens: %s" % (notices[0] if notices else "%d agent(s) read, %d not found: %s; nothing written" % (0, len(missing), ", ".join(missing))))
            continue
        replaced.add(feature)
        written += records
        print("tokens: %d agent(s) read, %d not found%s" % (read_count, len(missing), ": " + ", ".join(missing) if missing else ""))
        for notice in notices:
            print("tokens: %s" % notice)

    def of_replaced(text):
        try:
            return json.loads(text).get("feature") in replaced
        except (ValueError, AttributeError):
            return False

    if replaced:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        text = "".join(l + "\n" for l in [l for l in existing if not of_replaced(l)] + [json.dumps(r) for r in written])
        with open(path + ".tmp", "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(path + ".tmp", path)
    return written


def cmd_stats_write(root: str, config: dict, features: list) -> int:
    write_tokens(root, config, features)
    return 0
