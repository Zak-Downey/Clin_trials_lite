"""Review findings, the red-run audit and the evidence resolver.

Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import json
import os
import unittest

from fixtures import GOOD_BOXES, NEW, RED12, Repo, follow_up_branch, git, merged_repo


TITLE = "saves the record and reads it back"

RED = ".scratch/feat/red/01.txt"


class Reviews(unittest.TestCase):
    """The review file is read by the ticket gate the way a ticket file is."""

    def fixture(self):
        repo = Repo()
        repo.ticket("01")
        repo.commit()
        return repo, repo.head()

    def fixed(self, repo, tip, red_text, line_tail=None):
        """A review of `tip` with one blocking finding marked fixed, then a fix commit."""
        repo.write(RED, red_text)
        repo.review(["The save loses the record | box 1 | src/save.js:3 | " + (line_tail or "fixed \u2014 test: %s \u2014 red: %s" % (TITLE, RED))], tip=tip[:7])
        repo.commit()
        return repo.gate("ticket", "feat", "01")

    def test_ticket_refuses_an_open_blocking_finding(self):
        """Ticket refuses an open blocking finding"""
        repo, tip = self.fixture()
        repo.review(["The save loses the record | box 1 | src/save.js:3 | open"], tip=tip[:7])
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 1, out)
        self.assertIn("blocking finding 1 is still open", out)

    def test_ticket_refuses_a_finding_with_no_status(self):
        """Ticket refuses a finding with no status"""
        repo, tip = self.fixture()
        repo.review(["The save loses the record, and nothing says what became of it"], tip=tip[:7])
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 1, out)
        self.assertIn("blocking finding 1 ends with no status", out)

    def test_ticket_refuses_a_fixed_finding_without_a_check(self):
        """Ticket refuses a fixed finding without a check"""
        repo, tip = self.fixture()
        for tail in ("fixed", "fixed: it was changed", "fixed \u2014 red: %s" % RED, "fixed \u2014 test: a title no test holds \u2014 red: %s" % RED,
                     "fixed \u2014 walk: a walk nobody wrote \u2014 red: %s" % RED, "fixed \u2014 test:  \u2014 red: %s" % RED):
            code, out = self.fixed(repo, tip, "# tip %s\nnot ok 1 - %s\n" % (tip[:7], TITLE), tail)
            self.assertEqual(code, 1, tail)
            self.assertIn("blocking finding 1 is marked fixed", out, tail)

    def test_ticket_refuses_a_fixed_finding_without_a_red_run(self):
        """Ticket refuses a fixed finding without a red run"""
        repo, tip = self.fixture()
        code, out = self.fixed(repo, tip, "", "fixed \u2014 test: %s" % TITLE)
        self.assertEqual(code, 1, out)
        self.assertIn("no `red:` file", out)
        missing = "fixed \u2014 test: %s \u2014 red: .scratch/feat/red/nothing.txt" % TITLE
        self.assertIn("does not exist", self.fixed(repo, tip, "", missing)[1])
        outside = "fixed \u2014 test: %s \u2014 red: docs/agents/local/repo.md" % TITLE
        self.assertIn("not under .scratch/feat/red/", self.fixed(repo, tip, "", outside)[1])
        self.assertIn("is empty", self.fixed(repo, tip, "")[1])
        self.assertIn("first line", self.fixed(repo, tip, "not ok 1 - %s\n" % TITLE)[1])
        passing = "# tip %s\nok 1 - %s\nnot ok 2 - some other test\n" % (tip[:7], TITLE)
        self.assertIn("does not show `%s` failing" % TITLE, self.fixed(repo, tip, passing)[1])
        self.assertIn("does not show", self.fixed(repo, tip, "# tip %s\nnot ok 1 - some other test\n" % tip[:7])[1])

    def test_ticket_accepts_a_fixed_finding_shown_red_at_the_review_tip(self):
        """Ticket accepts a fixed finding shown red at the review tip"""
        repo, tip = self.fixture()
        code, out = self.fixed(repo, tip, "# tip %s\nTAP version 13\nnot ok 1 - %s\n" % (tip[:7], TITLE))
        self.assertEqual(code, 0, out)
        unittest_style = "# tip %s\nFAIL: test_saves (mod.T.test_saves)\n%s\nAssertionError\n" % (tip, TITLE.capitalize())
        self.assertEqual(self.fixed(repo, tip, unittest_style)[0], 0)
        repo.write("src/save.js", "fixed\n")
        repo.commit()
        self.assertEqual(repo.gate("ticket", "feat", "01")[0], 0, "an earlier tip stays valid after the fix commit")

    def test_ticket_refuses_a_red_run_made_after_the_fix(self):
        """Ticket refuses a red run made after the fix"""
        repo, tip = self.fixture()
        repo.write("src/save.js", "fixed\n")
        repo.commit()
        later = repo.head()
        code, out = self.fixed(repo, tip, "# tip %s\nnot ok 1 - %s\n" % (later[:7], TITLE))
        self.assertEqual(code, 1, out)
        self.assertIn("after the review tip", out)
        self.assertIn("not a commit", self.fixed(repo, tip, "# tip deadbeef\nnot ok 1 - %s\n" % TITLE)[1])

    def test_ticket_accepts_a_doc_only_fix_and_refuses_a_missing_file(self):
        """Ticket accepts a doc only fix and refuses a missing file"""
        repo, tip = self.fixture()
        self.assertEqual(self.fixed(repo, tip, "", "fixed \u2014 doc: docs/agents/local/repo.md#stand-ins")[0], 0)
        code, out = self.fixed(repo, tip, "", "fixed \u2014 doc: docs/nothing.md#stand-ins")
        self.assertEqual(code, 1, out)

    def test_ticket_refuses_a_left_blocking_finding(self):
        """Ticket refuses a left blocking finding"""
        repo, tip = self.fixture()
        repo.review(["The save loses the record | box 1 | left: not worth it"], tip=tip[:7])
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 1, out)
        self.assertIn("blocking finding 1 is marked left", out)
        repo.review([], notes=["A name is odd | left: it is the house style"], tip=tip[:7])
        self.assertEqual(repo.gate("ticket", "feat", "01")[0], 0)
        repo.review([], notes=["A name is odd | left:"], tip=tip[:7])
        self.assertIn("note 1 is marked left with no reason", repo.gate("ticket", "feat", "01")[1])

    def unreachable(self, repo, tip, tail, boxes=GOOD_BOXES):
        repo.ticket("01", boxes=boxes)
        repo.review(["The one-radio rule is never reached | box 1 | dialog.js:9 | " + tail], tip=tip[:7])
        repo.commit()
        return repo.gate("ticket", "feat", "01")

    def test_ticket_refuses_unreachable_short_of_one_run_per_engine(self):
        """Ticket refuses unreachable short of one run per engine"""
        repo, tip = self.fixture()
        repo.write("walks/02.walk.js", "for (const browser of ['chromium', 'webkit']) walk(`02 the dialog traps focus (${browser})`, async () => {}, { browser });\n")
        boxes = "- [x] Focus stays \u2014 walk: 02 the dialog traps focus"
        body = "The one-radio rule is never reached: tried to make the first radio unchecked, focus stayed inside\n"
        repo.write(".scratch/feat/red/run-chromium.txt", "# tip %s engine chromium\n%s" % (tip[:7], body))
        repo.write(".scratch/feat/red/run-webkit.txt", "# tip %s engine webkit\n%s" % (tip[:7], body))
        one = "unreachable \u2014 run: .scratch/feat/red/run-chromium.txt"
        code, out = self.unreachable(repo, tip, one, boxes)
        self.assertEqual(code, 1, out)
        self.assertIn("covers 2 engines (chromium, webkit) but names 1 run", out)
        both = one + "; run: .scratch/feat/red/run-webkit.txt"
        self.assertEqual(self.unreachable(repo, tip, both, boxes)[0], 0)
        twice = one + "; run: .scratch/feat/red/run-chromium.txt"
        self.assertIn("names no webkit run", self.unreachable(repo, tip, twice, boxes)[1])

    def test_ticket_accepts_one_unreachable_run_when_the_ticket_has_no_walks(self):
        """Ticket accepts one unreachable run when the ticket has no walks"""
        repo, tip = self.fixture()
        repo.write(".scratch/feat/red/run.txt", "# tip %s\nThe one-radio rule is never reached: tried a group with no checked radio\n" % tip[:7])
        self.assertEqual(self.unreachable(repo, tip, "unreachable \u2014 run: .scratch/feat/red/run.txt")[0], 0)
        self.assertIn("covers 1 engine but names 0 run", self.unreachable(repo, tip, "unreachable")[1])

    def test_ticket_refuses_a_run_that_tried_something_else(self):
        """Ticket refuses a run that tried something else"""
        repo, tip = self.fixture()
        repo.write(".scratch/feat/red/run.txt", "# tip %s\nTried to resize the window and watched the map\n" % tip[:7])
        code, out = self.unreachable(repo, tip, "unreachable \u2014 run: .scratch/feat/red/run.txt")
        self.assertEqual(code, 1, out)
        self.assertIn("does not name the finding's own step (the one-radio rule)", out)
        repo.write(".scratch/feat/red/run.txt", "The one-radio rule is never reached: tried\n")
        self.assertIn("first line", self.unreachable(repo, tip, "unreachable \u2014 run: .scratch/feat/red/run.txt")[1])

    def test_ticket_without_a_review_file_reads_boxes_only(self):
        """Ticket without a review file reads boxes only"""
        repo, _ = self.fixture()
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 0, out)
        self.assertNotIn("review:", out)
        self.assertNotIn("review 01", out)

    def test_ticket_accepts_a_zero_blocking_review_with_notes_left_by_the_reviewer(self):
        """Ticket accepts a zero-blocking review with notes left by the reviewer"""
        repo, tip = self.fixture()
        repo.review([], notes=["A name is odd | left: house style", "A comment is long | left: harmless"], tip=tip[:7])
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 0, out)
        self.assertIn("review: no blocking findings", out)

    def test_a_review_for_another_ticket_is_not_read(self):
        """A review for another ticket is not read"""
        repo, tip = self.fixture()
        repo.ticket("02", slug="other")
        repo.review(["The save loses the record | open"], tip=tip[:7], label="01")
        self.assertEqual(repo.gate("ticket", "feat", "02")[0], 0)
        self.assertEqual(repo.gate("ticket", "feat", "01")[0], 1)


class RedEvidence(unittest.TestCase):
    """A box citing a check new on the branch carries the run in which it failed; a `doc:` names something new."""

    def branch(self, boxes=None, test_text=None):
        """A repo whose integration branch (feature/feat) holds the old tests, and a branch that adds a new one."""
        repo = Repo()
        repo.ticket("01", boxes=boxes or "- [x] Does the new thing — test: %s; red: %s" % (NEW, RED12))
        repo.commit()
        base = repo.head()
        git(repo.root, "branch", "feature/feat")
        repo.write("test/new.test.js", test_text or "test('%s', () => {});\n" % NEW)
        repo.commit()
        return repo, base

    def red(self, repo, tip, body):
        repo.write(RED12, "# tip %s\n%s" % (tip[:7], body))
        repo.commit()
        return repo.gate("ticket", "feat", "01")

    def test_ticket_requires_red_evidence_for_a_new_check(self):
        """Ticket requires red evidence for a new check"""
        repo, base = self.branch(boxes="- [x] Does the new thing — test: %s" % NEW)
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 1, out)
        self.assertIn("no `red:` file", out)
        self.assertIn(NEW, out)

    def test_ticket_accepts_a_red_file_naming_the_failed_check(self):
        """Ticket accepts a red file naming the failed check"""
        repo, base = self.branch()
        code, out = self.red(repo, base, "not ok 1 - %s\n" % NEW)
        self.assertEqual(code, 0, out)
        code, out = self.red(repo, base, "FAIL: test_x (m.T.test_x)\n%s\n" % NEW.capitalize())
        self.assertEqual(code, 0, out)

    def test_ticket_refuses_a_red_file_in_which_the_check_passed(self):
        """Ticket refuses a red file in which the check passed"""
        repo, base = self.branch()
        code, out = self.red(repo, base, "ok 1 - %s\nnot ok 2 - another test\n" % NEW)
        self.assertEqual(code, 1, out)
        self.assertIn("does not show `%s` failing" % NEW, out)

    def test_ticket_refuses_a_red_file_made_after_the_check_passed(self):
        """Ticket refuses a red file made after the check passed"""
        repo, base = self.branch()
        passing = repo.head()
        for tip in (passing, None):
            if tip is None:
                repo.write("src/more.js", "more\n")
                repo.commit()
                tip = repo.head()
            code, out = self.red(repo, tip, "not ok 1 - %s\n" % NEW)
            self.assertEqual(code, 1, out)
            self.assertIn("after the check passed", out)
        self.assertIn("not a commit", self.red(repo, "deadbeef", "not ok 1 - %s\n" % NEW)[1])

    def test_ticket_needs_no_red_evidence_for_an_existing_check(self):
        """Ticket needs no red evidence for an existing check"""
        repo = Repo()
        repo.ticket("01")
        repo.commit()
        git(repo.root, "branch", "feature/feat")
        repo.write("src/x.js", "x\n")
        repo.commit()
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 0, out)

    def test_ticket_refuses_a_red_file_outside_the_red_folder(self):
        """Ticket refuses a red file outside the red folder"""
        repo, base = self.branch(boxes="- [x] Does the new thing \u2014 test: %s; red: docs/elsewhere.txt" % NEW)
        repo.write("docs/elsewhere.txt", "# tip %s\nnot ok 1 - %s\n" % (base[:7], NEW))
        repo.commit()
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 1, out)
        self.assertIn("is not under .scratch/feat/red/", out)

    def test_ticket_requires_red_evidence_for_a_new_walk(self):
        """Ticket requires red evidence for a new walk"""
        title = "02 the new walk shows the form"
        box = "- [x] Shows the form \u2014 walk: %s" % title
        repo = Repo()
        repo.ticket("01", boxes=box)
        repo.commit()
        base = repo.head()
        git(repo.root, "branch", "feature/feat")
        repo.write("walks/02.walk.js", "walk('%s', async () => {});\n" % title)
        repo.commit()
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 1, out)
        self.assertIn("no `red:` file", out)
        repo.ticket("01", boxes=box + "; red: " + RED12)
        repo.write(RED12, "# tip %s\nnot ok 1 - %s\n" % (base[:7], title))
        repo.commit()
        self.assertEqual(repo.gate("ticket", "feat", "01")[0], 0)

    def test_ticket_passes_in_a_staged_merge(self):
        """Ticket passes in a staged merge"""
        repo = Repo()
        repo.ticket("01", boxes="- [x] Does the new thing \u2014 test: %s; red: %s" % (NEW, RED12))
        repo.commit()
        base = repo.head()
        git(repo.root, "branch", "feature/feat")
        git(repo.root, "checkout", "-q", "-b", "ticket/01")
        repo.write("src/work.js", "work\n")
        repo.commit()
        before = repo.head()  # a commit only the ticket branch has: the red run was made here
        repo.write("test/new.test.js", "test('%s', () => {});\n" % NEW)
        repo.commit()
        repo.write(RED12, "# tip %s\nnot ok 1 - %s\n" % (before[:7], NEW))
        repo.commit()
        self.assertEqual(repo.gate("ticket", "feat", "01")[0], 0)
        git(repo.root, "checkout", "-q", "feature/feat")
        repo.write("other.txt", "another ticket merged meanwhile\n")
        repo.commit()
        git(repo.root, "merge", "-q", "--no-ff", "--no-commit", "ticket/01")
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 0, out)

    def test_ticket_judges_a_done_ticket_against_its_own_merge(self):
        """Ticket judges a done ticket against its own merge"""
        repo = merged_repo("done")
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 0, out)

    def test_ticket_takes_the_merge_whose_subject_has_the_colon(self):
        """Ticket takes the merge whose subject has the colon"""
        repo = merged_repo("done", audit="class RedAudit:\n    pass\n", noise=("later-merge",))
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 0, out)

    def test_ticket_takes_the_merge_on_the_integration_line(self):
        """Ticket takes the merge on the integration line"""
        repo = merged_repo("done", audit="class RedAudit:\n    pass\n", noise=("side-commit",))
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 0, out)

    def test_ticket_bounds_the_merge_lookup_to_the_feature(self):
        """Ticket bounds the merge lookup to the feature"""
        repo = Repo()
        repo.ticket("01", status="ready-for-agent", boxes="- [x] Documents it \u2014 test: saves the record and reads it back; doc: docs/a.md#gate-py-red")
        repo.write("docs/a.md", "# A\n")
        repo.write(".claude/factory/gate.py", "class RedAudit:\n    pass\n")
        repo.commit()
        git(repo.root, "branch", "-m", "main")
        git(repo.root, "checkout", "-q", "-b", "old")
        repo.write("docs/a.md", "# A\n\n## gate.py red\n")
        repo.commit()
        git(repo.root, "checkout", "-q", "main")
        git(repo.root, "merge", "-q", "--no-ff", "-m", "Merge ticket 01: an earlier feature's ticket", "old")
        git(repo.root, "checkout", "-q", "-b", "feature/feat")
        repo.write("src/x.js", "x\n")
        repo.commit()
        repo.ticket("01", status="done", boxes="- [x] Documents it \u2014 test: saves the record and reads it back; doc: docs/a.md#gate-py-red")
        repo.commit()
        # this feature's ticket 01 has no merge of its own: the older feature's merge on main must not be its base
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 1, out)
        self.assertIn("already existed at the integration tip", out)

    def test_ticket_does_not_judge_a_done_ticket_by_a_rule_newer_than_its_merge(self):
        """Ticket does not judge a done ticket by a rule newer than its merge"""
        repo = merged_repo("done", red=False)
        self.assertEqual(repo.gate("ticket", "feat", "01")[0], 0)
        repo = merged_repo("done", audit="class RedAudit:\n    pass\n", red=False)
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 1, out)
        self.assertIn("no `red:` file", out)

    def test_ticket_judges_an_unmerged_ticket_against_the_integration_tip(self):
        """Ticket judges an unmerged ticket against the integration tip"""
        repo = merged_repo("ready-for-agent")
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 1, out)
        self.assertIn("already existed at the integration tip", out)

    def doc_branch(self, pointer, base_files, branch_files):
        repo = Repo()
        for path, text in base_files.items():
            repo.write(path, text)
        repo.ticket("01", boxes="- [x] Documents it — test: saves the record and reads it back; doc: %s" % pointer)
        repo.commit()
        git(repo.root, "branch", "feature/feat")
        for path, text in branch_files.items():
            repo.write(path, text)
        repo.commit()
        return repo.gate("ticket", "feat", "01")

    def test_ticket_refuses_a_doc_path_that_already_existed(self):
        """Ticket refuses a doc path that already existed"""
        code, out = self.doc_branch("docs/a.md", {"docs/a.md": "# A\n"}, {"docs/a.md": "# A\n\nmore\n"})
        self.assertEqual(code, 1, out)
        self.assertIn("doc must be able to fail", out)
        code, out = self.doc_branch("docs/b.md", {}, {"docs/b.md": "# B\n"})
        self.assertEqual(code, 0, out)

    def test_ticket_accepts_a_doc_anchor_new_on_the_branch(self):
        """Ticket accepts a doc anchor new on the branch"""
        code, out = self.doc_branch("docs/a.md#gate-py-red", {"docs/a.md": "# A\n"}, {"docs/a.md": "# A\n\n## gate.py red\n"})
        self.assertEqual(code, 0, out)
        code, out = self.doc_branch("docs/a.md#red", {"docs/a.md": "# A\n"}, {"docs/a.md": "# A\n\nRed: the run\n"})
        self.assertEqual(code, 0, out)

    def test_ticket_refuses_a_doc_anchor_that_already_existed(self):
        """Ticket refuses a doc anchor that already existed"""
        code, out = self.doc_branch("docs/a.md#older", {"docs/a.md": "# A\n\n## Older\n"}, {"docs/a.md": "# A\n\n## Older\n\nmore\n"})
        self.assertEqual(code, 1, out)
        self.assertIn("doc must be able to fail", out)
        code, out = self.doc_branch("docs/a.md#absent", {"docs/a.md": "# A\n"}, {"docs/a.md": "# A\n\nmore\n"})
        self.assertEqual(code, 1, out)

class RedMarkerReading(unittest.TestCase):
    """One compiled regex per marker. Fixture: a one-line red file; real runners print more around it."""

    MARKERS = ["FAIL:|ERROR:", "(FAIL|ERROR):", "^FAIL:", "FAIL\\b"]

    def test_a_regex_shaped_red_marker_is_read_the_same_by_config_and_the_red_audit(self):
        """A regex-shaped red marker is read the same by config and the red audit"""
        from gate.evidence import red_markers, shows_failing
        for marker in self.MARKERS:
            with self.subTest(marker=marker):
                config = {"checks": [{"name": "unit", "command": "true", "proves": ["test"], "red_marker": marker}]}
                repo = Repo()
                repo.write("docs/agents/local/factory.json", json.dumps(config))
                code, out = repo.gate("config")
                self.assertEqual(code, 0, out)
                found = red_markers(config, "test")
                self.assertTrue(shows_failing("FAIL: test_save\n", "test_save", found, "test"))
                self.assertFalse(shows_failing("ok test_save\n", "test_save", found, "test"))
                self.assertFalse(shows_failing("FAIL: other_test\n", "test_save", found, "test"))

    def test_a_title_on_the_line_after_a_marker_line_is_shown_failing_only_when_the_line_starts_with_it(self):
        """A title on the line after a marker line is shown failing only when that line starts with the marker"""
        from gate.evidence import red_markers, shows_failing
        for marker in self.MARKERS:
            with self.subTest(marker=marker):
                config = {"checks": [{"name": "unit", "command": "true", "proves": ["test"], "red_marker": marker}]}
                found = red_markers(config, "test")
                self.assertTrue(shows_failing("FAIL: test_a (m.C)\nsaves the record\n", "saves the record", found, "test"))
                self.assertFalse(shows_failing("see FAIL: x\nsaves the record\n", "saves the record", found, "test"))

    def test_an_inline_flag_red_marker_is_shown_failing_alone_and_beside_another_check_of_the_same_kind(self):
        """An inline flag red marker is read by the red audit as config reads it"""
        from gate.evidence import red_markers, shows_failing
        unit = {"name": "unit", "command": "true", "proves": ["test"], "red_marker": "(?i)not ok"}
        other = {"name": "other", "command": "true", "proves": ["test"], "red_marker": "FAIL:"}
        for checks in ([unit], [unit, other], [other, unit]):
            with self.subTest(checks=[c["name"] for c in checks]):
                config = {"checks": checks}
                repo = Repo()
                repo.write("docs/agents/local/factory.json", json.dumps(config))
                code, out = repo.gate("config")
                self.assertEqual(code, 0, out)
                found = red_markers(config, "test")
                self.assertTrue(shows_failing("not ok 1 - saves the form\n", "saves the form", found, "test"))
                self.assertFalse(shows_failing("ok 1 - saves the form\n", "saves the form", found, "test"))

    def test_a_red_file_no_marker_matches_is_refused_naming_every_marker_tried(self):
        """A red file no marker matches is refused naming every marker tried"""
        repo = follow_up_branch()
        checks = [{"name": "unit", "command": "true", "proves": ["test"], "red_marker": "(?i)boom"},
                  {"name": "other", "command": "true", "proves": ["test"], "red_marker": "SPLAT:"}]
        config = json.loads(open(os.path.join(repo.root, "docs/agents/local/factory.json"), encoding="utf-8").read())
        config["checks"] = checks
        repo.write("docs/agents/local/factory.json", json.dumps(config))
        repo.commit()
        git(repo.root, "checkout", "-q", "ticket/01-fixes")
        git(repo.root, "merge", "-q", "feature/feat")
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 1, out)
        self.assertIn("(?i)boom", out)
        self.assertIn("SPLAT:", out)

    def test_a_title_on_the_line_after_a_marker_line_is_shown_failing_when_any_one_of_two_checks_markers_starts_it(self):
        """A title after a marker line is shown failing when any one of two checks markers starts that line"""
        from gate.evidence import red_markers, shows_failing
        config = {"checks": [{"name": "unit", "command": "true", "proves": ["test"], "red_marker": "(?i)not ok"},
                             {"name": "other", "command": "true", "proves": ["test"], "red_marker": "FAIL:"}]}
        found = red_markers(config, "test")
        self.assertTrue(shows_failing("FAIL: test_a (m.C)\nsaves the record\n", "saves the record", found, "test"))

    def test_config_refuses_a_red_marker_with_an_empty_alternative(self):
        """Config refuses a red marker with an empty alternative"""
        for marker in ["FAIL:|", "FAIL:||ERROR:"]:
            with self.subTest(marker=marker):
                repo = Repo()
                repo.write("docs/agents/local/factory.json", json.dumps({"checks": [{"name": "unit", "command": "true", "proves": ["test"], "red_marker": marker}]}))
                code, out = repo.gate("config")
                self.assertEqual(code, 1, out)
                self.assertIn("checks[0].red_marker", out)

