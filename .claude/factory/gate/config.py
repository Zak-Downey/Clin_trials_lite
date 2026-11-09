"""Reading `factory.json`, checking it against `schema.json`, and the defaults a missing key takes."""
from __future__ import annotations

import glob
import json
import os
import re

from gate.refuse import refuse

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schema.json")
CONFIG_PATH = os.path.join("docs", "agents", "local", "factory.json")
GATE_TESTS = ".claude/factory/tests"


DEFAULT_RED_MARKERS = ("not ok", "FAIL:", "ERROR:", "\u2716")


def red_marker_regex(check: dict) -> "re.Pattern":
    """A check's red marker, compiled once, as a regular expression (the default when it names none)."""
    marker = check.get("red_marker") or "|".join(re.escape(m) for m in DEFAULT_RED_MARKERS)
    return re.compile(marker, re.IGNORECASE)


def schema_keys() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as handle:
        return json.load(handle)["keys"]


DEFAULT_CONFIG = {k: v["default"] for k, v in schema_keys().items() if v.get("default") is not None}


def without_comments(value):
    if isinstance(value, dict):
        return {k: without_comments(v) for k, v in value.items() if not k.startswith("$comment")}
    if isinstance(value, list):
        return [without_comments(v) for v in value]
    return value


def read_raw(root: str) -> dict:
    path = os.path.join(root, CONFIG_PATH)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        return without_comments(json.load(handle))


def load_config(root: str) -> dict:
    config = dict(DEFAULT_CONFIG)
    config.update(read_raw(root))
    config["tracker"] = normal_tracker(config["tracker"])  # factory-allow: load_config normalises the tracker folder once
    return config


def normal_tracker(value: str) -> str:
    """The tracker folder without a leading `./` or a trailing `/`."""
    value = value.strip()
    while value.startswith("./"):
        value = value[2:]
    return value.rstrip("/") or "."


def tracker_dir(config: dict) -> str:
    """The tracker folder: the one place a module reads it from the config."""
    return config["tracker"]  # factory-allow: the one accessor


def check_value(value, spec: dict, path: str, problems: list) -> None:
    kind = spec["type"]
    if kind == "string":
        ok = isinstance(value, str)
    elif kind == "integer":
        ok = isinstance(value, int) and not isinstance(value, bool)
    elif kind == "number":
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        if ok and value < 0:
            problems.append("%s is %s, which is negative" % (path, value))
            return
    elif kind == "list of string":
        ok = isinstance(value, list) and all(isinstance(v, str) for v in value)
    elif kind == "list of object":
        ok = isinstance(value, list) and all(isinstance(v, dict) for v in value)
    else:
        ok = isinstance(value, dict)
    if not ok:
        problems.append("%s must be a %s" % (path, kind))
        return
    if "enum" in spec:
        problems += ["%s has %r, which is not one of %s" % (path, v, ", ".join(spec["enum"])) for v in value if v not in spec["enum"]]
    if spec.get("regex"):
        try:
            if re.compile(value).search(""):
                problems.append("%s matches an empty line (an empty alternative such as a trailing |?)" % path)
        except re.error as error:
            problems.append("%s is not a regular expression (%s)" % (path, error))
    if "values" in spec:
        for name, item in value.items():
            check_value(item, spec["values"], "%s.%s" % (path, name), problems)
    if "fields" in spec:
        for n, item in enumerate(value if kind == "list of object" else [value]):
            check_fields(item, spec["fields"], "%s[%d]" % (path, n) if kind == "list of object" else path, problems)


def check_fields(obj: dict, fields: dict, path: str, problems: list) -> None:
    for key in obj:
        if key not in fields:
            problems.append("%s.%s is not a key the schema knows (gate.py config --keys lists them)" % (path, key))
    for key, spec in fields.items():
        if key in obj:
            check_value(obj[key], spec, "%s.%s" % (path, key), problems)
        elif spec.get("required"):
            problems.append("%s.%s is required" % (path, key))


def validate(raw: dict, root: str) -> tuple:
    """(problems, advice) for a factory.json already read: problems refuse, advice is printed."""
    keys, problems, advice = schema_keys(), [], []
    if not isinstance(raw, dict):
        return ["factory.json must be an object"], []
    check_fields(raw, keys, "factory.json", problems)
    for key, spec in keys.items():
        trigger = spec.get("required_when_nonempty")
        if trigger and raw.get(trigger) and not raw.get(key):
            problems.append("factory.json.%s is required when %s is not empty (the gate has no default for it)" % (key, trigger))
    if problems:
        return problems, advice
    config = load_config(root)
    for n, check in enumerate(config["checks"]):
        if "walk" in check.get("proves", []) and not config["evidence"].get("walk"):
            problems.append("factory.json.checks[%d].proves names walk, and factory.json.evidence.walk is empty" % n)
    named = [("evidence.test", p) for p in config["evidence"].get("test", [])] + [("evidence.walk", p) for p in config["evidence"].get("walk", [])]
    named += [("standins_doc", config["standins_doc"]), ("tracker", tracker_dir(config))]
    advice += ["%s: %s does not exist" % (key, path) for key, path in named if not os.path.exists(os.path.join(root, path))]
    tested = any(GATE_TESTS in c["command"] for c in config["checks"]) and GATE_TESTS in config["evidence"].get("test", [])
    if not tested:
        advice.append("no check runs the gate's own tests over %s, or that folder is not under evidence.test (a repo may choose not to run them)" % GATE_TESTS)
    for rule in config["forbid"]:
        if isinstance(rule, dict) and not forbid_files(root, rule):
            advice.append("forbid rule %s: paths %s match no file" % (rule.get("name", "?"), rule.get("paths", [])))
    if not config["mutate_paths"]:
        advice.append("no mutation runner is configured (mutate_paths is empty)")
    return problems, advice


def cmd_config(root: str, args: list) -> int:
    if args == ["--keys"]:
        for key, spec in schema_keys().items():
            default = "none" if spec.get("default") is None else json.dumps(spec["default"])
            print("%s  %s  default %s  %s" % (key, spec["type"], default, spec["meaning"]))
            for field, sub in {**spec.get("fields", {}), **spec.get("values", {}).get("fields", {})}.items():
                print("  .%s  %s%s  %s" % (field, sub["type"], " (required)" if sub.get("required") else "", sub["meaning"]))
        return 0
    if args:
        print("gate: usage: config [--keys]")
        return 2
    problems, advice = validate(read_raw(root), root)
    for problem in problems:
        print("factory.json: %s" % problem)
    if problems:
        return refuse("config-valid", "factory.json has %d problem(s), listed above" % len(problems), "each problem fixed in docs/agents/local/factory.json")
    effective = {k: v.get("default") for k, v in schema_keys().items()}
    effective.update(load_config(root))
    print(json.dumps(effective, indent=2))
    for line in advice:
        print("advice: %s" % line)
    return 0


def forbid_files(root: str, rule: dict) -> list:
    """Every file a forbid rule's paths name: a glob match, or each file under a matched directory."""
    files = set()
    for spec in rule.get("paths", []):
        for match in glob.glob(os.path.join(root, spec), recursive=True):
            if os.path.isdir(match):
                for folder, _, names in os.walk(match):
                    files.update(os.path.join(folder, name) for name in names)
            else:
                files.add(match)
    return sorted(files)


def refusals(root: str) -> list:
    """What stops a command that depends on factory.json: the problems `config` would print."""
    return validate(read_raw(root), root)[0]


ALLOW_RE = re.compile(r"(?<!`)factory-allow:\s+[\w]")


def allowed(line: str) -> bool:
    """Whether a line carries the allow marker with a why after it: `factory-allow: <why>`. A bare marker, a placeholder
    (`<why>`) and a marker quoted in backticks excuse nothing."""
    return bool(ALLOW_RE.search(line))


def read(path: str) -> str:
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read()


LEDGER_PATH = os.path.join("docs", "agents", "local", "ledger.md")
