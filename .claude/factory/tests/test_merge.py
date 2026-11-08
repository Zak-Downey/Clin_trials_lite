"""`gate.py merge`.

Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import atexit
import os
import shutil
import subprocess
import tempfile
import unittest

from fixtures import CLEAN_ENV, Repo, git


class Merge(unittest.TestCase):
    """`gate.py merge`: the merger's mechanical steps, in a throwaway repo with a ticket branch."""

    HUMAN = "- [ ] Reads well — needs-human: judge the wording"
    BRANCH = "ticket/01-thing"

    def make(self, checks=None, boxes=None, branch_file=("src/a.txt", "from the branch\n"), other_tickets=()):
        repo = Repo(checks=checks)
        git(repo.root, "branch", "-m", "feature/feat")
        repo.write(".scratch/feat/spec.md", "# Feat\n\n**Status:** ready-for-agent\n")
        repo.ticket("01", status="ready-for-agent", boxes=boxes or self.HUMAN)
        for n, status in other_tickets:
            repo.ticket(n, status=status, boxes=self.HUMAN, slug="other")
        repo.commit()
        git(repo.root, "checkout", "-q", "-b", self.BRANCH)
        repo.write(*branch_file)
        repo.commit()
        git(repo.root, "checkout", "-q", "feature/feat")
        return repo

    def log_text(self, repo):
        path = os.path.join(repo.root, ".git", "factory", "build-log-feat.md")
        if not os.path.isfile(path):
            return ""
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def merging(self, repo):
        return os.path.exists(os.path.join(repo.root, ".git", "MERGE_HEAD"))

    def rev(self, repo, ref):
        return subprocess.run(["git", "-C", repo.root, "rev-parse", ref], check=True, capture_output=True, text=True, env=CLEAN_ENV).stdout.strip()

    def run_merge(self, repo):
        return repo.gate("merge", "feat", "01", self.BRANCH)

    def test_merge_refuses_a_dirty_tree(self):
        """Merge refuses a dirty tree"""
        repo = self.make()
        repo.write("scratch.txt", "not committed\n")
        before = self.rev(repo, "HEAD")
        code, out = self.run_merge(repo)
        self.assertEqual(code, 1, out)
        self.assertIn("scratch.txt", out)
        self.assertEqual(self.log_text(repo), "")
        self.assertFalse(self.merging(repo))
        self.assertEqual(self.rev(repo, "HEAD"), before)
        self.assertTrue(os.path.exists(os.path.join(repo.root, "scratch.txt")))
        git(repo.root, "checkout", "-q", "-b", "feature/other")
        os.remove(os.path.join(repo.root, "scratch.txt"))
        code, out = self.run_merge(repo)
        self.assertEqual(code, 1, out)
        self.assertIn("feature/other", out)
        self.assertEqual(self.log_text(repo), "")

    def test_merge_stops_on_conflict_with_the_merge_open(self):
        """Merge stops on conflict with the merge open"""
        repo = self.make(branch_file=("src/c.txt", "branch side\n"))
        repo.write("src/c.txt", "integration side\n")
        repo.commit()
        code, out = self.run_merge(repo)
        self.assertEqual(code, 1, out)
        self.assertIn("src/c.txt", out)
        self.assertTrue(self.merging(repo))
        log = self.log_text(repo)
        self.assertIn("merge-start 01 %s" % self.rev(repo, self.BRANCH), log)
        self.assertIn("merge-end 01 conflict", log)

    def last_line(self, out):
        return [l for l in out.strip().split("\n") if l][-1]

    def test_every_exit_of_merge_ends_in_a_refusal_with_a_rule_and_a_need(self):
        """Every exit of merge ends in a refusal with a rule and a need"""
        shape = r"^gate: refused by %s: .+\. Needs: .+$"
        conflict = self.make(branch_file=("src/c.txt", "branch side\n"))
        conflict.write("src/c.txt", "integration side\n")
        conflict.commit()
        code, out = self.run_merge(conflict)
        self.assertEqual(code, 1, out)
        self.assertRegex(self.last_line(out), shape % "merge-conflict")
        self.assertIn("src/c.txt", out)
        red = self.make(checks=[{"name": "unit", "command": "echo 'not ok 1 - x'; exit 1", "red_marker": "not ok"}])
        code, out = self.run_merge(red)
        self.assertRegex(self.last_line(out), shape % "merge-checks")
        self.assertIn("check unit: RED", out)
        bad = self.make()
        git(bad.root, "checkout", "-q", self.BRANCH)
        bad.write("docs/agents/local/factory.json", '{"tracker": 3}')
        bad.commit()
        git(bad.root, "checkout", "-q", "feature/feat")
        code, out = self.run_merge(bad)
        self.assertRegex(self.last_line(out), shape % "merge-config")

    def test_merge_resumes_after_the_conflict_is_resolved(self):
        """Merge resumes after the conflict is resolved"""
        repo = self.make(branch_file=("src/c.txt", "branch side\n"))
        repo.write("src/c.txt", "integration side\n")
        repo.commit()
        self.run_merge(repo)
        code, out = self.run_merge(repo)
        self.assertEqual(code, 1, out)
        self.assertIn("refused", out)
        repo.write("src/c.txt", "both sides\n")
        git(repo.root, "add", "src/c.txt")
        code, out = self.run_merge(repo)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.subject(repo), "Merge ticket 01: Ticket 01")
        log = self.log_text(repo)
        self.assertEqual(log.count("merge-start"), 2)
        self.assertEqual(log.count("merge-end"), 2)
        self.assertLess(log.index("merge-end 01 conflict"), log.rindex("merge-start"))

    def test_merge_aborts_on_a_check_red_alone(self):
        """Merge aborts on a check red alone"""
        repo = self.make(checks=[{"name": "unit", "command": "echo 'not ok 1 - the broken thing'; exit 1", "red_marker": "not ok"}])
        before = self.rev(repo, "HEAD")
        code, out = self.run_merge(repo)
        self.assertEqual(code, 1, out)
        self.assertIn("check unit: RED", out)
        self.assertIn("output:", out)
        self.assertIn("not ok 1 - the broken thing", out)
        self.assertEqual(self.rev(repo, "HEAD"), before)
        self.assert_aborted_clean(repo)
        self.assertIn("merge-end 01 red unit", self.log_text(repo))

    def test_merge_names_the_failing_line_for_a_regex_shaped_marker(self):
        """Merge names the failing line for a regex shaped marker"""
        repo = self.make(checks=[{"name": "unit", "command": "echo 'setup done'; echo 'ERROR: test_save'; exit 1", "red_marker": "^(FAIL|ERROR):"}])
        code, out = self.run_merge(repo)
        self.assertEqual(code, 1, out)
        self.assertIn("failing test: ERROR: test_save", out)

    def test_merge_accepts_a_walk_green_alone(self):
        """Merge accepts a walk green alone"""
        out_dir = tempfile.mkdtemp(prefix="gate-walk-")
        atexit.register(shutil.rmtree, out_dir, True)
        result = os.path.join(out_dir, "walk-output.txt")
        with open(result, "w", encoding="utf-8") as handle:
            handle.write("# tip abc1234\n\n## Result\n\nwalks/06.walk.js \u203a slow one: red under load, green alone (retry: /tmp/x.txt)\n")
        command = "echo 'Walk output written to %s (exit 0); read that file.'" % result
        repo = self.make(checks=[{"name": "walks", "command": command}])
        code, out = self.run_merge(repo)
        self.assertEqual(code, 0, out)
        self.assertIn("FLAKE walks", out)
        self.assertIn("Merge ticket 01:", self.subject(repo))

    def assert_aborted_clean(self, repo):
        """After an abort: no merge open, nothing modified or staged, the ticket still not done."""
        self.assertFalse(self.merging(repo))
        status = subprocess.run(["git", "-C", repo.root, "status", "--porcelain"], capture_output=True, text=True, env=CLEAN_ENV).stdout
        self.assertEqual(status.strip(), "")
        with open(os.path.join(repo.root, ".scratch/feat/issues/01-thing.md"), encoding="utf-8") as handle:
            self.assertIn("**Status:** ready-for-agent", handle.read())

    def subject(self, repo):
        return subprocess.run(["git", "-C", repo.root, "log", "-1", "--format=%s"], check=True, capture_output=True, text=True, env=CLEAN_ENV).stdout.strip()

    def merged_once_with_a_fix_on_the_branch(self):
        repo = self.make()
        code, out = self.run_merge(repo)
        self.assertEqual(code, 0, out)
        git(repo.root, "checkout", "-q", self.BRANCH)
        repo.write("src/fix.txt", "a fix after the review\n")
        repo.commit()
        git(repo.root, "checkout", "-q", "feature/feat")
        return repo

    def test_a_follow_up_merge_has_its_own_subject_and_leaves_the_status(self):
        """A follow-up merge has its own subject and leaves the status"""
        repo = self.merged_once_with_a_fix_on_the_branch()
        first = self.rev(repo, "HEAD")
        code, out = repo.gate("merge", "feat", "01", self.BRANCH, "--follow-up")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.subject(repo), "Merge ticket 01 follow-up: Ticket 01")
        self.assertNotEqual(self.rev(repo, "HEAD"), first)
        self.assertTrue(os.path.exists(os.path.join(repo.root, "src/fix.txt")))
        with open(os.path.join(repo.root, ".scratch/feat/issues/01-thing.md"), encoding="utf-8") as handle:
            self.assertIn("**Status:** done", handle.read())
        files = subprocess.run(["git", "-C", repo.root, "show", "--name-only", "--format=", "HEAD"], capture_output=True, text=True, env=CLEAN_ENV).stdout
        self.assertNotIn(".scratch/feat/issues/01-thing.md", files)
        log = self.log_text(repo)
        self.assertEqual(log.count("merge-start 01"), 2, log)
        self.assertIn("merge-end 01 %s" % self.rev(repo, "HEAD"), log)
        self.assertIn("check unit: green", out)

    def test_a_second_merge_of_a_done_ticket_without_the_flag_is_refused(self):
        """A second merge of a done ticket without the flag is refused"""
        repo = self.merged_once_with_a_fix_on_the_branch()
        before = self.rev(repo, "HEAD")
        log = self.log_text(repo)
        code, out = self.run_merge(repo)
        self.assertEqual(code, 1, out)
        self.assertIn("--follow-up", out)
        self.assertEqual(self.rev(repo, "HEAD"), before)
        self.assertFalse(self.merging(repo))
        self.assertEqual(self.log_text(repo), log)
        fresh = self.make()
        code, out = fresh.gate("merge", "feat", "01", self.BRANCH, "--follow-up")
        self.assertEqual(code, 1, out)
        self.assertIn("--follow-up is for a done ticket", out)

    def test_merge_aborts_when_the_ticket_gate_refuses(self):
        """Merge aborts when the ticket gate refuses"""
        repo = self.make(boxes="- [ ] Nothing proves this")
        before = self.rev(repo, "HEAD")
        code, out = self.run_merge(repo)
        self.assertEqual(code, 1, out)
        self.assertIn("may NOT be marked done", out)
        self.assertRegex(self.last_line(out), r"^gate: refused by merge-ticket-gate: .+\. Needs: .+$")
        self.assertEqual(self.rev(repo, "HEAD"), before)
        self.assert_aborted_clean(repo)
        self.assertIn("merge-end 01 refused", self.log_text(repo))

    def test_merge_commits_a_clean_merge_and_logs_both_ends(self):
        """Merge commits a clean merge and logs both ends"""
        repo = self.make(other_tickets=[("02", "ready-for-agent")])
        tip = self.rev(repo, self.BRANCH)
        code, out = self.run_merge(repo)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.subject(repo), "Merge ticket 01: Ticket 01")
        parents = subprocess.run(["git", "-C", repo.root, "rev-list", "--parents", "-n1", "HEAD"], capture_output=True, text=True, env=CLEAN_ENV).stdout.split()
        self.assertEqual(len(parents), 3)
        with open(os.path.join(repo.root, ".scratch/feat/issues/01-thing.md"), encoding="utf-8") as handle:
            self.assertIn("**Status:** done", handle.read())
        with open(os.path.join(repo.root, ".scratch/feat/spec.md"), encoding="utf-8") as handle:
            self.assertIn("ready-for-agent", handle.read())
        status = subprocess.run(["git", "-C", repo.root, "status", "--porcelain"], capture_output=True, text=True, env=CLEAN_ENV).stdout
        self.assertEqual(status.strip(), "")
        log = self.log_text(repo)
        self.assertIn("merge-start 01 %s" % tip, log)
        self.assertIn("merge-end 01 %s" % self.rev(repo, "HEAD"), log)
        self.assertIn(self.rev(repo, "HEAD")[:7], out)
        self.assertIn("check unit: green", out)

    def test_merge_closes_the_spec_with_its_last_ticket(self):
        """Merge closes the spec with its last ticket"""
        repo = self.make(other_tickets=[("02", "done")])
        code, out = self.run_merge(repo)
        self.assertEqual(code, 0, out)
        with open(os.path.join(repo.root, ".scratch/feat/spec.md"), encoding="utf-8") as handle:
            self.assertIn("**Status:** done", handle.read())
        files = subprocess.run(["git", "-C", repo.root, "show", "--name-only", "--format=", "HEAD"], capture_output=True, text=True, env=CLEAN_ENV).stdout
        self.assertIn(".scratch/feat/spec.md", files)

    def test_merge_leaves_the_spec_while_another_ticket_is_open(self):
        """Merge leaves the spec while another ticket is open"""
        repo = self.make(other_tickets=[("02", "done"), ("03", "ready-for-agent")])
        code, out = self.run_merge(repo)
        self.assertEqual(code, 0, out)
        with open(os.path.join(repo.root, ".scratch/feat/spec.md"), encoding="utf-8") as handle:
            self.assertIn("**Status:** ready-for-agent", handle.read())
        repo = self.make(other_tickets=[("02", "wontfix")])
        code, out = self.run_merge(repo)
        self.assertEqual(code, 0, out)
        with open(os.path.join(repo.root, ".scratch/feat/spec.md"), encoding="utf-8") as handle:
            self.assertIn("**Status:** done", handle.read())

    def test_merge_refuses_another_branchs_open_merge(self):
        """Merge refuses another branch's open merge"""
        repo = self.make()
        git(repo.root, "checkout", "-q", "-b", "ticket/09-other", "feature/feat")
        repo.write("src/other.txt", "other\n")
        repo.commit()
        git(repo.root, "checkout", "-q", "feature/feat")
        git(repo.root, "merge", "--no-ff", "--no-commit", "ticket/09-other")
        code, out = self.run_merge(repo)
        self.assertEqual(code, 1, out)
        self.assertIn("refused", out)
        self.assertTrue(self.merging(repo))
        self.assertEqual(self.log_text(repo), "")

    def test_merge_names_what_ran_when_no_checks_are_configured(self):
        """Merge names what ran when no checks are configured"""
        repo = self.make(checks=[])
        code, out = self.run_merge(repo)
        self.assertEqual(code, 1, out)
        self.assertIn("merge-end 01 red no-checks", self.log_text(repo))
        self.assertNotIn("red lint", self.log_text(repo))

    def test_merge_exports_the_walk_feature(self):
        """Merge exports the walk feature"""
        repo = self.make(checks=[{"name": "unit", "command": "echo walk-feature-is=$WALK_FEATURE"}])
        code, out = self.run_merge(repo)
        self.assertEqual(code, 0, out)
        path = [l for l in out.split("\n") if l.startswith("check unit:")][0].split("output: ")[1].rstrip(")")
        with open(path, encoding="utf-8") as handle:
            self.assertIn("walk-feature-is=feat", handle.read())

    def committed_paths(self, repo):
        return subprocess.run(["git", "-C", repo.root, "show", "--name-only", "--format=", "HEAD"], check=True, capture_output=True, text=True, env=CLEAN_ENV).stdout.split()

    def test_merge_commits_the_walk_results_its_checks_wrote(self):
        """Merge commits the walk results its checks wrote"""
        repo = self.make(checks=[{"name": "unit", "command": "mkdir -p .scratch/feat/walks && echo result > .scratch/feat/walks/w.md"}])
        code, out = self.run_merge(repo)
        self.assertEqual(code, 0, out)
        self.assertIn(".scratch/feat/walks/w.md", self.committed_paths(repo))
        status = subprocess.run(["git", "-C", repo.root, "status", "--porcelain"], check=True, capture_output=True, text=True, env=CLEAN_ENV).stdout
        self.assertEqual(status, "")

    def test_merge_names_any_other_path_its_checks_changed(self):
        """Merge names any other path its checks changed"""
        repo = self.make(checks=[{"name": "unit", "command": "echo x > stray.txt && echo y > src/a.txt"}])
        code, out = self.run_merge(repo)
        self.assertEqual(code, 0, out)
        self.assertIn("stray.txt", out)
        self.assertIn("src/a.txt", out)
        self.assertNotIn("stray.txt", self.committed_paths(repo))

    def test_merge_stages_only_the_walks_folder(self):
        """Merge stages only the walks folder"""
        repo = self.make(checks=[{"name": "unit", "command": "mkdir -p .scratch/feat/walks && echo r > .scratch/feat/walks/w.md && echo x > stray.txt"}])
        code, out = self.run_merge(repo)
        self.assertEqual(code, 0, out)
        self.assertIn(".scratch/feat/walks/w.md", self.committed_paths(repo))
        self.assertNotIn("stray.txt", self.committed_paths(repo))
        self.assertIn("stray.txt", out)


class MergeMatrix(unittest.TestCase):
    """The merge, judged against what the branch's own `gate.py ticket` says (the matrix's staged-merge places)."""

    make = Merge.make
    run_merge = Merge.run_merge
    subject = Merge.subject
    HUMAN = Merge.HUMAN
    BRANCH = Merge.BRANCH

    def configured(self, repo):
        import json
        path = os.path.join(repo.root, "docs/agents/local/factory.json")
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def test_the_merges_ticket_gate_agrees_with_the_branchs(self):
        """The merge's ticket gate agrees with the branch's"""
        for boxes, code_wanted in (("- [x] Done — test: saves the record and reads it back", 0), ("- [x] Done — test: a title nobody wrote", 1)):
            repo = self.make(boxes=boxes)
            git(repo.root, "checkout", "-q", self.BRANCH)
            on_branch, branch_out = repo.gate("ticket", "feat", "01")
            git(repo.root, "checkout", "-q", "feature/feat")
            code, out = self.run_merge(repo)
            self.assertEqual((on_branch, code), (code_wanted, code_wanted), branch_out + out)
            if code_wanted:
                refusal = [l for l in branch_out.split("\n") if "evidence does not resolve" in l]
                self.assertTrue(refusal, branch_out)
                self.assertIn(refusal[0].split(": ", 1)[1], out)

    def test_merge_reads_the_configuration_of_the_merged_tree(self):
        """Merge reads the configuration of the merged tree"""
        import json
        repo = self.make(boxes="- [x] Adds a check — check: added")
        git(repo.root, "checkout", "-q", self.BRANCH)
        config = self.configured(repo)
        config["checks"].append({"name": "added", "command": "true"})
        repo.write("docs/agents/local/factory.json", json.dumps(config))
        repo.commit()
        git(repo.root, "checkout", "-q", "feature/feat")
        code, out = self.run_merge(repo)
        self.assertEqual(code, 0, out)
        self.assertIn("check added: green", out)
        self.assertIn("Merge ticket 01:", self.subject(repo))

    def test_merge_aborts_on_a_configuration_the_merge_makes_invalid(self):
        """Merge aborts on a configuration the merge makes invalid"""
        repo = self.make()
        git(repo.root, "checkout", "-q", self.BRANCH)
        repo.write("docs/agents/local/factory.json", '{"tracker": 3}')
        repo.commit()
        git(repo.root, "checkout", "-q", "feature/feat")
        before = subprocess.run(["git", "-C", repo.root, "rev-parse", "HEAD"], capture_output=True, text=True, env=CLEAN_ENV).stdout
        code, out = self.run_merge(repo)
        self.assertEqual(code, 1, out)
        self.assertIn("invalid in the merged tree", out)
        self.assertFalse(os.path.exists(os.path.join(repo.root, ".git", "MERGE_HEAD")))
        after = subprocess.run(["git", "-C", repo.root, "rev-parse", "HEAD"], capture_output=True, text=True, env=CLEAN_ENV).stdout
        self.assertEqual(before, after)
