"""The project settings, read as text: what the building agent is refused."""

from __future__ import annotations

import json
from pathlib import Path

SETTINGS = Path(__file__).resolve().parent.parent / ".claude" / "settings.json"


def test_the_settings_refuse_gh_pr_merge_after_the_push_refusals():
    deny = json.loads(SETTINGS.read_text())["permissions"]["deny"]
    assert "Bash(gh pr merge*)" in deny
    last_push = max(i for i, rule in enumerate(deny) if rule.startswith("Bash(git push"))
    assert deny.index("Bash(gh pr merge*)") == last_push + 1
