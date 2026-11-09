"""The role files' hand-sample clauses: pinned by text, since no runner mutates prose."""
import re
import unittest
from pathlib import Path

import fixtures  # noqa: F401  (puts the gate package on the path)
from gate.refuse import RULES

AGENTS = Path(__file__).resolve().parents[2] / "agents"


DOCS = Path(__file__).resolve().parents[3] / "docs" / "agents"


def role(name):
    return (AGENTS / name).read_text()


class HandSampleText(unittest.TestCase):
    def test_reviewer_draw_skips_the_implementers_lines(self):
        """The reviewer's draw skips the implementer's hand-sample lines"""
        text = role("ticket-reviewer.md")
        self.assertIn("Skip every line that line names", text)
        self.assertIn("The two samples never share a line", text)
        self.assertIn("say in the findings file that the prompt lacked one", text)

    def test_both_roles_say_how_to_apply_a_mutant(self):
        """Both role files say how to apply a mutant"""
        for name in ("implementer.md", "ticket-reviewer.md"):
            text = role(name)
            self.assertIn("### Applying a mutant", text, name)
            self.assertIn("git checkout -- <file>", text, name)

    def test_neither_role_recommends_sed_i(self):
        """Neither role file recommends sed -i"""
        for name in ("implementer.md", "ticket-reviewer.md"):
            text = role(name)
            self.assertIn("Never `sed -i`", text, name)
            self.assertNotIn("Use `sed -i`", text, name)

    def test_implementer_report_carries_the_hand_sample_line(self):
        """The implementer's report carries the hand-sample line"""
        text = role("implementer.md")
        self.assertIn("## The hand sample", text)
        self.assertIn("`Hand sample: <file:line>, <file:line>, <file:line>; N of 3 caught`", text)

    def test_the_hand_sample_line_reaches_the_reviewer_by_its_prompt(self):
        """The orchestrator's ticket-reviewer prompt carries the hand-sample line"""
        orch = (DOCS / "orchestrator.md").read_text()
        bullet = next(l for l in orch.splitlines() if l.startswith("- **Ticket reviewer**"))
        self.assertIn("`Hand sample:` line", bullet)
        self.assertIn("verbatim", bullet)
        text = role("ticket-reviewer.md")
        self.assertIn("in your prompt", text)
        self.assertNotIn("Hand sample:` line in the report", text)
        self.assertIn("With no `Hand sample:` line in the prompt", text)

    def test_rule_names_the_docs_quote_are_rules_the_gate_holds(self):
        """Every merge rule name orchestrator.md and merger.md quote is a key of RULES"""
        for path in (DOCS / "orchestrator.md", AGENTS / "merger.md"):
            names = set(re.findall(r"`((?:merge-[a-z-]+)|ticket-gate)`", path.read_text()))
            self.assertTrue(names, path.name)
            # a merge the ticket gate stops ends `merge-ticket-gate`; bare `ticket-gate` is the inner line
            self.assertNotIn("ticket-gate", names, f"{path.name} routes on ticket-gate, not merge-ticket-gate")
            for name in names - {"merge-start", "merge-end", "merge-abort"}:  # log verbs, not rules
                self.assertIn(name, RULES, f"{path.name} quotes {name}")


if __name__ == "__main__":
    unittest.main()
