"""The record files under docs/agents/local, and the one reader of them: every reader of a record file skips, and counts, the same lines.

A line is skipped when it is not JSON, is not an object, or has a field of its file's shape with the wrong type: a text field that is
not text, or a count that is not a finite number. A field the shape does not name is left alone. Each file's shape sits here, beside
the tests that tie it to its writer (`ledger.ESCAPE_FIELDS`, `github.USAGE_FIELDS`, and the lines `close`, `ready` and `stats --write` write).
"""
from __future__ import annotations

import json
import math
import os

from gate.config import read
from gate.pricing import KINDS

# name -> (text fields, count fields, other fields the writer sets and nothing reads as text or number)
SHAPES = {
    "builds": (("date", "feature", "tip"),
               ("tickets", "reviews", "blocking", "mutants_tried", "mutants_survived", "boxes_proved", "boxes_human", "hours", "guard_refusals"),
               ("subagents",)),
    "escapes": (("date", "feature", "id", "class", "found_by", "should_have_been", "fixed_in", "rule_id", "flake"), (), ()),
    "flakes": (("date", "feature", "file", "title", "tip"), (), ()),
    "tokens": (("date", "feature", "ticket", "role", "agent", "model"), KINDS, ()),
    "github": (("date", "product", "sku", "unitType", "repositoryName"), ("quantity", "netAmount"), ()),
}


def is_count(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def well_typed(name: str, record: dict) -> bool:
    """Whether the fields of the named file's shape that the record has are text, or finite numbers for counts."""
    texts, counts, _ = SHAPES.get(name, ((), (), ()))
    return all(record.get(f) is None or isinstance(record[f], str) for f in texts) and \
        all(record.get(f) is None or is_count(record[f]) for f in counts)


def unclassified(name: str, record: dict) -> list:
    """The record's fields that its file's shape does not name."""
    texts, counts, other = SHAPES[name]
    return [k for k in record if k not in texts + counts + other]


def read_records(path: str):
    """(records, skipped): the well-typed JSON objects of the record file at `path`, and how many non-blank lines were not."""
    if not os.path.isfile(path):
        return [], 0
    name = os.path.basename(path).split(".")[0]
    records, skipped = [], 0
    for line in read(path).split("\n"):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError:
            skipped += 1
            continue
        if isinstance(record, dict) and well_typed(name, record):
            records.append(record)
        else:
            skipped += 1
    return records, skipped
