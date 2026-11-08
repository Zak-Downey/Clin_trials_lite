"""`gate.py release`.

Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import json
import os
import subprocess
import unittest

from fixtures import Repo, git


class Release(unittest.TestCase):
    """`gate.py release` and the design-mark refusal, in a throwaway repo with `main` and `feature/feat`."""

    def made(self, spec_extra="", kinds=None, touches=None, cut_from_tip=True, status="needs-triage", review=False):
        repo = Repo()
        self.user_facing(repo)
        git(repo.root, "branch", "-m", "main")
        repo.write(".scratch/feat/spec.md", "# Feat\n\n**Status:** %s\n%s\n" % (status, spec_extra))
        kinds = kinds if kinds is not None else {"01": "foundational", "02": ""}
        touches = touches or {}
        for n, kind in kinds.items():
            line = "**Kind:** %s\n" % kind if kind else ""
            body = "# %s: T\n\n**Blocked by:** None\n\n**Status:** %s\n%s**Touches:** %s\n\n- [ ] Box — needs-human: look\n\n## Comments\n" % (n, "ready-for-human" if kind == "ready-for-human" else status, line, touches.get(n, "none"))
            repo.write(".scratch/feat/issues/%s-t.md" % n, body)
        repo.commit()
        if not cut_from_tip:
            git(repo.root, "checkout", "-q", "-b", "feature/feat")
            repo.write("later.txt", "x\n")
            repo.commit()
            git(repo.root, "checkout", "-q", "main")
            repo.write("main-moves.txt", "x\n")
            repo.commit()
            git(repo.root, "checkout", "-q", "feature/feat")
        else:
            git(repo.root, "checkout", "-q", "-b", "feature/feat")
        return repo

    def user_facing(self, repo):
        path = os.path.join(repo.root, "docs/agents/local/factory.json")
        with open(path, encoding="utf-8") as handle:
            factory = json.load(handle)
        factory["user_facing"] = ["client/**"]
        factory["user_facing_except"] = ["client/**/*.test.js"]
        repo.write("docs/agents/local/factory.json", json.dumps(factory))

    def text(self, repo, path):
        with open(os.path.join(repo.root, path), encoding="utf-8") as handle:
            return handle.read()

    def test_release_moves_status_once(self):
        """Release moves status once"""
        repo = self.made()
        code, out = repo.gate("release", "feat")
        self.assertEqual(code, 0, out)
        self.assertIn("**Status:** ready-for-agent", self.text(repo, ".scratch/feat/spec.md"))
        for n in ("01", "02"):
            self.assertIn("**Status:** ready-for-agent", self.text(repo, ".scratch/feat/issues/%s-t.md" % n))
        code, out = repo.gate("release", "feat")
        self.assertEqual(code, 1)
        self.assertIn("already released", out)

    def test_release_refuses_a_second_fix_feature(self):
        """Release refuses a second fix feature of one root: the rounds are the root's"""
        repo = self.made()
        for name in ("feat-review-2", "feat-review-review"):
            git(repo.root, "branch", "feature/%s" % name)
            repo.write(".scratch/%s/spec.md" % name, "# Fix again\n\n**Status:** needs-triage\n")
            repo.write(".scratch/%s/issues/01-t.md" % name, "# 1: T\n\n**Blocked by:** None\n\n**Status:** needs-triage\n**Kind:** foundational\n**Touches:** none\n\n- [ ] Box — needs-human: look\n\n## Comments\n")
            repo.commit()
            code, out = repo.gate("release", name)
            self.assertEqual(code, 1, out)
            self.assertIn("refused by release-rounds", out)
            self.assertIn("second fix feature of feat", out)
            self.assertIn("Open list", out)
            self.assertIn("**Status:** needs-triage", self.text(repo, ".scratch/%s/spec.md" % name))
        # the first fix feature is released as before
        git(repo.root, "branch", "feature/feat-review")
        repo.write(".scratch/feat-review/spec.md", "# Fix\n\n**Status:** needs-triage\n")
        repo.write(".scratch/feat-review/issues/01-t.md", "# 1: T\n\n**Blocked by:** None\n\n**Status:** needs-triage\n**Kind:** foundational\n**Touches:** none\n\n- [ ] Box — needs-human: look\n\n## Comments\n")
        repo.commit()
        code, out = repo.gate("release", "feat-review")
        self.assertEqual(code, 0, out)

    def test_release_refuses_a_branch_not_cut_from_the_protected_tip(self):
        """Release refuses a branch not cut from the protected tip"""
        repo = self.made(cut_from_tip=False)
        code, out = repo.gate("release", "feat")
        self.assertEqual(code, 1)
        main = subprocess.run(["git", "-C", repo.root, "rev-parse", "--short", "main"], capture_output=True, text=True).stdout.strip()
        base = subprocess.run(["git", "-C", repo.root, "merge-base", "main", "feature/feat"], capture_output=True, text=True).stdout.strip()[:7]
        self.assertIn(main, out)
        self.assertIn(base, out)
        self.assertIn("needs-triage", self.text(repo, ".scratch/feat/spec.md"))

    def test_release_refuses_a_user_facing_spec_without_walk_tickets(self):
        """Release refuses a user-facing spec without walk tickets"""
        repo = self.made(touches={"02": "client/css/app.css"})
        code, out = repo.gate("release", "feat")
        self.assertEqual(code, 1)
        self.assertIn("acceptance-walk", out)
        self.assertIn("exploration", out)
        walks = self.made(touches={"02": "walks/lib.js"})
        self.assertEqual(walks.gate("release", "feat")[0], 0)
        both = self.made(kinds={"01": "foundational", "02": "", "03": "acceptance-walk", "04": "exploration"}, touches={"02": "client/css/app.css"})
        code, out = both.gate("release", "feat")
        self.assertEqual(code, 0, out)

    def test_release_reads_paths_named_in_the_spec(self):
        """Release reads paths named in the spec"""
        repo = self.made(spec_extra="Changes `client/js/map/view.js`.")
        code, out = repo.gate("release", "feat")
        self.assertEqual(code, 1)
        self.assertIn("acceptance-walk", out)

    def test_release_refuses_a_spec_with_no_foundational_ticket(self):
        """Release refuses a spec with no foundational ticket"""
        repo = self.made(kinds={"01": "", "02": ""})
        code, out = repo.gate("release", "feat")
        self.assertEqual(code, 1)
        self.assertIn("foundational", out)

    def test_release_refuses_an_unread_brief(self):
        """Release refuses an unread brief"""
        repo = self.made(spec_extra="**Brief:** `brief.md`")
        code, out = repo.gate("release", "feat")
        self.assertEqual(code, 1)
        self.assertIn("spec-against-brief", out)
        repo.gate("log", "feat", "spec-against-brief", ".scratch/feat/brief.md")
        code, out = repo.gate("release", "feat")
        self.assertEqual(code, 0, out)

    def test_frontier_ignores_kind(self):
        """Frontier ignores kind"""
        repo = self.made(kinds={"01": "foundational", "02": "acceptance-walk", "03": "ready-for-human"})
        self.assertEqual(repo.gate("release", "feat")[0], 0)
        self.assertIn("**Status:** ready-for-human", self.text(repo, ".scratch/feat/issues/03-t.md"))
        repo.commit()
        code, out = repo.gate("frontier", "feat")
        self.assertEqual(code, 0, out)
        self.assertIn("ready (2): 01; 02", out)
        self.assertIn("03 ready-for-human", out)

    def fix_repo(self, kind, open_item, path="client/js/a.js"):
        repo = Repo()
        self.user_facing(repo)
        git(repo.root, "branch", "-m", "feature/feat-review")
        repo.write(".scratch/feat-review/spec.md", "# Fix\n\n**Status:** ready-for-agent\n\n## Open list\n\n%s\n" % open_item)
        line = "**Kind:** %s\n" % kind if kind else ""
        repo.write(".scratch/feat-review/issues/01-fix.md", "# 1: Fix\n\n**Blocked by:** None\n\n**Status:** ready-for-agent\n%s**Touches:** none\n\n- [ ] Box \u2014 needs-human: look\n\n## Comments\n" % line)
        repo.commit()
        git(repo.root, "checkout", "-q", "-b", "ticket/01-fix")
        repo.write(path, "changed\n")
        repo.commit()
        return repo

    def test_ticket_refuses_a_user_facing_fix_without_a_design_mark(self):
        """Ticket refuses a user-facing fix without a design mark"""
        marked = "1. Ticket 01 changes the dialog wording. Recommended: do."
        repo = self.fix_repo("", marked)
        code, out = repo.gate("ticket", "feat-review", "01")
        self.assertEqual(code, 1)
        self.assertIn("Kind: design", out)
        repo = self.fix_repo("design", "1. Something else. Recommended: do.")
        code, out = repo.gate("ticket", "feat-review", "01")
        self.assertEqual(code, 1)
        self.assertIn("Open list", out)
        repo = self.fix_repo("design", marked)
        code, out = repo.gate("ticket", "feat-review", "01")
        self.assertEqual(code, 0, out)
        repo = self.fix_repo("", "", path="src/a.js")
        self.assertEqual(repo.gate("ticket", "feat-review", "01")[0], 0)


    def test_release_does_not_count_an_excepted_path(self):
        """Release does not count an excepted path"""
        repo = self.made(touches={"02": "client/js/a.test.js"})
        code, out = repo.gate("release", "feat")
        self.assertEqual(code, 0, out)

    def test_release_reads_a_directory_in_touches(self):
        """Release reads a directory in touches"""
        repo = self.made(touches={"02": "client/"})
        code, out = repo.gate("release", "feat")
        self.assertEqual(code, 1)
        self.assertIn("acceptance-walk", out)

    def test_release_names_a_missing_integration_branch(self):
        """Release names a missing integration branch"""
        repo = self.made()
        git(repo.root, "checkout", "-q", "main")
        git(repo.root, "branch", "-D", "feature/feat")
        code, out = repo.gate("release", "feat")
        self.assertEqual(code, 1)
        self.assertIn("feature/feat", out)
        self.assertIn("needs-triage", self.text(repo, ".scratch/feat/spec.md"))

    def test_release_names_a_missing_protected_branch(self):
        """Release names a missing protected branch"""
        repo = self.made()
        git(repo.root, "branch", "-m", "main", "trunk")
        code, out = repo.gate("release", "feat")
        self.assertEqual(code, 1)
        self.assertIn("main", out)

    def test_release_refuses_an_unknown_kind(self):
        """Release refuses an unknown kind"""
        repo = self.made(kinds={"01": "foundational", "02": "foundation"})
        code, out = repo.gate("release", "feat")
        self.assertEqual(code, 1)
        self.assertIn("unknown Kind `foundation`", out)

    def test_design_item_must_be_in_the_open_list_section(self):
        """Design item must be in the open list section"""
        repo = self.fix_repo("design", "1. Something else.\n\n## Comments\n\nticket 01 is discussed here.")
        code, out = repo.gate("ticket", "feat-review", "01")
        self.assertEqual(code, 1)
        self.assertIn("Open list", out)
