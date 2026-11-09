"""The dashboard page (`gate.py dashboard`): one static HTML page from the factory's own records.

It reads, all optional (a missing file is an empty section naming the command that fills it):
  docs/agents/local/builds.jsonl         one line per build, written by `close`
  docs/agents/local/escapes.jsonl        one line per escape, written by `ledger add`
  docs/agents/local/flakes.jsonl         one line per flake, written by `ready`
  docs/agents/local/tokens.jsonl         one line per agent run, written by `close` and `stats --write`
  docs/agents/local/github.jsonl         one line per usage item, written by `github`
  docs/agents/local/github-storage.json  the repository's artifact and cache bytes, written by `github`
  factory.json "prices"                  {"<model>": {"input": .., "output": .., "cache_read": .., "cache_write": ..}} in dollars per million tokens

Three parts: `load` reads the records, `compute` makes the figures, `render` makes one HTML string. Standard
library only, inline SVG and CSS, no script and nothing loaded from anywhere. A line that is not a JSON
object, or whose fields have the wrong type (`gate.records`), is skipped and counted in the page footer with the file.
"""
from __future__ import annotations

import html
import json
import os
import random
import re
import time
from collections import OrderedDict, defaultdict

from gate.config import read
from gate.git import run_git
from gate.ledger import ESCAPE_GATES, LATER_GATES
from gate.pricing import KINDS, number, priced_cost, read_prices
from gate.records import read_records

LOCAL = os.path.join("docs", "agents", "local")
ROLE_ORDER = ("implementer", "ticket-reviewer", "merger", "standards-reviewer", "branch-reviewer", "review-merger", "orchestrator")
GATE_COLORS = ("#5fc9d9", "#e8b45a", "#b58ff4", "#ee8fb4", "#7fd49a", "#f0a06a", "#9fb4cf", "#e38282", "#c9d65f", "#6a8ff0")
ROLE_COLORS = ("#5fc9d9", "#3fa3b3", "#2a7d8a", "#9fb4cf", "#b58ff4", "#8c66d6", "#e8b45a", "#f0a06a", "#7fd49a", "#ee8fb4")
EMPTY = {
    "builds": "No builds recorded. <code>gate.py close &lt;feature&gt;</code> writes docs/agents/local/builds.jsonl.",
    "escapes": "No escapes recorded. <code>gate.py ledger add</code> writes docs/agents/local/escapes.jsonl.",
    "tokens": "No token records. <code>gate.py close &lt;feature&gt;</code> or <code>gate.py stats --write &lt;feature&gt;</code> writes docs/agents/local/tokens.jsonl.",
    "flakes": "No flakes recorded. <code>gate.py ready &lt;feature&gt;</code> writes docs/agents/local/flakes.jsonl when a check flakes.",
    "github": "No usage recorded. <code>gate.py github</code> writes docs/agents/local/github.jsonl.",
}


def read_jsonl(path: str):
    """(records, skipped): the well-typed JSON objects of the record file, and how many non-blank lines were not (see `gate.records`)."""
    return read_records(path)


def read_object(path: str):
    """(object, skipped): the file's JSON object, or {} and 1 when it exists and is not one."""
    if not os.path.isfile(path):
        return {}, 0
    try:
        value = json.loads(read(path))
    except ValueError:
        return {}, 1
    return (value, 0) if isinstance(value, dict) else ({}, 1)


def load(root: str, config: dict) -> dict:
    here = os.path.join(root, LOCAL)
    data, skipped, where = {}, 0, []
    for name in ("builds", "escapes", "flakes", "tokens", "github"):
        data[name], more = read_records(os.path.join(here, name + ".jsonl"))
        skipped += more
        if more:
            where.append("%s.jsonl %d" % (name, more))
    data["storage"], more = read_object(os.path.join(here, "github-storage.json"))
    data["prices"] = read_prices(config)
    data["skipped"] = skipped + more
    data["skipped_in"] = ", ".join(where + (["github-storage.json 1"] if more else []))
    return data


def sample() -> dict:
    """Invented figures, to show a filled page before a first build closes."""
    rng = random.Random(7)
    data = {"builds": [], "escapes": [], "flakes": [], "tokens": [], "github": [], "skipped": 0, "skipped_in": ""}
    names = ("first-feature", "second-feature", "third-feature", "fourth-feature")
    days = ("2026-11-02", "2026-11-06", "2026-11-14", "2026-11-21")
    count = 0
    for i, (name, day) in enumerate(zip(names, days)):
        tickets = (12, 16, 18, 9)[i]
        data["builds"].append({"date": day, "feature": name, "tip": "a%dc3f9e" % i, "tickets": tickets, "reviews": tickets,
                               "blocking": (9, 14, 11, 4)[i], "mutants_tried": (0, 50, 54, 27)[i], "mutants_survived": (0, 14, 6, 2)[i],
                               "boxes_proved": (44, 88, 97, 51)[i], "boxes_human": (2, 3, 9, 2)[i], "hours": (9.5, 11.2, 13.0, 6.1)[i], "guard_refusals": (0, 1, 2, 0)[i],
                               "subagents": {"implementer": tickets, "ticket-reviewer": tickets, "merger": tickets, "branch-reviewer": 4, "orchestrator": 1}})
        for _ in range((12, 10, 6, 3)[i]):
            count += 1
            data["escapes"].append({"date": day, "feature": name, "id": "E-%03d" % count, "class": rng.choice(("blocking", "blocking", "sweep", "nit", "design")),
                                    "found_by": rng.choice(("branch-review", "branch-review", "re-check", "user", "walk")),
                                    "should_have_been": rng.choice(("ticket-review", "ticket-review", "walk", "unit", "exploration")), "fixed_in": "%02d" % rng.randint(1, tickets), "rule_id": "", "flake": ""})
        for t in range(tickets):
            for role in ("implementer", "ticket-reviewer", "merger"):
                data["tokens"].append({"date": day, "feature": name, "ticket": "%02d" % (t + 1), "role": role, "model": "model-a",
                                       "input": rng.randint(18000, 70000), "output": rng.randint(4000, 16000), "cache_read": rng.randint(120000, 400000), "cache_write": rng.randint(20000, 60000)})
        for role, ticket in (("branch-reviewer", "-"), ("orchestrator", "-")):
            data["tokens"].append({"date": day, "feature": name, "ticket": ticket, "role": role, "model": "model-b",
                                   "input": rng.randint(60000, 140000), "output": rng.randint(8000, 22000), "cache_read": rng.randint(300000, 900000), "cache_write": rng.randint(40000, 120000)})
        for _ in range((0, 2, 3, 1)[i]):
            data["flakes"].append({"date": day, "feature": name, "file": "checks/a", "title": rng.choice(("the form opens", "a restart keeps the pack")), "tip": "a%dc3f9e" % i})
    for day in range(1, 23):
        minutes = rng.choice((0, 0, 12, 38, 64, 120))
        if minutes:
            data["github"].append({"date": "2026-11-%02d" % day, "product": "actions", "sku": "Actions Linux", "quantity": minutes, "unitType": "Minutes", "netAmount": round(minutes * 0.008, 2), "repositoryName": "owner/repo"})
        data["github"].append({"date": "2026-11-%02d" % day, "product": "shared storage", "sku": "Shared Storage", "quantity": round(0.9 + day * 0.07, 2), "unitType": "gb-hours", "netAmount": round((0.9 + day * 0.07) * 0.008, 3), "repositoryName": "owner/repo"})
    data["storage"] = {"artifacts_bytes": 1340000000, "caches_bytes": 812000000, "fetched": "2026-11-22T08:10:00Z"}
    data["prices"] = {"model-a": {"input": 3, "output": 15, "cache_read": 0.3, "cache_write": 3.75}, "model-b": {"input": 15, "output": 75, "cache_read": 1.5, "cache_write": 18.75}}
    return data


def feature_names(text) -> list:
    """`ready` writes the features of one run as a comma-separated list."""
    return [part.strip() for part in str(text).split(",")]


def count_flakes(records, names) -> int:
    """The flakes recorded for any of these features: one record is one flake, however many features its `ready` named."""
    wanted = set(names)
    return len([r for r in records if wanted & set(feature_names(r.get("feature", "")))])


def compute(data: dict) -> dict:
    prices = data["prices"]
    builds = sorted((b for b in data["builds"] if b.get("feature")), key=lambda b: str(b.get("date", "")))
    by_feature_escapes = defaultdict(list)
    for e in data["escapes"]:
        by_feature_escapes[e.get("feature")].append(e)
    by_role = defaultdict(lambda: defaultdict(lambda: {"tokens": 0, "cost": 0.0, "runs": 0, "agents": set(), "unpriced": set(), "priced": 0}))
    for t in data["tokens"]:
        if not t.get("feature") or not t.get("role"):
            continue
        cell = by_role[t["feature"]][t["role"]]
        cell["tokens"] += sum(number(t.get(kind)) for kind in KINDS)
        if (t.get("ticket"), t.get("agent")) not in cell["agents"]:  # an agent on two models is one run
            cell["agents"].add((t.get("ticket"), t.get("agent")))
            cell["runs"] += 1
        cost = priced_cost(t, prices)
        if cost is None:
            cell["unpriced"].add(str(t.get("model", "")) or "unknown model")
        else:
            cell["cost"] += cost
            cell["priced"] += 1
    flakes_by_title = defaultdict(int)
    for f in data["flakes"]:
        flakes_by_title[(str(f.get("file", "")), str(f.get("title", "")))] += 1
    closes = OrderedDict()  # one close = the builds rows with the same tip and date: a build and its fix round are one build
    for b in builds:
        closes.setdefault((str(b.get("tip", "")), str(b.get("date", ""))), []).append(b)
    groups = [(", ".join(dict.fromkeys(b["feature"] for b in group)), group, False) for group in closes.values()]
    built = {b["feature"] for b in builds}
    stray = sorted({f for f in list(by_feature_escapes) + [t.get("feature") for t in data["tokens"]] if f and f not in built})
    for name in stray:  # records of a feature with no builds row still show, marked
        dates = [str(r.get("date", "")) for r in by_feature_escapes.get(name, []) + [t for t in data["tokens"] if t.get("feature") == name]]
        groups.append((name, [{"feature": name, "date": min(dates)}], True))
    groups.sort(key=lambda g: str(g[1][0].get("date", "")))
    rows = []
    for name, group, no_builds in groups:
        features = list(dict.fromkeys(b["feature"] for b in group))
        escapes = [e for f in features for e in by_feature_escapes.get(f, [])]
        cells = [c for f in features for c in by_role.get(f, {}).values()]
        tickets = sum(number(b.get("tickets")) for b in group)
        tokens = sum(c["tokens"] for c in cells)
        unpriced = set().union(*(c["unpriced"] for c in cells)) if cells else set()
        tried, survived = (int(sum(number(b.get(k)) for b in group)) for k in ("mutants_tried", "mutants_survived"))
        subagents = {}
        for b in group:
            for role, n in (b.get("subagents") if isinstance(b.get("subagents"), dict) else {}).items():
                subagents[role] = subagents.get(role, 0) + number(n)
        hours = [b.get("hours") for b in group if isinstance(b.get("hours"), (int, float))]
        rows.append({
            "feature": name, "features": features, "no_builds": no_builds, "date": str(group[0].get("date", "")), "tip": str(group[0].get("tip", "")), "tickets": int(tickets),
            "blocking": int(sum(number(b.get("blocking")) for b in group)),
            "escapes": len(escapes), "late": len([e for e in escapes if e.get("found_by") in LATER_GATES]),
            "user_found": len([e for e in escapes if e.get("found_by") == "user"]),
            "misclass": len([e for e in escapes if e.get("class") in ("nit", "sweep") and e.get("found_by") in LATER_GATES]),
            "escapes_per_ticket": len(escapes) / tickets if tickets else 0.0,
            "mutants": "%d/%d" % (survived, tried) if tried else "-", "mutants_survived": survived,
            "boxes": "%d + %d" % (sum(number(b.get("boxes_proved")) for b in group), sum(number(b.get("boxes_human")) for b in group)),
            "subagents": int(sum(subagents.values())),
            "has_tokens": bool(cells), "has_priced": any(c["priced"] for c in cells), "mutants_tried": tried,
            "tokens": tokens, "tokens_per_ticket": tokens / tickets if tickets else 0.0,
            "cost": sum(c["cost"] for c in cells), "unpriced": unpriced,
            "flakes": count_flakes(data["flakes"], features), "guard": int(sum(number(b.get("guard_refusals")) for b in group)),
            "hours": sum(hours) if hours else None,
        })
    names = [r["feature"] for r in rows]
    merged = {}
    for r in rows:
        cell_of = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "runs": 0, "unpriced": set()})
        for f in r["features"]:
            for role, c in by_role.get(f, {}).items():
                m = cell_of[role]
                m["tokens"] += c["tokens"]
                m["cost"] += c["cost"]
                m["runs"] += c["runs"]
                m["unpriced"] |= c["unpriced"]
        merged[r["feature"]] = dict(cell_of)
    escapes_by = {r["feature"]: _count([e for f in r["features"] for e in by_feature_escapes.get(f, [])], "should_have_been") for r in rows}
    gates_seen = {e.get("should_have_been") for e in data["escapes"]}
    gates = [g for g in ESCAPE_GATES if g in gates_seen] + sorted(str(g) for g in gates_seen if g not in ESCAPE_GATES and g)
    roles_seen = {r for name in names for r in merged.get(name, {})}
    roles = [r for r in ROLE_ORDER if r in roles_seen] + sorted(r for r in roles_seen if r not in ROLE_ORDER)
    actions, storage_days, costs, other_units = OrderedDict(), OrderedDict(), defaultdict(float), OrderedDict()
    month = max((str(g.get("date", ""))[:7] for g in data["github"]), default="")
    for g in sorted((g for g in data["github"] if str(g.get("date", ""))[:7] == month), key=lambda g: str(g.get("date", ""))):
        unit = str(g.get("unitType", "")).lower()
        day = str(g.get("date", ""))
        if unit.startswith("minute"):
            actions[day] = actions.get(day, 0) + number(g.get("quantity"))
            costs["actions"] += number(g.get("netAmount"))
        elif re.sub(r"[^a-z0-9]", "", unit) in ("gigabytehours", "gbhours"):
            storage_days[day] = storage_days.get(day, 0) + number(g.get("quantity"))
            costs["storage"] += number(g.get("netAmount"))
        else:
            name = str(g.get("unitType", "")) or "(no unit)"
            other_units[name] = other_units.get(name, 0) + number(g.get("quantity"))
    return {"rows": rows, "names": names, "gates": gates, "roles": roles, "by_role": merged, "escapes_by": escapes_by,
            "flake_titles": sorted(flakes_by_title.items(), key=lambda kv: (-kv[1], kv[0])), "actions": actions, "storage_days": storage_days, "other_units": other_units, "costs": costs, "month": month,
            "storage": data["storage"] if ("artifacts_bytes" in data["storage"] or "caches_bytes" in data["storage"]) else {}, "storage_why": str(data["storage"].get("usage", "")), "priced": bool(prices), "recent": [e for _, e in sorted(enumerate(data["escapes"]), key=lambda ie: (str(ie[1].get("date", "")), ie[0]), reverse=True)][:12],
            "has_github": bool(data["github"]), "skipped": data["skipped"], "skipped_in": data["skipped_in"], "unpriced": sorted({m for r in rows for m in r["unpriced"]})}


def _count(items: list, key: str) -> dict:
    counts = defaultdict(int)
    for item in items:
        counts[item.get(key)] += 1
    return counts


def fmt_tokens(n: float) -> str:
    if n >= 1e6:
        return "%.1fM" % (n / 1e6)
    if n >= 1e3:
        return "%.0fk" % (n / 1e3)
    return str(int(n))


def fmt_money(x) -> str:
    return "-" if x is None else "${:,.2f}".format(x)


def plain_number(q: float) -> str:
    """A quantity without exponent form: 1234567, 0.5."""
    return ("%.6f" % q).rstrip("0").rstrip(".")


def fmt_bytes(b: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return "%.1f %s" % (b, unit)
        b /= 1024
    return "%.1f TB" % b


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def cost_text(cost: float, unpriced, priced: bool) -> str:
    """Money for a figure: nothing without prices, `unpriced` for a model with no price (never zero)."""
    if not priced:
        return "-"
    if unpriced:
        return "%s + unpriced" % fmt_money(cost) if cost else "unpriced"
    return fmt_money(cost)


def bars_svg(series: list, labels: list, colors, unit: str = "") -> str:
    """Stacked columns, one per label; series is [(name, [value per label])]."""
    width, height = 560, 150
    pad_l, pad_b, pad_t = 44, 34, 8
    n = len(labels)
    vmax = max([sum(s[1][i] for s in series) for i in range(n)] or [0]) or 1
    cw = (width - pad_l - 8) / n
    bw = min(cw * 0.6, 56)
    out = ['<svg viewBox="0 0 %d %d" role="img" aria-label="column chart" class="chart">' % (width, height)]
    for frac in (0, 0.5, 1):
        y = pad_t + (height - pad_t - pad_b) * (1 - frac)
        value = vmax * frac
        out.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" class="grid"/>' % (pad_l, y, width - 8, y))
        out.append('<text x="%d" y="%.1f" text-anchor="end" class="tick">%s</text>' % (pad_l - 6, y + 4, ("$%g" % value) if unit == "$" else "%g%s" % (value, unit)))
    for i, label in enumerate(labels):
        x = pad_l + cw * i + (cw - bw) / 2
        y0 = height - pad_b
        for (name, values), color in zip(series, colors):
            h = (height - pad_t - pad_b) * values[i] / vmax
            out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"><title>%s: %g</title></rect>' % (x, y0 - h, bw, h, color, esc(name), values[i]))
            y0 -= h
        short = label if len(label) <= 14 else label[:13] + "..."
        out.append('<text x="%.1f" y="%d" text-anchor="middle" class="tick">%s</text>' % (x + bw / 2, height - pad_b + 16, esc(short)))
    out.append("</svg>")
    return "".join(out)


def line_svg(points: list, unit: str = "", color: str = "var(--accent)") -> str:
    width, height = 560, 120
    pad_l, pad_b, pad_t = 44, 26, 8
    vmax = max(v for _, v in points) or 1
    n = len(points)
    xs = [pad_l + (width - pad_l - 8) * (i / max(n - 1, 1)) for i in range(n)]
    ys = [pad_t + (height - pad_t - pad_b) * (1 - v / vmax) for _, v in points]
    out = ['<svg viewBox="0 0 %d %d" role="img" aria-label="line chart" class="chart">' % (width, height)]
    for frac in (0, 1):
        y = pad_t + (height - pad_t - pad_b) * (1 - frac)
        out.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" class="grid"/>' % (pad_l, y, width - 8, y))
        out.append('<text x="%d" y="%.1f" text-anchor="end" class="tick">%g%s</text>' % (pad_l - 6, y + 4, vmax * frac, unit))
    path = "M " + " L ".join("%.1f %.1f" % (x, y) for x, y in zip(xs, ys))
    out.append('<path d="%s L %.1f %d L %.1f %d Z" fill="%s" opacity="0.12"/>' % (path, xs[-1], height - pad_b, xs[0], height - pad_b, color))
    out.append('<path d="%s" fill="none" stroke="%s" stroke-width="2"/>' % (path, color))
    out.append('<circle cx="%.1f" cy="%.1f" r="3.5" fill="%s"/>' % (xs[-1], ys[-1], color))
    for i in sorted({0, n - 1}):
        out.append('<text x="%.1f" y="%d" text-anchor="%s" class="tick">%s</text>' % (xs[i], height - 8, "start" if i == 0 else "end", esc(points[i][0][5:])))
    out.append("</svg>")
    return "".join(out)


def empty(kind: str) -> str:
    return '<p class="empty">%s</p>' % EMPTY[kind]


def delta(cur, old, good_when: str = "down", fmt=lambda v: "%g" % v) -> str:
    if old is None or cur is None:
        return ""
    d = cur - old
    if d == 0:
        return '<span class="delta flat">no change</span>'
    better = d < 0 if good_when == "down" else d > 0
    return '<span class="delta %s">%s%s vs last</span>' % ("good" if better else "bad", "+" if d > 0 else "-", fmt(abs(d)))


def kpi_tiles(M: dict) -> list:
    rows = [r for r in M["rows"] if not r["no_builds"]]
    last = rows[-1] if rows else None
    prev = rows[-2] if len(rows) > 1 else None
    tiles = []
    if last:
        tiles.append(("Escapes per ticket", "%.2f" % last["escapes_per_ticket"], delta(last["escapes_per_ticket"], prev and prev["escapes_per_ticket"], "down", lambda v: "%.2f" % v), "defects found after the ticket closed, over tickets"))
        tiles.append(("Found by you", str(last["user_found"]), delta(last["user_found"], prev and prev["user_found"]), "escapes whose found_by is the user; the number the factory exists to hold at zero"))
        fix = "gate.py stats --write %s" % " ".join(last["features"])
        if not last["has_tokens"]:
            tiles.append(("Tokens per ticket", "no records", "", "no token records for this build: %s writes them" % fix))
        else:
            old = prev["tokens_per_ticket"] if prev is not None and prev["has_tokens"] else None
            tiles.append(("Tokens per ticket", fmt_tokens(last["tokens_per_ticket"]), delta(last["tokens_per_ticket"], old, "down", fmt_tokens), "every agent's tokens for the build, over tickets"))
        if not last["has_tokens"]:
            tiles.append(("Build cost", "no records", "", "no token records for this build: %s writes them" % fix))
        elif M["priced"]:
            value = "unpriced" if not last["has_priced"] else fmt_money(last["cost"]) + (" + unpriced" if last["unpriced"] else "")
            both = prev is not None and prev["has_priced"] and last["has_priced"] and not last["unpriced"] and not prev["unpriced"]
            note = "from factory.json prices" + ("; unpriced: %s" % ", ".join(sorted(last["unpriced"])) if last["unpriced"] else "")
            tiles.append(("Build cost", esc(value), delta(last["cost"], prev["cost"], "down", lambda v: "$%.2f" % v) if both else "", note))
        else:
            tiles.append(("Build cost", fmt_tokens(last["tokens"]) + " tok", "", "no prices set: add prices to factory.json (gate.py config --keys shows the shape)"))
        mutants_old = prev["mutants_survived"] if prev is not None and prev["mutants_tried"] and last["mutants_tried"] else None
        tiles.append(("Surviving mutants", last["mutants"], delta(last["mutants_survived"], mutants_old) if mutants_old is not None else "", "survived / tried; every survivor must be shown red before merge"))
        tiles.append(("Flakes", str(last["flakes"]), delta(last["flakes"], prev and prev["flakes"]), "checks red under load, green alone"))
    storage = M["storage"]
    minutes = sum(M["actions"].values())
    tiles.append(("GitHub Actions", ("%g min" % minutes) if M["has_github"] else "-", '<span class="delta flat">%s in %s</span>' % (fmt_money(M["costs"].get("actions", 0)), esc(M["month"])) if M["has_github"] else "",
                  "billable minutes in %s from the billing usage report" % M["month"] if M["has_github"] else "no usage yet: gate.py github fetches it"))
    total = number(storage.get("artifacts_bytes")) + number(storage.get("caches_bytes"))
    tiles.append(("GitHub storage", fmt_bytes(total) if storage else "-",
                  '<span class="delta flat">artifacts %s - caches %s</span>' % (fmt_bytes(number(storage.get("artifacts_bytes"))), fmt_bytes(number(storage.get("caches_bytes")))) if storage else "",
                  "current storage, fetched %s" % storage.get("fetched", "") if storage else "no storage yet: gate.py github fetches it"))
    return tiles


STYLE = """:root { --bg:#f5f7fb; --surf:#ffffff; --surf2:#eef2f8; --line:#d5dce8; --fg:#1b2433; --mute:#5b6a82; --accent:#b7791f; --good:#1f7a3d; --warn:#b7791f; --bad:#b83232; color-scheme: light dark; }
@media (prefers-color-scheme: dark) { :root { --bg:#0d1320; --surf:#151d2c; --surf2:#1b2536; --line:#2b3850; --fg:#e7edf7; --mute:#8d9bb3; --accent:#e8b45a; --good:#7fd49a; --warn:#e8b45a; --bad:#e38282; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font: 14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; padding: 24px 16px 48px; }
header { display:flex; flex-wrap:wrap; align-items:baseline; gap:8px 20px; margin-bottom:18px; }
h1 { font-size:1.3rem; margin:0; font-weight:600; }
header .meta { color:var(--mute); font-size:.85rem; }
h2 { font-size:.8rem; letter-spacing:.08em; text-transform:uppercase; color:var(--mute); margin:0 0 10px; font-weight:600; }
section { margin-bottom:28px; }
.kpis { display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap:10px; }
.kpi { background:var(--surf); border:1px solid var(--line); border-radius:8px; padding:12px 14px; min-width:0; overflow-wrap:anywhere; }
.kpi-label { font-size:.78rem; color:var(--mute); }
.kpi-value { font-size:1.6rem; font-weight:600; font-variant-numeric: tabular-nums; margin:2px 0; }
.kpi-delta { font-size:.78rem; min-height:1.2em; }
.kpi-note { font-size:.72rem; color:var(--mute); margin-top:4px; }
.delta.good { color:var(--good); } .delta.bad { color:var(--bad); } .delta.flat { color:var(--mute); }
.good { color:var(--good); } .warn { color:var(--warn); } .bad { color:var(--bad); }
.grid2 { display:grid; grid-template-columns: repeat(auto-fit, minmax(min(320px,100%), 1fr)); gap:14px; }
.card { background:var(--surf); border:1px solid var(--line); border-radius:8px; padding:14px; min-width:0; }
.card h2 { margin-bottom:8px; }
.chart { width:100%; height:auto; display:block; }
.chart .grid { stroke:var(--line); stroke-width:1; }
.chart .tick { fill:var(--mute); font-size:10px; }
.legend { display:flex; flex-wrap:wrap; gap:6px 14px; margin-top:6px; font-size:.78rem; color:var(--mute); }
.lg i { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:5px; vertical-align:-1px; }
.tablewrap { overflow-x:auto; }
table { border-collapse:collapse; width:100%; font-size:.85rem; font-variant-numeric: tabular-nums; }
th, td { text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); white-space:nowrap; vertical-align:top; }
th { color:var(--mute); font-weight:600; font-size:.75rem; letter-spacing:.04em; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size:.85em; color:var(--mute); }
.empty { color:var(--mute); font-size:.85rem; margin:0; }
.banner { background:var(--surf2); border:1px dashed var(--accent); color:var(--accent); border-radius:6px; padding:8px 12px; font-size:.85rem; margin-bottom:16px; }
footer { color:var(--mute); font-size:.75rem; margin-top:30px; line-height:1.6; }
"""


def no_records(r: dict) -> str:
    return 'no records<br><code>%s</code>' % esc("gate.py stats --write %s" % " ".join(r["features"]))


def render(M: dict, generated: str, sample_mode: bool) -> str:
    rows, names = M["rows"], M["names"]
    last = ([r for r in rows if not r["no_builds"]] or [None])[-1]
    kpis = kpi_tiles(M)
    kpi_html = "".join('<div class="kpi"><div class="kpi-label">%s</div><div class="kpi-value">%s</div><div class="kpi-delta">%s</div><div class="kpi-note">%s</div></div>' % (esc(l), v, d, esc(n)) for l, v, d, n in kpis)
    if not last:
        kpi_html = '<p class="empty">No builds yet, so no build figures. <code>gate.py close &lt;feature&gt;</code> writes them.</p>' + '<div class="kpis">' + kpi_html + "</div>"
    else:
        kpi_html = '<div class="kpis">' + kpi_html + "</div>"
    head = ["Build", "Date", "Tickets", "Blocking", "Escapes", "Late", "By you", "Misclass", "Mutants", "Boxes", "Subagents", "Tokens", "Cost", "Flakes", "Guard", "Hours"]
    body = []
    for r in rows:
        cells = ['<b>%s</b><br><code>%s</code>' % (esc(r["feature"]), "no builds row" if r["no_builds"] else esc(r["tip"])), esc(r["date"]), "" if r["no_builds"] else r["tickets"], r["blocking"], r["escapes"], r["late"],
                 '<span class="%s">%d</span>' % ("bad" if r["user_found"] else "good", r["user_found"]), r["misclass"], esc(r["mutants"]), esc(r["boxes"]), r["subagents"],
                 fmt_tokens(r["tokens"]) if r["has_tokens"] else no_records(r), esc(cost_text(r["cost"], r["unpriced"], M["priced"])) if r["has_tokens"] else no_records(r), r["flakes"], r["guard"], ("%g" % r["hours"]) if r["hours"] is not None else "-"]
        body.append("<tr>" + "".join("<td>%s</td>" % c for c in cells) + "</tr>")
    builds_table = '<div class="tablewrap"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % ("".join("<th>%s</th>" % h for h in head), "".join(body)) if rows else empty("builds")
    gates = M["gates"]
    gates_chart = bars_svg([(g, [M["escapes_by"][n].get(g, 0) for n in names]) for g in gates], names, [GATE_COLORS[ESCAPE_GATES.index(g) % len(GATE_COLORS)] if g in ESCAPE_GATES else "#8d9bb3" for g in gates]) if gates and names else empty("escapes")
    gates_legend = "".join('<span class="lg"><i style="background:%s"></i>%s</span>' % (GATE_COLORS[ESCAPE_GATES.index(g) % len(GATE_COLORS)] if g in ESCAPE_GATES else "#8d9bb3", esc(g)) for g in gates)
    roles = M["roles"]
    role_colors = {r: ROLE_COLORS[i % len(ROLE_COLORS)] for i, r in enumerate(roles)}
    if roles and M["priced"]:
        roles_chart = bars_svg([(r, [round(M["by_role"][n].get(r, {}).get("cost", 0), 2) for n in names]) for r in roles], names, [role_colors[r] for r in roles], unit="$")
        what = "cost"
    elif roles:
        roles_chart = bars_svg([(r, [round(M["by_role"][n].get(r, {}).get("tokens", 0) / 1e6, 2) for n in names]) for r in roles], names, [role_colors[r] for r in roles], unit="M")
        what = "tokens"
    else:
        roles_chart, what = empty("tokens"), "tokens"
    roles_legend = "".join('<span class="lg"><i style="background:%s"></i>%s</span>' % (role_colors[r], esc(r)) for r in roles)
    unpriced_note = '<p class="empty">Unpriced (no entry in prices, not counted as free): %s.</p>' % esc(", ".join(M["unpriced"])) if M["priced"] and M["unpriced"] else ""
    role_rows = ""
    if last:
        for r in roles:
            v = M["by_role"].get(last["feature"], {}).get(r)
            if v:
                role_rows += "<tr><td>%s</td><td>%d</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (esc(r), v["runs"], fmt_tokens(v["tokens"]), fmt_tokens(v["tokens"] / v["runs"]), esc(cost_text(v["cost"], v["unpriced"], M["priced"])))
    role_table = '<div class="tablewrap"><table><thead><tr><th>Role</th><th>Runs</th><th>Tokens</th><th>Per run</th><th>Cost</th></tr></thead><tbody>%s</tbody></table></div>' % role_rows if role_rows else empty("tokens")
    actions = list(M["actions"].items())
    storage = M["storage"]
    storage_note = (" - artifacts %s, caches %s, fetched %s" % (fmt_bytes(number(storage.get("artifacts_bytes"))), fmt_bytes(number(storage.get("caches_bytes"))), storage.get("fetched", ""))) if storage else ""
    why = M["storage_why"]
    no_usage = '<p class="empty">%s</p>' % esc(why) if why else empty("github")
    if M["other_units"]:
        other_note = '<p class="empty">Other units on the bill this month, not charted: %s</p>' % esc(", ".join("%s %s" % (plain_number(q), u) for u, q in M["other_units"].items()))
    else:
        other_note = ""
    actions_html = line_svg(actions, " min") + '<p class="empty">%s net in %s - from <code>gate.py github</code></p>' % (fmt_money(M["costs"].get("actions", 0)), esc(M["month"])) if actions else no_usage + other_note
    no_usage = other_note or no_usage
    storage_html = line_svg(list(M["storage_days"].items()), " GB-hours", "#b58ff4") + '<p class="empty">%s net in %s, billed per day%s</p>' % (fmt_money(M["costs"].get("storage", 0)), esc(M["month"]), esc(storage_note)) + other_note if M["storage_days"] else no_usage
    flake_rows = "".join('<tr><td>%s</td><td>%s</td><td><span class="%s">%d</span></td></tr>' % (esc(title), esc(file), "bad" if n >= 3 else "warn" if n == 2 else "", n) for (file, title), n in M["flake_titles"])
    flakes_html = '<div class="tablewrap"><table><thead><tr><th>Check</th><th>File</th><th>Count</th></tr></thead><tbody>%s</tbody></table></div><p class="empty">Three for one title refuses the ready stamp until the ledger ties it.</p>' % flake_rows if flake_rows else empty("flakes")
    esc_rows = "".join("<tr><td><code>%s</code></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % tuple(
        esc(e.get(k) or "-") for k in ("id", "date", "feature", "class", "found_by", "should_have_been", "fixed_in", "rule_id")) for e in M["recent"])
    esc_table = '<div class="tablewrap"><table><thead><tr><th>Id</th><th>Date</th><th>Build</th><th>Class</th><th>Found by</th><th>Should have been</th><th>Fixed in</th><th>Rule</th></tr></thead><tbody>%s</tbody></table></div>' % esc_rows if esc_rows else empty("escapes")
    banner = '<div class="banner">These are invented figures, to show a filled page. Run <code>gate.py dashboard</code> without <code>--sample</code> to see this repository\'s builds.</div>' if sample_mode else ""
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Factory dashboard</title>
<style>
%(style)s</style></head><body>
<header><h1>Factory dashboard</h1><span class="meta">%(builds)d builds - generated %(generated)s</span></header>
%(banner)s
<section><h2>Is it working</h2>%(kpis)s</section>
<section><h2>Builds</h2><div class="card">%(table)s
<p class="empty" style="margin-top:6px">Late = found at one of: %(late)s. Misclass = marked nit or sweep, then found later. Boxes = proved + needs-human.</p></div></section>
<section class="grid2">
  <div class="card"><h2>Where failures are: escapes by the gate that should have caught them</h2>%(gates)s<div class="legend">%(gates_legend)s</div></div>
  <div class="card"><h2>What it costs: %(what)s by role per build</h2>%(roles)s<div class="legend">%(roles_legend)s</div>%(unpriced)s</div>
</section>
<section class="grid2">
  <div class="card"><h2>Last build by role</h2>%(role_table)s</div>
  <div class="card"><h2>Recent escapes</h2>%(esc_table)s</div>
</section>
<section class="grid2">
  <div class="card"><h2>GitHub Actions minutes per day</h2>%(actions)s</div>
  <div class="card"><h2>GitHub shared storage (GB-hours billed) per day</h2>%(storage)s</div>
</section>
<section class="grid2">
  <div class="card"><h2>Flakes by walk (all builds)</h2>%(flakes)s</div>
</section>
<footer>%(skipped)d line(s) skipped as unreadable or of the wrong type%(skipped_in)s. Sources: builds.jsonl (gate.py close) - escapes.jsonl (gate.py ledger add) - flakes.jsonl (gate.py ready) - tokens.jsonl (gate.py close, gate.py stats --write) - github.jsonl and github-storage.json (gate.py github). Nothing on this page is judged by the page; it counts what the gates recorded.</footer>
</body></html>
""" % {"late": esc(", ".join(LATER_GATES)), "builds": len([r for r in M["rows"] if not r["no_builds"]]), "generated": esc(generated), "banner": banner, "kpis": kpi_html, "table": builds_table, "gates": gates_chart, "gates_legend": gates_legend,
       "what": what, "roles": roles_chart, "roles_legend": roles_legend, "unpriced": unpriced_note, "role_table": role_table, "esc_table": esc_table, "actions": actions_html,
       "storage": storage_html, "flakes": flakes_html, "skipped": M["skipped"], "skipped_in": html.escape(" (%s)" % M["skipped_in"]) if M["skipped_in"] else "", "style": STYLE}


def output_path(root: str, out):
    if out:
        return os.path.abspath(out)
    common = run_git(root, "rev-parse", "--git-common-dir")
    if common is None:
        return None
    return os.path.join(common if os.path.isabs(common) else os.path.join(root, common), "factory", "dashboard.html")


def cmd_dashboard(root: str, config: dict, out, sample_mode: bool) -> int:
    """Write the page to `out` (None: the git common directory's factory folder), from invented figures when `sample_mode`."""
    path = output_path(root, out)
    if path is None:
        print("dashboard: not a git repository; give a path to write to")
        return 1
    data = sample() if sample_mode else load(root, config)
    page = render(compute(data), time.strftime("%Y-%m-%d %H:%M"), sample_mode)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(page)
    print("dashboard: %s" % path)
    return 0
