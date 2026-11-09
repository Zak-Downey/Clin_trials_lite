"""Git helpers and the era check: which rules the gate a ticket merged under held.

Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import unittest

from fixtures import Repo, git, merged_repo

from gate.git import rule_in_force, run_git

MONOLITH = "class RedAudit:\n    pass\n"


class Era(unittest.TestCase):
    def judged(self, repo):
        """True when ticket 01, merged without a `red:` file, is refused for it: the red rule judged it."""
        code, out = repo.gate("ticket", "feat", "01")
        self.assertIn(code, (0, 1), out)
        return code == 1 and "no `red:` file" in out

    def test_a_ticket_merged_before_the_red_rule_is_not_judged_by_it(self):
        """A ticket merged before the red rule is not judged by it"""
        repo = merged_repo("done", red=False, rules="doc-anchor\nreview-grammar\n")
        self.assertFalse(self.judged(repo))
        self.assertTrue(self.judged(merged_repo("done", red=False, rules="red-audit\n")))

    def test_a_ticket_merged_with_no_rules_file_is_judged_by_no_era_rule(self):
        """A ticket merged with no rules file is judged by no era rule"""
        repo = merged_repo("done", red=False)
        self.assertFalse(self.judged(repo))
        self.assertFalse(rule_in_force(repo.root, "HEAD", "red-audit"))
        self.assertFalse(rule_in_force(repo.root, "HEAD", "mutants"))

    def test_a_ticket_merged_under_a_hardened_monolith_is_still_judged(self):
        """A ticket merged under a hardened monolith is still judged"""
        repo = merged_repo("done", red=False, audit=MONOLITH)
        self.assertTrue(self.judged(repo))
        self.assertTrue(rule_in_force(repo.root, "HEAD", "red-audit"))

    def test_the_era_check_reads_the_rules_file_before_the_gate_s_source(self):
        """The era check reads the rules file before the gate's source"""
        repo = merged_repo("done", red=False, audit=MONOLITH, rules="mutants\n")
        self.assertFalse(self.judged(repo))
        self.assertFalse(rule_in_force(repo.root, "HEAD", "red-audit"))
        self.assertTrue(rule_in_force(repo.root, "HEAD", "mutants"))

    def test_a_rules_file_lists_one_rule_per_line(self):
        """A rules file lists one rule per line"""
        repo = merged_repo("done", rules="red-audit\n  mutants  \n")
        self.assertTrue(rule_in_force(repo.root, "HEAD", "mutants"))
        self.assertFalse(rule_in_force(repo.root, "HEAD", "mut"))


class RunGit(unittest.TestCase):
    def test_run_git_returns_none_on_a_failed_command(self):
        """Run git returns none on a failed command"""
        repo = Repo()
        repo.commit()
        self.assertIsNone(run_git(repo.root, "rev-parse", "--verify", "-q", "refs/heads/nope"))
        self.assertEqual(run_git(repo.root, "rev-parse", "--abbrev-ref", "HEAD"), "feature/x")
