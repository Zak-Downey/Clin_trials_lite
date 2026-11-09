"""The gate judges one ticket the same from every place a build runs it in.

Fixture: `fixtures.places()`, one feature with one ticket (box with a new test, a red run and a `doc:` anchor) in five
states. It has no second ticket, no review file and no build log; the checks are `true`.

Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import os
import time
import unittest

from fixtures import Repo, follow_up_branch, gate_in, git, linked_worktree, places


class Places(unittest.TestCase):
    def everywhere(self, check, **kwargs):
        for place in places(**kwargs):
            with self.subTest(place=place.name):
                check(place)

    def test_a_done_ticket_is_judged_the_same_from_every_place(self):
        """A done ticket is judged the same from every place"""
        def check(place):
            code, out = place.gate("ticket", "feat", "01")
            self.assertEqual(code, 0, out)
            self.assertIn("ticket 01 may be marked done: 1 boxes proved", out)
        self.everywhere(check)

    def test_a_missing_red_tip_is_refused_from_every_place(self):
        """A missing red tip is refused from every place"""
        def check(place):
            code, out = place.gate("ticket", "feat", "01")
            self.assertEqual(code, 1, out)
            self.assertIn("which is not on this branch", out)
        self.everywhere(check, missing_red=True)

    def test_a_renamed_heading_after_the_merge_does_not_refuse_the_done_ticket(self):
        """A renamed heading after the merge does not refuse the done ticket"""
        def check(place):
            if not place.merged:
                return
            code, out = place.gate("ticket", "feat", "01")
            self.assertEqual(code, 0, out)
        self.everywhere(check, rename_heading=True)

    def test_the_audit_refuses_another_features_stamp_from_every_place(self):
        """The audit refuses another feature's stamp from every place"""
        def check(place):
            place.stamp("%s\nother-feature\n2026-11-07T10:00:00\n" % ("0" * 40))
            code, out = place.gate("audit", "feat")
            self.assertEqual(code, 1, out)
            self.assertIn("the stamp is for other-feature, not feat", out)
        self.everywhere(check)

    def test_the_audit_in_a_worktree_reports_no_stamp(self):
        """The audit in a worktree reports no stamp"""
        worktree = {p.name: p for p in places()}["worktree"]
        # the checkout it hangs from has another feature's stamp; the linked worktree must not read it
        self.assertTrue(os.path.isfile(os.path.join(worktree.main, ".git", "factory-ready")))
        code, out = worktree.gate("audit", "feat")
        self.assertIn("expected and did not find: stamps: the built-tip stamp", out)
        self.assertNotIn("other-feature", out)

    def test_boxes_counts_the_same_from_every_place(self):
        """Boxes counts the same from every place"""
        def check(place):
            code, out = place.gate("boxes", "feat")
            self.assertEqual(code, 0, out)
            self.assertIn("boxes in feat: 1 proved, 0 for a person to judge, 0 open, 0 ticked without evidence", out)
        self.everywhere(check)

    def test_readys_box_audit_agrees_with_boxes_from_every_place(self):
        """Ready's box audit agrees with boxes from every place"""
        def check(place):
            if not place.merged:
                return  # ready skips a ticket that is not done, whatever its boxes say
            code, out = place.gate("ready", "feat")
            self.assertEqual(code, 1, out)
            problems = [l for l in place.gate("boxes", "feat")[1].split("\n") if "evidence does not resolve" in l]
            self.assertEqual(len(problems), 1, problems)
            self.assertIn(problems[0], out)
        self.everywhere(check, bad_evidence=True)

    def test_ready_counts_the_boxes_the_same_from_every_place(self):
        """Ready counts the boxes the same from every place"""
        def check(place):
            code, out = place.gate("ready", "feat")
            if place.merged:
                self.assertEqual(code, 0, out)
                self.assertIn("1 boxes proved, 0 for a person to judge", out)
            else:
                self.assertEqual(code, 1, out)
                self.assertIn("ticket 01 is ready-for-agent, not done", out)
                self.assertNotIn("evidence", out)
        self.everywhere(check)


    def test_ticket_and_boxes_say_the_same_on_the_branch_as_in_the_staged_merge(self):
        """Ticket and boxes say the same on the follow-up branch as in the staged follow-up merge"""
        repo = follow_up_branch()
        wt = linked_worktree(repo, "ticket/01-fixes")
        git(repo.root, "merge", "-q", "--no-ff", "--no-commit", "ticket/01-fixes")
        for verb in (("ticket", "feat", "01"), ("boxes", "feat")):
            on_branch = repo.gate_at(wt, *verb)
            staged = repo.gate(*verb)
            self.assertEqual(on_branch[0], 0, on_branch)
            self.assertEqual(on_branch, staged)


class ConfiguredTracker(unittest.TestCase):
    """A repo whose factory.json says `"tracker": "work"`: nothing the gate prints, matches or counts names `.scratch`."""

    def test_a_feature_in_work_goes_through_the_printed_steps_to_the_records_stamp(self):
        """A feature in work goes through release, merge, ready, close and the records stamp"""
        repo = Repo(tracker="work")
        repo.write(".gitignore", ".claude/worktrees/\n")
        repo.write("docs/agents/local/ledger.md", "# Ledger\n\n## Builds\n\n| Feature | Dates | Tickets |\n|---|---|---|\n| old | then | 1 |\n\n## Recurring findings\n")
        repo.write("work/feat/spec.md", "# Feat\n\n**Status:** needs-triage\n")
        repo.write("work/feat/issues/01-thing.md", "# 1: T\n\n**Blocked by:** None\n\n**Status:** needs-triage\n**Kind:** foundational\n**Touches:** none\n\n- [ ] Reads well \u2014 needs-human: judge the wording\n\n## Comments\n")
        repo.commit()
        git(repo.root, "branch", "-m", "main")
        git(repo.root, "checkout", "-q", "-b", "feature/feat")
        code, out = repo.gate("release", "feat")
        self.assertEqual(code, 0, out)
        repo.commit()
        git(repo.root, "checkout", "-q", "-b", "ticket/01-thing")
        repo.write("src/a.txt", "from the branch\n")
        repo.write("work/feat/reviews/01.md", "# Review: ticket 01\nTip reviewed: abc1234. Mutation sample: 4 tried, 3 caught.\n## Blocking\n## Notes\n1. n | left: x\n## Not checked\nNothing.\n")
        repo.commit()
        git(repo.root, "checkout", "-q", "feature/feat")
        for words in (("dispatch", "01", "implementer", "--agent", "a1"), ("report", "01", "implementer"), ("dispatch", "01", "ticket-reviewer", "--agent", "a2"), ("report", "01", "ticket-reviewer")):
            repo.gate("log", "feat", *words)
        time.sleep(1.1)  # the log and git both stamp whole seconds; the audit reads a commit in the merge's second as landing in it
        code, out = repo.gate("merge", "feat", "01", "ticket/01-thing")
        time.sleep(1.1)
        self.assertEqual(code, 0, out)
        repo.gate("log", "feat", "review-wave", "1")
        code, out = repo.gate("ready", "feat")
        self.assertEqual(code, 0, out)
        self.assertIn("Write work/feat/report.md", out)
        self.assertNotIn(".scratch", out)
        built = repo.head()
        code, out = repo.gate("close", "feat")
        self.assertEqual(code, 0, out)
        repo.write("work/feat/report.md", "# Report\n\n## Facts\n\nBuilt tip: %s\n" % built)
        repo.commit()
        code, out = repo.gate("ready", "feat", "--records", repo.head())
        self.assertEqual(code, 0, out)

    def test_a_bug_spec_folder_under_the_tracker_clears_a_flake(self):
        """A bug spec folder under the configured tracker clears a flake"""
        from gate.ready import fixed_in_re
        found = fixed_in_re("work")
        self.assertTrue(found.search("fixed in work/bug-x/"))
        self.assertFalse(found.search("fixed in .scratch/bug-x/"))
        self.assertFalse(found.search("fixed in work/bug-x/issues/01.md"))
        self.assertTrue(fixed_in_re(".scratch").search("fixed in .scratch/bug-x/"))

    def test_blocking_findings_are_counted_under_the_tracker(self):
        """Blocking findings are counted under the configured tracker"""
        from gate.ledger import blocking_findings
        repo = Repo(tracker="work")
        repo.commit()
        repo.review(blocking=["one", "two"])
        count, source = blocking_findings(repo.root, "feat", ["01"], "reviews", "work")
        self.assertEqual(count, 2)
        self.assertIn("work/feat/reviews", source)

    def test_stats_counts_blocking_findings_under_the_tracker(self):
        """Stats counts blocking findings under the configured tracker"""
        import atexit, json, shutil, subprocess, sys, tempfile
        from fixtures import CLEAN_ENV, GATE
        repo = Repo(tracker="work")
        repo.write("work/feat/reviews/01.md", "# Review: ticket 01\n## Blocking\n1. one\n2. two\n## Notes\n")
        repo.commit()
        repo.gate("log", "feat", "dispatch", "01", "ticket-reviewer", "--agent", "abc123")
        projects = tempfile.mkdtemp(prefix="gate-projects-")
        atexit.register(shutil.rmtree, projects, True)
        folder = os.path.join(projects, "-p", "s1", "subagents")
        os.makedirs(folder)
        usage = {"input_tokens": 100, "cache_creation_input_tokens": 200, "cache_read_input_tokens": 300, "output_tokens": 400}
        with open(os.path.join(folder, "agent-abc123.jsonl"), "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"message": {"id": "m1", "usage": usage}}) + "\n")
        result = subprocess.run([sys.executable, GATE, "stats"], cwd=repo.root, capture_output=True, text=True,
                                env=dict(CLEAN_ENV, GATE_PROJECTS_DIR=projects))
        self.assertIn("500 per blocking finding (2 blocking in 1 file(s) of work/feat/reviews)", result.stdout + result.stderr)

    def flaking_repo(self, row, escapes=False, count=2):
        import json
        repo = Repo(tracker="work", checks=[{"name": "walks", "command": "true"}])
        title = "stale page: banner"
        out = os.path.join(repo.root, "walk-output.txt")
        with open(out, "w", encoding="utf-8") as handle:
            handle.write("# tip abc1234\n\n## Result\n\ntotal duration: 3s\nwalks/06.walk.js \u203a %s: red under load, green alone (retry: /tmp/r.txt)\n" % title)
        repo.write("docs/agents/local/factory.json", json.dumps({
            "tracker": "work", "evidence": {"test": ["test"], "walk": ["walks"]},
            "checks": [{"name": "walks", "command": "echo 'Walk output written to %s (exit 0); read that file.'" % out}]}))
        old = json.dumps({"date": "2026-11-06", "feature": "feat", "file": "walks/06.walk.js", "title": title, "tip": "841f557"})
        repo.write("docs/agents/local/flakes.jsonl", (old + "\n") * count)
        head = "# Ledger\n\n## Escapes\n\n| Date | Feature | What | Found | Should | Fixed |\n|---|---|---|---|---|---|\n" if escapes else ""
        repo.write("docs/agents/local/ledger.md", head + "| 2026-11-06 | x | `%s` flaked | y | z | %s |\n" % (title, row))
        repo.ticket("01")
        repo.write(".gitignore", "walk-output.txt\n")
        repo.commit()
        return repo

    def test_the_flake_refusal_names_the_tracker(self):
        """The flake refusal names the configured tracker"""
        repo = self.flaking_repo("UNRESOLVED. see .scratch/bug-x/")
        code, out = repo.gate("ready", "feat")
        self.assertEqual(code, 1, out)
        self.assertIn("`work/<slug>/`", out)

    def test_handover_reads_the_tracker_for_a_fixed_row_and_a_flake(self):
        """Handover reads the configured tracker for a fixed row and a flake"""
        repo = self.flaking_repo("UNRESOLVED. Bug spec work/bug-x/", escapes=True, count=3)
        out = repo.gate("handover", "feat")[1]
        self.assertIn("names work/bug-x/: it may be fixed", out)
        self.assertIn("the ledger names work/bug-x/", out)


if __name__ == "__main__":
    unittest.main()
