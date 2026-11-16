"""One-off: turn the old escapes ledger into findings and fates for the html-front-end hand-over page.

    python3 .scratch/html-front-end/convert_escapes_once.py      (from the repo root; run once, 2026-11-16)

Reads docs/agents/local/escapes.jsonl (rows E-001 to E-037: features html-front-end and
pr-1-review, the latter being the same build's fix round) and writes, in this folder,
findings/1-walker.jsonl, findings/2-review.jsonl, findings/3-walker-recheck.jsonl and fates.jsonl
in the formats handover.py reads. handover.py itself never reads the ledger.

Nothing is made up:
- `what` is the ledger's `defect` text, whole.
- `finder` is `found_by` (exploration is a walker, branch-review is the review); `pass` is
  "recheck" for the pr-1-review exploration rows (found after the fixes), else "first".
- `area` is the explore or findings file the defect text cites after "explore:" or "findings:".
- `severity` is "not recorded" for every row: the ledger has a class (escape, blocking), not
  what a user would lose. `where` is empty: the ledger has no such field.
- `check` is the walk the defect text names after "walk:", found by name in walks/; else empty.
- A fate is "fixed" where the ledger's `fixed_in` names a ticket. For the seventeen review rows
  the ledger names no fix; RANKED below is copied by hand from the Blocking table of
  .scratch/pr-1-review/ranked.md, which gives each finding (by its source citation) a fix
  ticket. Each such ticket's file says Status: done. A row with neither would get no fate line.
- `commit` is the merge commit of that ticket, found in git by its subject.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
BASE, REVIEW_TIP, TIP = "ec9c681^1", "e77cb9c", "ec9c681^2"  # the build; the tip the review read; the merged tip

# Ledger id -> (row of ranked.md's Blocking table, its sources as written there, pr-1-review ticket).
RANKED = {
    "E-012": (4, "walk B1", "01"),
    "E-013": (3, "srv 1", "08"),
    "E-014": (5, "cli 1; seams 1", "02"),
    "E-015": (13, "cli 2", "03"),
    "E-016": (14, "cli 5", "03"),
    "E-017": (11, "cli 3; cli 4", "04"),
    "E-018": (9, "seams 2", "04"),
    "E-019": (1, "disc S1", "05"),
    "E-020": (10, "disc S3", "05"),
    "E-021": (2, "seams 3", "06"),
    "E-022": (12, "seams 4; srv 4", "06"),
    "E-023": (7, "disc S2; srv 8", "07"),
    "E-024": (8, "srv 7", "07"),
    "E-025": (6, "disc S4", "08"),
    "E-026": (17, "cli 10; walk N3", "09"),
    "E-027": (15, "walk S1", "10"),
    "E-028": (16, "walk S2", "10"),
}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def merge_of(ticket: str, fix_round: bool) -> str:
    """The short sha of 'Merge ticket NN: ...', in the fix round's commits or the first build's."""
    span = f"{REVIEW_TIP}..{TIP}" if fix_round else f"{BASE}..{REVIEW_TIP}"
    found = git("log", "--format=%h", f"--grep=^Merge ticket {ticket}: ", span).split()
    assert len(found) == 1, (ticket, fix_round, found)
    return found[0]


def areas(defect: str) -> str:
    """The files cited after the last 'explore:' / 'findings:' of the defect text, e.g. 'find-trials, dialogs'."""
    cited = re.split(r"(?:explore findings|explore|findings):", defect)
    if len(cited) < 2:
        return "not recorded"
    names = re.findall(r"([a-z]+(?:-[a-z]+)*) [A-Z]?\d", cited[-1].split(";")[0])
    return ", ".join(dict.fromkeys(name for name in names if name != "and")) or "not recorded"


def walk_named(defect: str) -> str:
    """'walks/<file>.py::<test>' for the walk the defect text names after 'walk:', or '' when it names none."""
    named = re.search(r"walk: (test_\w+)", defect)
    if not named:
        return ""
    files = git("grep", "-l", f"def {named.group(1)}(", "--", "walks", "tests").split()
    assert len(files) == 1, (named.group(1), files)
    return f"{files[0]}::{named.group(1)}"


def convert(rows: list[dict]) -> tuple[dict[str, list[dict]], list[dict]]:
    files: dict[str, list[dict]] = {"1-walker": [], "2-review": [], "3-walker-recheck": []}  # file-name order is page order
    fates = []
    for row in rows:
        walker = {"exploration": True, "branch-review": False}[row["found_by"]]
        recheck = row["feature"] == "pr-1-review"
        check = walk_named(row["defect"])
        files["3-walker-recheck" if recheck else "1-walker" if walker else "2-review"].append({
            "id": row["id"], "finder": "walker" if walker else "review", "pass": "recheck" if recheck else "first",
            "area": areas(row["defect"]), "severity": "not recorded", "what": row["defect"], "where": "", "check": check,
        })
        ticket = re.match(r"ticket (\d+)", row["fixed_in"])
        if ticket:
            fates.append({"id": row["id"], "fate": "fixed", "commit": merge_of(ticket.group(1), recheck), "check": check,
                          "why": f"docs/agents/local/escapes.jsonl, fixed_in: {row['fixed_in']}"})
        elif row["id"] in RANKED:
            number, sources, fix = RANKED[row["id"]]
            fates.append({"id": row["id"], "fate": "fixed", "commit": merge_of(fix, True), "check": "",
                          "why": (f"The ledger names no fix. .scratch/pr-1-review/ranked.md, Blocking row {number} ({sources}), "
                                  f"gives it to fix ticket {fix}, whose file says Status: done; the commit is that ticket's merge.")})
    return files, fates


def main() -> None:
    ledger = ROOT / "docs" / "agents" / "local" / "escapes.jsonl"
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = [row for row in rows if row["feature"] in ("html-front-end", "pr-1-review")]
    files, fates = convert(rows)
    (HERE / "findings").mkdir(exist_ok=True)
    for name, found in files.items():
        (HERE / "findings" / f"{name}.jsonl").write_text("".join(json.dumps(f, ensure_ascii=False) + "\n" for f in found), encoding="utf-8")
        print(f"findings/{name}.jsonl: {len(found)}")
    (HERE / "fates.jsonl").write_text("".join(json.dumps(f, ensure_ascii=False) + "\n" for f in fates), encoding="utf-8")
    print(f"fates.jsonl: {len(fates)} of {len(rows)} findings")
    for found in (f for group in files.values() for f in group):
        fate = next((f for f in fates if f["id"] == found["id"]), {})
        print(found["id"], "|", found["area"], "|", fate.get("commit", "NO FATE"), "|", fate.get("check", ""))


if __name__ == "__main__":
    main()
