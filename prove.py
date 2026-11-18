"""Proof that the checks can fail: small deliberate breaks, each of which a named test or check must notice.

The list is docs/agents/local/breaks.json: entries with an `id`, the `file` to change, the text to
`find` (exactly once in that file), the text to `replace` it with, a `why` in one sentence, and what
proves it: `test` (one pytest test, by its id) or `check` (the name of a check in CHECKS), never both.
"""

from __future__ import annotations

import ast
import pathlib

import checks

BREAKS = "docs/agents/local/breaks.json"
FIELDS = ("id", "file", "find", "replace", "why")


def list_problems(breaks, root, check_names=None) -> list[str]:
    """`<id>: <fault>` for everything wrong with a list of breaks over the repo at `root`: a field
    missing, both or neither of test and check, a repeated id, a file that does not exist, find text
    absent or there more than once, find and replace the same, a test or check that does not exist.
    The checks are the names in `check_names`, by default the ones checks.py runs."""
    names = [name for name, *_ in checks.CHECKS] if check_names is None else list(check_names)
    problems, seen = [], set()
    for number, item in enumerate(breaks, start=1):
        faults = [f"has no {field}" for field in FIELDS
                  if not isinstance(item.get(field), str) or (field != "replace" and not item[field])]
        if "test" in item and "check" in item:
            faults.append("names both a test and a check; it takes one")
        elif "test" in item:
            faults += named_test_problems(str(item["test"]), root)
        elif "check" in item:
            if item["check"] not in names:
                faults.append(f"{item['check']} is not one of the checks ({', '.join(names)})")
        else:
            faults.append("names neither a test nor a check")
        if item.get("id") and item["id"] in seen:
            faults.append("the id is used more than once")
        seen.add(item.get("id"))
        faults += text_problems(item, root)
        problems += [f"{item.get('id') or f'entry {number}'}: {fault}" for fault in faults]
    return problems


def text_problems(item, root) -> list[str]:
    """The entry's file is missing, its find text is not there exactly once, or the change changes nothing."""
    file, find = item.get("file"), item.get("find")
    if not isinstance(file, str) or not file or not isinstance(find, str) or not find:
        return []
    path = pathlib.Path(root) / file
    if not path.is_file():
        return [f"{file} does not exist"]
    faults = []
    count = path.read_text(encoding="utf-8").count(find)
    if count == 0:
        faults.append(f"the find text is not in {file}")
    elif count > 1:
        faults.append(f"the find text occurs {count} times in {file}; it must occur once")
    if find == item.get("replace"):
        faults.append("find and replace are the same, so nothing breaks")
    return faults


def named_test_problems(test, root) -> list[str]:
    """The pytest id `<file>::<test>` (or `<file>::<Class>::<test>`, with any `[parameters]`) names
    a file that is not there or a test function it does not define."""
    file, _, name = test.partition("::")
    if not name:
        return ["the test is not one test, written <file>::<test>"]
    path = pathlib.Path(root) / file
    if not path.is_file():
        return [f"the test file {file} does not exist"]
    *classes, function = name.split("[")[0].split("::")
    body = ast.parse(path.read_text(encoding="utf-8")).body
    for cls in classes:
        body = next((node.body for node in body if isinstance(node, ast.ClassDef) and node.name == cls), [])
    if not any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function for node in body):
        return [f"{file} has no test {name.split('[')[0]}"]
    return []
