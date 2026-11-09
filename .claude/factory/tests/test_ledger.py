"""`gate.py ledger` and the escapes records.

Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from fixtures import CLEAN_ENV, GATE, Repo


def escape_line(**fields):
    base = {"date": "2026-11-07", "feature": "feat", "id": "E-001", "class": "escape", "found_by": "user",
            "should_have_been": "walk", "fixed_in": "", "rule_id": "", "flake": ""}
    base.update(fields)
    return json.dumps(base)


class Escapes(unittest.TestCase):
    """The structured escape lines beside the ledger's prose rows."""

    LEDGER = ("# Ledger\n\n## Escapes\n\n| ID | Date | Feature | Defect | Found by | Should have been found by | Change made |\n|---|---|---|---|---|---|---|\n"
              "| E-001 | 2026-11-07 | feat | One | user | walk | Fixed |\n"
              "| E-002 | 2026-11-07 | feat | Two | user | unit | Fixed |\n")

    def repo(self, ledger=None, lines=None):
        repo = Repo()
        repo.ticket("01")
        repo.write("docs/agents/local/ledger.md", self.LEDGER if ledger is None else ledger)
        if lines is None:
            lines = [escape_line(), escape_line(id="E-002", should_have_been="unit")]
        repo.write("docs/agents/local/escapes.jsonl", "\n".join(lines) + "\n")
        repo.commit()
        return repo

    def gate_in(self, repo, projects, *args):
        env = dict(CLEAN_ENV, GATE_PROJECTS_DIR=projects)
        result = subprocess.run([sys.executable, GATE] + list(args), cwd=repo.root, capture_output=True, text=True, env=env)
        return result.returncode, result.stdout + result.stderr

    def test_ledger_add_writes_a_line_and_a_row(self):
        """Ledger add writes a line and a row"""
        repo = self.repo()
        code, out = repo.gate("ledger", "add", "--feature", "feat", "--date", "2026-11-08", "--class", "blocking", "--found-by", "branch-review",
                              "--should-have-been", "ticket-review", "--fixed-in", "ticket 04", "--rule-id", "R-3", "--defect", "A thing broke")
        self.assertEqual(code, 0, out)
        with open(os.path.join(repo.root, "docs/agents/local/escapes.jsonl"), encoding="utf-8") as handle:
            line = json.loads(handle.read().strip().split("\n")[-1])
        self.assertEqual(line, {"date": "2026-11-08", "feature": "feat", "id": "E-003", "class": "blocking", "found_by": "branch-review",
                                "should_have_been": "ticket-review", "fixed_in": "ticket 04", "rule_id": "R-3", "flake": ""})
        from gate.records import unclassified, well_typed
        self.assertEqual(unclassified("escapes", line), [])
        self.assertTrue(well_typed("escapes", line))
        row = [l for l in out.split("\n") if l.startswith("| E-003")][0]
        cells = [c.strip() for c in row.strip("|").split("|")]
        self.assertEqual(cells[:7], ["E-003", "2026-11-08", "feat", "A thing broke", "branch-review", "ticket-review", "ticket 04"])

    def test_ledger_add_refuses_a_class_or_gate_off_the_list(self):
        """Ledger add refuses a class or gate off the list"""
        repo = self.repo()
        code, out = repo.gate("ledger", "add", "--feature", "feat", "--class", "huge", "--found-by", "user", "--should-have-been", "walk", "--defect", "x")
        self.assertEqual(code, 2, out)
        self.assertIn("'huge' is not a class", out)
        code, out = repo.gate("ledger", "add", "--feature", "feat", "--class", "escape", "--found-by", "luck", "--should-have-been", "walk", "--defect", "x")
        self.assertEqual(code, 2, out)
        self.assertIn("'luck' is not a gate", out)

    def test_ledger_check_passes_a_joined_ledger(self):
        """Ledger check passes a joined ledger"""
        self.assertEqual(self.repo().gate("ledger", "check")[0], 0)

    def test_ledger_check_refuses_an_unjoined_row(self):
        """Ledger check refuses an unjoined row"""
        repo = self.repo(lines=[escape_line(), escape_line(id="E-009")])
        code, out = repo.gate("ledger", "check")
        self.assertEqual(code, 1)
        self.assertIn("E-002 has a prose row and no line", out)
        self.assertIn("E-009 has a line in docs/agents/local/escapes.jsonl and no prose row", out)

    def test_ledger_check_refuses_a_row_without_an_id(self):
        """Ledger check refuses a row without an id"""
        repo = self.repo(ledger=self.LEDGER + "| | 2026-11-07 | feat | Three | user | walk | Fixed |\n")
        code, out = repo.gate("ledger", "check")
        self.assertEqual(code, 1)
        self.assertIn("has no id", out)

    def test_ready_refuses_an_unjoined_ledger(self):
        """Ready refuses an unjoined ledger"""
        repo = self.repo(lines=[escape_line()])
        code, out = repo.gate("ready", "feat")
        self.assertEqual(code, 1)
        self.assertIn("ledger: E-002 has a prose row and no line", out)

    def test_handover_reads_rows_with_an_id_column(self):
        """Handover reads rows with an id column"""
        ledger = self.LEDGER + "| E-003 | 2026-11-08 | feat | UNRESOLVED app defect: the map jumps | user | walk | Not fixed |\n"
        repo = self.repo(ledger=ledger, lines=[escape_line(), escape_line(id="E-002"), escape_line(id="E-003")])
        out = repo.gate("handover", "feat")[1]
        self.assertIn("- 2026-11-08: UNRESOLVED app defect: the map jumps", out)

    def test_stats_cost_per_finding_counts_only_the_dispatched_reviews(self):
        """Stats cost per finding counts only the dispatched reviews"""
        repo, projects = self.tokens_repo()
        out = self.gate_in(repo, projects, "stats")[1]
        self.assertIn("(2 blocking in 1 file(s)", out)
        self.assertNotIn("5 blocking", out)

    def test_stats_cost_per_finding_with_none_says_so(self):
        """Stats cost per finding with none says so"""
        repo, projects = self.tokens_repo()
        os.remove(os.path.join(repo.root, ".scratch/feat/reviews/01.md"))
        out = self.gate_in(repo, projects, "stats")[1]
        self.assertIn("0 blocking findings in 0 file(s) of .scratch/feat/reviews: no division", out)

    def test_stats_divides_the_branch_reviewer_by_its_findings(self):
        """Stats divides the branch reviewer by its findings"""
        repo, projects = self.tokens_repo()
        repo.write(".scratch/feat/findings/areas.md", "# Areas\nTip reviewed: abcdef1.\n## Blocking\n1. a\n2. b\n3. c\n4. d\n## Notes\n")
        repo.commit()
        repo.gate("log", "feat", "dispatch", "03", "branch-reviewer", "--agent", "br1")
        with open(os.path.join(projects, "-some-project", "session1", "subagents", "agent-br1.jsonl"), "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"message": {"id": "b1", "usage": {"output_tokens": 800}}}) + "\n")
        out = self.gate_in(repo, projects, "stats")[1]
        self.assertIn("feat branch-reviewer: 800 tokens (800 output) in 1 transcript(s); 200 per blocking finding (4 blocking in 1 file(s) of .scratch/feat/findings)", out)

    def test_stats_costs_walks_and_unit_from_recorded_check_durations(self):
        """Stats costs walks and unit from recorded check durations"""
        repo, projects = self.tokens_repo()
        folder = os.path.join(repo.root, ".git", "factory")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "check-durations.jsonl"), "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"check": "walks", "seconds": 30, "green": True}) + "\n" + json.dumps({"check": "walks", "seconds": 10, "green": True}) + "\n")
        out = self.gate_in(repo, projects, "stats")[1]
        self.assertIn("feat walk: 1 escape(s); check walks ran 2 time(s), 40s in all (source: the git directory's factory/check-durations.jsonl", out)
        self.assertIn("40s per escape", out)

    def test_checks_record_their_duration(self):
        """Checks record their duration"""
        repo = Repo()
        repo.gate("checks")
        with open(os.path.join(repo.root, ".git", "factory", "check-durations.jsonl"), encoding="utf-8") as handle:
            record = json.loads(handle.readline())
        self.assertEqual((record["check"], record["green"]), ("unit", True))

    def test_log_refuses_a_second_dispatch_for_one_agent(self):
        """Log refuses a second dispatch for one agent"""
        repo = Repo()
        self.assertEqual(repo.gate("log", "feat", "dispatch", "01", "implementer", "--agent", "abc")[0], 0)
        code, out = repo.gate("log", "feat", "dispatch", "02", "ticket-reviewer", "--agent", "abc")
        self.assertEqual(code, 2)
        self.assertIn("already in the feat log", out)

    def test_a_piped_defect_survives_add_check_and_handover(self):
        """A piped defect survives add, check and handover"""
        repo = self.repo(ledger=self.LEDGER.replace("| E-002", "| E-002"))
        code, out = repo.gate("ledger", "add", "--feature", "feat", "--class", "escape", "--found-by", "user", "--should-have-been", "walk",
                              "--defect", "UNRESOLVED a | b broke", "--change", "Fixed in ticket 05")
        self.assertEqual(code, 0, out)
        row = [l for l in out.split("\n") if l.startswith("| E-003")][0]
        with open(os.path.join(repo.root, "docs/agents/local/ledger.md"), "a", encoding="utf-8") as handle:
            handle.write(row + "\n")
        repo.commit()
        self.assertEqual(repo.gate("ledger", "check")[0], 0)
        self.assertIn("UNRESOLVED a | b broke", repo.gate("handover", "feat")[1])
        self.assertIn("names ticket 05", repo.gate("handover", "feat")[1])


    def stats_repo(self):
        lines = [escape_line(id="E-001", should_have_been="walk", found_by="user"),
                 escape_line(id="E-002", should_have_been="ticket-review", found_by="branch-review", **{"class": "blocking"}),
                 escape_line(id="E-003", should_have_been="walk", found_by="user", **{"class": "nit"}),
                 escape_line(id="E-004", should_have_been="unit", found_by="re-check", **{"class": "sweep"}),
                 escape_line(id="E-005", should_have_been="unit", found_by="ticket-review", **{"class": "sweep"}),
                 escape_line(id="E-006", feature="other", should_have_been="walk", found_by="user")]
        ledger = self.LEDGER + "".join("| E-%03d | 2026-11-07 | feat | x | user | walk | Fixed |\n" % n for n in range(3, 7))
        return self.repo(ledger=ledger, lines=lines)

    def test_stats_counts_escapes_by_gate(self):
        """Stats counts escapes by gate"""
        out = self.stats_repo().gate("stats")[1]
        feat = out.split("escapes in feat by should-have-been gate:")[1].split("\n\n")[0]
        self.assertIn("walk 2", feat)
        self.assertIn("unit 2", feat)
        self.assertIn("ticket-review 1", feat)
        self.assertNotIn("branch-review", feat)
        self.assertIn("escapes in other by should-have-been gate:", out)

    def test_stats_counts_misclasses(self):
        """Stats counts misclasses"""
        out = self.stats_repo().gate("stats")[1]
        self.assertIn("misclassed (nit or sweep, found by a later gate or the user): 2", out)

    def tokens_repo(self):
        repo = self.repo(lines=[escape_line(id="E-001", should_have_been="ticket-review", found_by="user", **{"class": "blocking"}),
                                escape_line(id="E-002", should_have_been="walk")])
        repo.review(blocking=["one", "two"])
        repo.write(".scratch/feat/reviews/00-spec-vs-brief.md", "# Spec against brief\n## Blocking\n1. not a per-ticket review\n2. nor this\n3. nor this\n## Notes\n")
        repo.write(".scratch/feat/reviews/02.md", "# Review: ticket 02\n## Blocking\n1. a ticket nobody dispatched a reviewer to\n## Notes\n")
        repo.commit()
        repo.gate("log", "feat", "dispatch", "01", "ticket-reviewer", "--agent", "abc123")
        repo.gate("log", "feat", "dispatch", "01", "implementer", "--agent", "missing9")
        repo.gate("log", "feat", "note", "prose")
        projects = tempfile.mkdtemp(prefix="gate-projects-")
        atexit.register(shutil.rmtree, projects, True)
        folder = os.path.join(projects, "-some-project", "session1", "subagents")
        os.makedirs(folder)
        usage = {"input_tokens": 100, "cache_creation_input_tokens": 200, "cache_read_input_tokens": 300, "output_tokens": 400}
        with open(os.path.join(folder, "agent-abc123.jsonl"), "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"message": {"id": "m1", "usage": usage}}) + "\n")
            handle.write("not json\n")
            handle.write(json.dumps({"message": {"id": "m1", "usage": usage}}) + "\n")  # the same message again: counted once
        return repo, projects

    def test_stats_reads_tokens_per_role(self):
        """Stats reads tokens per role"""
        repo, projects = self.tokens_repo()
        out = self.gate_in(repo, projects, "stats")[1]
        self.assertIn("dispatches matched: 2", out)
        self.assertIn("feat ticket-reviewer: 1000 tokens (400 output) in 1 transcript(s)", out)
        self.assertIn("feat implementer: not read", out)
        self.assertIn("500 per blocking finding (2 blocking in 1 file(s) of .scratch/feat/reviews)", out)

    def test_stats_divides_tokens_per_gate_by_escapes(self):
        """Stats divides tokens per gate by escapes"""
        repo, projects = self.tokens_repo()
        out = self.gate_in(repo, projects, "stats")[1]
        self.assertIn("ticket-review: 1000 tokens, 1 escape(s), 1000 per escape", out)
        self.assertIn("walk: 1 escape(s), cost not read", out)

    def test_stats_without_transcripts_says_not_read(self):
        """Stats without transcripts says not read"""
        repo, projects = self.tokens_repo()
        out = self.gate_in(repo, os.path.join(projects, "nowhere"), "stats")[1]
        self.assertIn("feat ticket-reviewer: not read", out)
