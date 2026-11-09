"""`gate.py mutate` and the ticket gate's reading of its report.

Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import json
import os
import sys
import unittest

from fixtures import Repo, git, merged_repo


if __name__ == "__main__":
    unittest.main()


FAKE_STRYKER = """import json, os, sys
# A stand-in for Stryker: records the files it was told to mutate and leaves a report where Stryker leaves its own.
os.makedirs("reports/mutation", exist_ok=True)
open("reports/args.txt", "w").write(" ".join(sys.argv[1:]))
json.dump(json.load(open("fixture-report.json")), open("reports/mutation/mutation.json", "w"))
"""


def mutant(line, status="Survived", mutator="ConditionalExpression", end=None):
    return {"id": str(line), "mutatorName": mutator, "replacement": "true", "status": status,
            "location": {"start": {"line": line, "column": 1}, "end": {"line": end or line, "column": 9}}}


class Mutate(unittest.TestCase):
    """`gate.py mutate` runs Stryker over the ticket's changed files; `ticket` reads the report it leaves.
    Fixture: a fake Stryker (FAKE_STRYKER) and hand-made reports in Stryker's JSON shape. They lack:
    the real tool's output, which one committed run of the real thing shows (explore/mutants.md)."""

    OLD = "".join("line %d\n" % n for n in range(1, 11))

    def branch(self, changed=None, extra=None, files=None):
        """feature/feat holds a ten-line src/a.js; the branch changes `changed` lines of it (default 3 and 4)."""
        repo = Repo(extra={"mutate_paths": ["src/", "client/js/lib/"],
                           "mutate_command": "%s fake_stryker.py {files}" % sys.executable, "mutate_report": "reports/mutation/mutation.json", **(extra or {})})
        repo.write("fake_stryker.py", FAKE_STRYKER)
        repo.write(".gitignore", "reports/\n")
        repo.write("src/a.js", self.OLD)
        repo.ticket("01", status="ready-for-agent")
        repo.commit()
        git(repo.root, "branch", "feature/feat")
        new = self.OLD.split("\n")
        for n in (changed or (3, 4)):
            new[n - 1] = "changed %d" % n
        repo.write("src/a.js", "\n".join(new))
        for path, text in (files or {}).items():
            repo.write(path, text)
        repo.commit()
        return repo

    def fixture(self, repo, mutants, path="src/a.js"):
        repo.write("fixture-report.json", json.dumps({"schemaVersion": "2", "files": {path: {"language": "javascript", "mutants": mutants}}}))
        git(repo.root, "add", "-A")
        git(repo.root, "commit", "-q", "-m", "fixture")

    def run_mutate(self, repo, mutants):
        self.fixture(repo, mutants)
        return repo.gate("mutate", "feat", "01")

    def report_path(self, repo):
        return os.path.join(repo.root, ".scratch/feat/reviews/01-mutants.json")

    def with_report(self, repo, mutants):
        code, out = self.run_mutate(repo, mutants)
        self.assertEqual(code, 0, out)
        git(repo.root, "add", "-A")
        git(repo.root, "commit", "-q", "-m", "report")
        return out

    def test_mutate_scopes_to_changed_files(self):
        """Mutate scopes to changed files"""
        repo = self.branch(files={"src/b.js": "export const b = 1;\n", "test/b.test.js": "x\n", "walks/02.walk.js": "x\n",
                                   "client/js/app.js": "x\n", "src/untouched.md": "x\n"})
        code, out = self.run_mutate(repo, [mutant(3, "Killed")])
        self.assertEqual(code, 0, out)
        with open(os.path.join(repo.root, "reports/args.txt")) as handle:
            args = handle.read()
        self.assertEqual(sorted(args.split(",")), ["src/a.js", "src/b.js"])
        with open(self.report_path(repo)) as handle:
            saved = json.load(handle)
        self.assertIn("src/a.js", saved["files"])
        self.assertEqual(saved["gate"]["tip"], repo.head())

    def test_mutate_refuses_a_tree_changed_since_the_commit(self):
        """Mutate refuses a tree changed since the commit"""
        repo = self.branch()
        repo.write("src/a.js", "dirty\n")
        code, out = repo.gate("mutate", "feat", "01")
        self.assertEqual(code, 2, out)
        self.assertIn("uncommitted", out)

    def test_mutate_lists_exemptions(self):
        """Mutate lists exemptions"""
        repo = self.branch(files={"src/b.js": "// Stryker disable next-line ConditionalExpression: the guard is a no-op here\nif (x) y();\n"})
        code, out = self.run_mutate(repo, [mutant(3, "Killed")])
        self.assertEqual(code, 0, out)
        self.assertIn("exemption: src/b.js:1", out)
        self.assertIn("the guard is a no-op here", out)

    def test_mutate_does_not_list_a_lowercase_stryker_comment(self):
        """Mutate does not list a lowercase stryker comment"""
        repo = self.branch(files={"src/b.js": "// stryker disable next-line all: Stryker ignores this spelling\nx\n"})
        code, out = self.run_mutate(repo, [mutant(3, "Killed")])
        self.assertEqual(code, 0, out)
        self.assertNotIn("exemption:", out)

    def test_mutate_says_when_every_changed_file_is_excepted(self):
        """Mutate says when every changed file is excepted"""
        repo = Repo(extra={"mutate_paths": ["src/"], "mutate_except": ["src/big.js"], "mutate_command": "false", "mutate_report": "r.json"})
        repo.ticket("01", status="ready-for-agent")
        repo.commit()
        git(repo.root, "branch", "feature/feat")
        repo.write("src/big.js", "slow\n")
        repo.commit()
        code, out = repo.gate("mutate", "feat", "01")
        self.assertEqual(code, 0, out)
        self.assertIn("excepted from mutation", out)
        self.assertNotIn("nothing under mutate_paths changed", out)

    def test_mutate_lists_what_it_did_not_mutate(self):
        """Mutate lists what it did not mutate"""
        repo = self.branch(files={".claude/factory/x.py": "a = 1\nb = 2\nc = 3\n", "scripts/run.js": "one\n", "walks/01.walk.js": "changed walk\n",
                                   "client/js/app.js": "app\n", "test/t.test.js": "t\n", ".scratch/feat/note.md": "n\n"})
        code, out = self.run_mutate(repo, [mutant(3, "Killed")])
        self.assertEqual(code, 0, out)
        for line in ("not mutated: .claude/factory/x.py:1-3", "not mutated: scripts/run.js:1", "not mutated: walks/01.walk.js:1", "not mutated: client/js/app.js:1"):
            self.assertIn(line, out)
        self.assertNotIn("not mutated: src/a.js", out)
        self.assertNotIn("test/t.test.js", out)
        self.assertNotIn("note.md", out)

    def test_mutate_with_no_paths_prints_every_changed_line_as_not_mutated(self):
        """Mutate with no paths prints every changed line as not mutated"""
        repo = Repo()
        repo.ticket("01", status="ready-for-agent")
        repo.commit()
        git(repo.root, "branch", "feature/feat")
        repo.write("lib/a.py", "a = 1\nb = 2\n")
        repo.write("tools/b.sh", "echo hi\n")
        repo.commit()
        code, out = repo.gate("mutate", "feat", "01")
        self.assertEqual(code, 0, out)
        self.assertIn("not mutated: lib/a.py:1-2", out)
        self.assertIn("not mutated: tools/b.sh:1", out)
        self.assertNotIn("Stryker", out)
        self.assertNotIn("npm", out)

    def test_ticket_refuses_a_survivor_in_a_changed_line(self):
        """Ticket refuses a survivor in a changed line"""
        repo = self.branch()
        self.with_report(repo, [mutant(4)])
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 1, out)
        self.assertIn("survivor in a changed line: src/a.js:4 ConditionalExpression", out)

    def test_ticket_prints_a_survivor_elsewhere(self):
        """Ticket prints a survivor elsewhere"""
        repo = self.branch()
        self.with_report(repo, [mutant(8), mutant(3, "Killed")])
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 0, out)
        self.assertIn("survivor elsewhere in a changed file: src/a.js:8 ConditionalExpression", out)

    def test_ticket_refuses_a_stale_mutants_report(self):
        """Ticket refuses a stale mutants report"""
        repo = self.branch()
        self.with_report(repo, [mutant(3, "Killed")])
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 0, out)
        repo.write("src/a.js", "changed again\n")
        repo.commit()
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 1, out)
        self.assertIn("mutants report is for", out)
        self.assertIn("run `gate.py mutate feat 01` again", out)

    def test_ticket_refuses_a_missing_mutants_report(self):
        """Ticket refuses a missing mutants report"""
        repo = self.branch()
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 1, out)
        self.assertIn("01-mutants.json", out)

    def test_ticket_needs_no_mutants_report_outside_mutate_paths(self):
        """Ticket needs no mutants report outside mutate paths"""
        repo = Repo(extra={"mutate_paths": ["src/"], "mutate_command": "false", "mutate_report": "r.json"})
        repo.write("src/a.js", "old\n")
        repo.ticket("01", status="ready-for-agent")
        repo.commit()
        git(repo.root, "branch", "feature/feat")
        for path in (".claude/factory/gate.py", "client/js/app.js", "scripts/x.js", "src/a.test.js", "test/t.test.js"):
            repo.write(path, "new\n")
        repo.commit()
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 0, out)
        self.assertNotIn("mutants", out)

    def test_mutate_leaves_out_the_excepted_files(self):
        """Mutate leaves out the excepted files"""
        repo = self.branch(extra={"mutate_except": ["src/big.js"]}, files={"src/big.js": "slow\n"})
        code, out = self.run_mutate(repo, [mutant(3, "Killed")])
        self.assertEqual(code, 0, out)
        with open(os.path.join(repo.root, "reports/args.txt")) as handle:
            self.assertEqual(handle.read(), "src/a.js")
        self.assertIn("not mutated: src/big.js:1", out)

    def multi_line(self, start, end):
        repo = self.branch(changed=(4,))
        self.with_report(repo, [mutant(start, end=end)])
        return repo.gate("ticket", "feat", "01")

    def test_ticket_refuses_a_multi_line_survivor_whose_changed_line_is_not_its_first(self):
        """Ticket refuses a multi-line survivor whose changed line is not its first"""
        code, out = self.multi_line(2, 5)
        self.assertEqual(code, 1, out)
        self.assertIn("survivor in a changed line: src/a.js:2", out)

    def test_ticket_only_prints_a_multi_line_survivor_over_unchanged_lines(self):
        """Ticket only prints a multi-line survivor over unchanged lines"""
        code, out = self.multi_line(6, 9)
        self.assertEqual(code, 0, out)
        self.assertIn("survivor elsewhere in a changed file: src/a.js:6", out)

    def test_ticket_does_not_judge_a_done_ticket_merged_under_an_older_gate(self):
        """Ticket does not judge a done ticket merged under an older gate"""
        for gate_text, expect in (("class RedAudit\n", 0), ("class RedAudit\ndef mutant_problems\n", 1)):
            with self.subTest(gate=gate_text.split()[-1]):
                repo = merged_repo("done", audit=gate_text, extra={"mutate_paths": ["src/"], "mutate_command": "false", "mutate_report": "r.json"})
                code, out = repo.gate("ticket", "feat", "01")
                self.assertEqual(code, expect, out)
                if expect:
                    self.assertIn("no mutants report", out)

    def test_ticket_prints_exemptions_beside_the_report(self):
        """Ticket prints exemptions beside the report"""
        repo = self.branch(files={"src/b.js": "// Stryker disable next-line all: boundary\nx\n"})
        self.with_report(repo, [mutant(3, "Killed")])
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 0, out)
        self.assertIn("exemption: src/b.js:1", out)
