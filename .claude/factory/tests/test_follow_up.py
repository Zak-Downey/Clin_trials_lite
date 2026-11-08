"""A follow-up after merge: its log line, its place in the merge lookup and in the judgement of a done ticket;
and what `frontier` says about merges not yet pushed.

Fixtures: a throwaway repo from `merged_repo` (ticket 01 merged once, `done`), with a second branch merged above it as
`Merge ticket 01 follow-up:`. They lack a second ticket and a remote, except where a test adds one.

Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import json
import os
import subprocess
import tempfile
import shutil
import atexit
import unittest

from fixtures import CLEAN_ENV, Repo, follow_up_branch, git, linked_worktree, merged_repo, two_feature_line

import gate.git as gate_git
from gate.config import load_config
from gate.tracker import Feature



def rev(repo, ref):
    return subprocess.run(["git", "-C", repo.root, "rev-parse", ref], check=True, capture_output=True, text=True, env=CLEAN_ENV).stdout.strip()


def with_follow_up(cite_red=True):
    """follow_up_branch merged as `Merge ticket 01 follow-up:`. Returns (repo, first merge)."""
    repo = follow_up_branch(cite_red)
    first = subprocess.run(["git", "-C", repo.root, "log", "--format=%H", "--grep=^Merge ticket 01:"], check=True, capture_output=True, text=True, env=CLEAN_ENV).stdout.split()[0]
    git(repo.root, "merge", "-q", "--no-ff", "-m", "Merge ticket 01 follow-up: more", "ticket/01-fixes")
    return repo, first


def feature_of(repo, name):
    return Feature(repo.root, load_config(repo.root), name)


class Lookup(unittest.TestCase):
    def test_the_merge_lookup_skips_follow_up_merges(self):
        """The merge lookup skips follow-up merges"""
        repo, first = with_follow_up()
        self.assertEqual(gate_git.merge_commit_for(repo.root, "HEAD", "01", feature_of(repo, "feat")), first)
        self.assertEqual(gate_git.newest_merge_commit_for(repo.root, "HEAD", "01", feature_of(repo, "feat")), rev(repo, "HEAD"))
        self.assertEqual(gate_git.newest_merge_commit_for(repo.root, "HEAD~1", "01", feature_of(repo, "feat")), first)
        self.assertIsNone(gate_git.merge_commit_for(repo.root, "HEAD", "02", feature_of(repo, "feat")))

    def test_each_lookup_returns_its_own_feature_s_merge(self):
        """Each lookup returns its own feature's merge"""
        repo, mine, theirs = two_feature_line()
        feat, other = feature_of(repo, "feat"), feature_of(repo, "feat-review")
        self.assertEqual(gate_git.merge_commit_for(repo.root, "HEAD", "01", feat), mine)
        self.assertEqual(gate_git.newest_merge_commit_for(repo.root, "HEAD", "01", feat), mine)
        self.assertEqual(gate_git.merge_commit_for(repo.root, "HEAD", "01", other), theirs)
        self.assertEqual(gate_git.newest_merge_commit_for(repo.root, "HEAD", "01", other), theirs)
        repo.write(".scratch/lone/spec.md", "# Lone\n")
        repo.write(".scratch/lone/issues/01-x.md", "# 01: x\n\n**Status:** ready-for-agent\n")
        lone = feature_of(repo, "lone")
        self.assertIsNone(gate_git.merge_commit_for(repo.root, "HEAD", "01", lone))
        self.assertIsNone(gate_git.newest_merge_commit_for(repo.root, "HEAD", "01", lone))

    def test_a_follow_up_that_adds_no_box_is_still_the_newest_merge(self):
        """A follow-up that adds no box is still the newest merge"""
        repo, first = with_follow_up()
        git(repo.root, "reset", "-q", "--hard", "HEAD~1")
        git(repo.root, "checkout", "-q", "-b", "ticket/01-notes")
        repo.write(".scratch/feat/reviews/01-followup.md", "# Review: ticket 01\n")
        repo.commit()
        git(repo.root, "checkout", "-q", "feature/feat")
        git(repo.root, "merge", "-q", "--no-ff", "-m", "Merge ticket 01 follow-up: notes", "ticket/01-notes")
        feat = feature_of(repo, "feat")
        self.assertEqual(gate_git.newest_merge_commit_for(repo.root, "HEAD", "01", feat), rev(repo, "HEAD"))
        self.assertEqual(gate_git.merge_commit_for(repo.root, "HEAD", "01", feat), first)

    def test_a_first_merge_subject_that_changed_only_the_review_file_is_not_the_first_merge(self):
        """A review-only merge is not the first merge"""
        repo, first = with_follow_up()
        git(repo.root, "checkout", "-q", "-b", "ticket/01-review-only")
        repo.write(".scratch/feat/reviews/01-followup.md", "# Review: ticket 01\n")
        repo.commit()
        git(repo.root, "checkout", "-q", "feature/feat")
        git(repo.root, "merge", "-q", "--no-ff", "-m", "Merge ticket 01: review only", "ticket/01-review-only")
        feat = feature_of(repo, "feat")
        self.assertEqual(gate_git.merge_commit_for(repo.root, "HEAD", "01", feat), first)
        self.assertEqual(gate_git.newest_merge_commit_for(repo.root, "HEAD", "01", feat), rev(repo, "HEAD"))

    def test_a_tracker_spelled_with_a_trailing_slash_still_finds_the_merge(self):
        """A tracker spelled with a trailing slash still finds the merge"""
        for spelling in (".scratch/", "./.scratch"):
            repo = merged_repo("done", extra={"tracker": spelling})
            feat = feature_of(repo, "feat")
            found = gate_git.merge_commit_for(repo.root, "HEAD", "01", feat)
            self.assertEqual(found, gate_git.newest_merge_commit_for(repo.root, "HEAD", "01", feat), spelling)
            self.assertIsNotNone(found, spelling)

    def test_a_ticket_is_not_judged_by_another_feature_s_merge_of_the_same_number(self):
        """A ticket is not judged by another feature's merge"""
        repo, _, _ = two_feature_line()
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 0, out)
        self.assertIn("may be marked done", out)

    def test_a_done_ticket_is_judged_from_the_first_merge_s_base_to_the_newest_merge(self):
        """A done ticket is judged from the first merge's base to the newest merge"""
        repo, _ = with_follow_up()
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 0, out)
        bare, _ = with_follow_up(cite_red=False)
        code, out = bare.gate("ticket", "feat", "01")
        self.assertEqual(code, 1, out)
        self.assertIn("no `red:` file", out)


class OnItsOwnBranch(unittest.TestCase):
    def test_a_follow_up_branch_cut_from_the_integration_tip_passes_the_ticket_gate(self):
        """A follow-up branch cut from the integration tip passes the ticket gate"""
        repo = follow_up_branch()
        wt = linked_worktree(repo, "ticket/01-fixes")
        code, out = repo.gate_at(wt, "ticket", "feat", "01")
        self.assertEqual(code, 0, out)
        self.assertIn("ticket 01 may be marked done: 2 boxes proved", out)

    def test_a_follow_up_branch_passes_the_ticket_gate_with_an_inline_flag_red_marker(self):
        """A follow-up branch passes the ticket gate with an inline flag red marker"""
        repo = follow_up_branch()
        config = json.loads(open(os.path.join(repo.root, "docs/agents/local/factory.json"), encoding="utf-8").read())
        config["checks"] = [{"name": "unit", "command": "true", "proves": ["test"], "red_marker": "(?i)not ok"}]
        repo.write("docs/agents/local/factory.json", json.dumps(config))
        repo.commit()
        git(repo.root, "checkout", "-q", "ticket/01-fixes")
        git(repo.root, "merge", "-q", "feature/feat")
        git(repo.root, "checkout", "-q", "feature/feat")
        wt = linked_worktree(repo, "ticket/01-fixes")
        code, out = repo.gate_at(wt, "ticket", "feat", "01")
        self.assertEqual(code, 0, out)
        self.assertNotIn("Traceback", out)

    def test_merge_of_a_follow_up_with_an_inline_flag_red_marker_completes(self):
        """Merge of a follow-up with an inline flag red marker completes"""
        repo = follow_up_branch()
        config = json.loads(open(os.path.join(repo.root, "docs/agents/local/factory.json"), encoding="utf-8").read())
        config["checks"] = [{"name": "unit", "command": "true", "proves": ["test"], "red_marker": "(?i)not ok"}]
        repo.write("docs/agents/local/factory.json", json.dumps(config))
        repo.commit()
        git(repo.root, "checkout", "-q", "ticket/01-fixes")
        git(repo.root, "merge", "-q", "feature/feat")
        git(repo.root, "checkout", "-q", "feature/feat")
        code, out = repo.gate("merge", "feat", "01", "ticket/01-fixes", "--follow-up")
        self.assertEqual(code, 0, out)
        self.assertNotIn("Traceback", out)
        with open(os.path.join(repo.root, ".git", "factory", "build-log-feat.md"), encoding="utf-8") as handle:
            self.assertIn("merge-end 01", handle.read())

    def test_a_follow_up_branch_without_its_red_run_is_refused_on_the_branch(self):
        """A follow-up branch without its red run is refused on the branch"""
        repo = follow_up_branch(cite_red=False)
        wt = linked_worktree(repo, "ticket/01-fixes")
        code, out = repo.gate_at(wt, "ticket", "feat", "01")
        self.assertEqual(code, 1, out)
        self.assertIn("no `red:` file", out)

    def test_a_follow_up_branch_is_audited_even_where_the_first_merge_predates_the_red_audit(self):
        """A follow-up branch is audited as unmerged work, whatever rules the first merge had"""
        repo = follow_up_branch(cite_red=False, rules="follow-up\n")
        wt = linked_worktree(repo, "ticket/01-fixes")
        code, out = repo.gate_at(wt, "ticket", "feat", "01")
        self.assertEqual(code, 1, out)
        self.assertIn("no `red:` file", out)

    def test_merge_follow_up_passes_its_ticket_gate_step_with_a_new_red_run(self):
        """Merge follow-up passes its ticket gate step with a new red run"""
        repo = follow_up_branch()
        code, out = repo.gate("merge", "feat", "01", "ticket/01-fixes", "--follow-up")
        self.assertEqual(code, 0, out)
        self.assertIn("ticket 01 merged", out)

    def test_ticket_names_the_follow_up_review_it_expects(self):
        """Ticket names the follow-up review file it expects"""
        repo = follow_up_branch()
        code, out = repo.gate("ticket", "feat", "01")
        self.assertIn(".scratch/feat/reviews/01-followup.md", out)
        repo.write(".scratch/feat/reviews/01-followup.md", "# Review\nTip reviewed: abcdef1.\n## Blocking\n## Notes\n")
        code, out = repo.gate("ticket", "feat", "01")
        self.assertIn(".scratch/feat/reviews/01-followup-2.md", out)


class Frontier(unittest.TestCase):
    def remote(self, repo):
        bare = tempfile.mkdtemp(prefix="gate-remote-")
        atexit.register(shutil.rmtree, bare, True)
        git(bare, "init", "-q", "--bare")
        git(repo.root, "remote", "add", "origin", bare)
        git(repo.root, "push", "-q", "-u", "origin", "feature/feat")

    def merge_one_more(self, repo):
        git(repo.root, "checkout", "-q", "-b", "ticket/09-more")
        repo.write("src/more.js", "more\n")
        repo.commit()
        git(repo.root, "checkout", "-q", "feature/feat")
        git(repo.root, "merge", "-q", "--no-ff", "-m", "Merge ticket 09: more", "ticket/09-more")

    def test_frontier_counts_unpushed_merges(self):
        """Frontier counts unpushed merges"""
        repo = Repo()
        repo.ticket("01", status="ready-for-agent")
        repo.commit()
        git(repo.root, "checkout", "-q", "-b", "feature/feat")
        self.remote(repo)
        pushed = rev(repo, "HEAD")
        self.assertNotIn("unpushed", repo.gate("frontier", "feat")[1])
        self.merge_one_more(repo)
        self.merge_one_more_again(repo)
        code, out = repo.gate("frontier", "feat")
        self.assertEqual(code, 0, out)
        self.assertIn("unpushed: 2 merge(s) since %s" % pushed[:7], out)

    def merge_one_more_again(self, repo):
        git(repo.root, "checkout", "-q", "-b", "ticket/10-more")
        repo.write("src/more2.js", "more\n")
        repo.commit()
        git(repo.root, "checkout", "-q", "feature/feat")
        git(repo.root, "merge", "-q", "--no-ff", "-m", "Merge ticket 10: more", "ticket/10-more")

    def test_frontier_says_nothing_about_pushing_without_a_remote(self):
        """Frontier says nothing about pushing without a remote"""
        repo = Repo()
        repo.ticket("01", status="ready-for-agent")
        repo.commit()
        git(repo.root, "checkout", "-q", "-b", "feature/feat")
        self.merge_one_more(repo)
        code, out = repo.gate("frontier", "feat")
        self.assertEqual(code, 0, out)
        self.assertNotIn("unpushed", out)
        self.assertNotIn("push", out)
