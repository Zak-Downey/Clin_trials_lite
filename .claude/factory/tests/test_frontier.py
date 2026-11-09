"""`gate.py frontier`.

Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import os
import unittest

from fixtures import Repo, git


class Frontier(unittest.TestCase):
    def test_groups(self):
        """Frontier groups tickets into ready, blocked, held, done and flags clashing touches"""
        repo = Repo()
        repo.ticket("01")
        repo.ticket("02", status="ready-for-agent", blocked="01 (was ticket 9 before the split)", touches="client/css/app.css", slug="shell")
        repo.ticket("03", status="ready-for-agent", blocked="01 to 02", slug="list")
        repo.ticket("04", status="ready-for-agent", blocked="None", touches="client/css", slug="map")
        repo.ticket("05", status="ready-for-agent", blocked="01", touches="`*`", slug="deps")
        repo.ticket("06", status="ready-for-human", blocked="01 to 05, 07 (the walks run first)", slug="release")
        repo.ticket("07", status="needs-info", blocked="01", slug="odd")
        repo.ticket("08", status="ready-for-agent", blocked="01", touches="none", slug="quiet")
        repo.ticket("09", status="ready-for-agent", blocked="01", touches="none", slug="quieter")
        code, out = repo.gate("frontier", "feat")
        self.assertEqual(code, 0, out)
        self.assertIn("ready (5): 02; 04; 05; 08; 09", out)
        self.assertNotIn("08 and 09", out)
        self.assertNotIn("08 has no Touches line", out)
        self.assertIn("blocked (1): 03 (on 02)", out)
        self.assertIn("02 and 04 both touch client/css/app.css", out)
        self.assertIn("one of 02 and 05 is marked `*`", out)
        self.assertIn("06 ready-for-human (blocked on 02, 03, 04, 05, 07)", out)
        self.assertIn("one of 05 and 08 is marked `*`", out)
        self.assertIn("07 needs-info", out)
        self.assertIn("done (1): 01", out)

    def test_in_flight_and_held(self):
        """In flight and held"""
        repo = Repo()
        repo.ticket("01")
        repo.ticket("02", status="ready-for-agent", touches="client/css/app.css", slug="fixed-shell-and-start")
        repo.ticket("03", status="ready-for-agent", touches="client/css/app.css, src/routes", slug="list")
        repo.ticket("04", status="ready-for-agent", touches="src/store.js", slug="map")
        repo.ticket("05", status="ready-for-agent", touches="*", slug="deps")
        repo.commit()
        git(repo.root, "worktree", "add", "-q", "-b", "ticket/02-fixed-shell", os.path.join(repo.root, ".claude", "worktrees", "02"))
        code, out = repo.gate("frontier", "feat")
        self.assertIn("in flight (1): 02", out)
        self.assertIn("held (2): 03 (touches client/css/app.css, as does in-flight 02); 05 (one of it and in-flight 02 is marked `*`", out)
        self.assertIn("ready (1): 04", out)

    def test_a_blocking_cycle_is_a_problem(self):
        """A blocking cycle is a problem"""
        repo = Repo()
        repo.ticket("01")
        repo.ticket("02", status="ready-for-agent", blocked="01, 03", slug="walk")
        repo.ticket("03", status="ready-for-agent", blocked="02", slug="explore")
        code, out = repo.gate("frontier", "feat")
        self.assertEqual(code, 1)
        self.assertIn("blocking cycle: 02 -> 03 -> 02", out)

    def test_only_a_ready_ticket_with_a_worktree_is_in_flight(self):
        """Only a ready ticket with a worktree is in flight"""
        repo = Repo()
        repo.ticket("01")
        repo.ticket("02", status="needs-info", slug="odd")
        repo.ticket("03", status="ready-for-agent", slug="exploration")
        repo.commit()
        git(repo.root, "worktree", "add", "-q", "-b", "ticket/02-odd", os.path.join(repo.root, ".claude", "worktrees", "02-odd"))
        git(repo.root, "worktree", "add", "-q", "-b", "ticket/03-exploration--sites", os.path.join(repo.root, ".claude", "worktrees", "03-exploration--sites"))
        code, out = repo.gate("frontier", "feat")
        self.assertIn("in flight (1): 03", out)
        self.assertIn("02 needs-info (has a worktree", out)

    def test_an_unknown_blocker_is_a_problem(self):
        """An unknown blocker is a problem"""
        repo = Repo()
        repo.ticket("01", status="ready-for-agent", blocked="09")
        code, out = repo.gate("frontier", "feat")
        self.assertEqual(code, 1)
        self.assertIn("blocked by 09, which is not a ticket", out)


class FoundationHold(unittest.TestCase):
    """The foundation read holds by `Blocked by`. Lacks: a second foundational ticket, a ticket blocked by 01 through a chain only, a follow-up of 01."""

    def repo(self):
        repo = Repo()
        repo.ticket("01", slug="base")
        repo.write(".scratch/feat/issues/01-base.md", open(os.path.join(repo.root, ".scratch/feat/issues/01-base.md"), encoding="utf-8").read().replace("**Status:** done", "**Status:** done\n\n**Kind:** foundational"))
        repo.ticket("02", status="ready-for-agent", blocked="01", slug="builds-on")
        repo.ticket("03", status="ready-for-agent", blocked="None", slug="alone")
        repo.commit()
        return repo

    def test_a_dependent_is_held_while_the_foundation_read_is_pending(self):
        """A ticket blocked by the foundation is held while its read is pending"""
        repo = self.repo()
        repo.gate("log", "feat", "foundation-read", "01", "--agent", "x")
        code, out = repo.gate("frontier", "feat")
        self.assertIn("held (1): 02 (foundation 01 read pending)", out)
        self.assertIn("ready (1): 03", out)

    def test_the_branch_reviewer_report_releases_the_hold(self):
        """A report of the foundation read releases the held ticket"""
        repo = self.repo()
        repo.gate("log", "feat", "foundation-read", "01", "--agent", "x")
        self.assertIn("held (1): 02", repo.gate("frontier", "feat")[1])
        repo.gate("log", "feat", "report", "01", "branch-reviewer")
        code, out = repo.gate("frontier", "feat")
        self.assertIn("ready (2): 02; 03", out)
        self.assertNotIn("held", out)

    def test_a_foundation_never_read_holds_its_dependents(self):
        """A done foundation with no read line holds its dependents as not dispatched"""
        repo = self.repo()
        code, out = repo.gate("frontier", "feat")
        self.assertIn("02 (foundation 01 read not dispatched)", out)
        self.assertIn("ready (1): 03", out)

    def test_a_wontfix_foundation_holds_nothing(self):
        """A foundational blocker that is wontfix does not hold its dependents"""
        repo = self.repo()
        path = ".scratch/feat/issues/01-base.md"
        repo.write(path, open(os.path.join(repo.root, path), encoding="utf-8").read().replace("**Status:** done", "**Status:** wontfix"))
        repo.commit()
        code, out = repo.gate("frontier", "feat")
        self.assertIn("ready (2): 02; 03", out)
        self.assertNotIn("held", out)

    def test_only_a_branch_reviewer_report_after_the_read_releases_the_hold(self):
        """A report before the read, or by another role, does not release the hold"""
        repo = self.repo()
        repo.gate("log", "feat", "report", "01", "branch-reviewer")
        repo.gate("log", "feat", "foundation-read", "01", "--agent", "x")
        self.assertIn("02 (foundation 01 read pending)", repo.gate("frontier", "feat")[1])
        repo.gate("log", "feat", "report", "01", "implementer")
        self.assertIn("02 (foundation 01 read pending)", repo.gate("frontier", "feat")[1])
