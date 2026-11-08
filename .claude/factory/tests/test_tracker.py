"""The ticket grammar: headers, acceptance boxes, evidence kinds and what resolves.

Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import ast
import glob
import os
import unittest

from fixtures import HERE, Repo


class Boxes(unittest.TestCase):
    def test_a_clean_ticket_may_be_marked_done(self):
        """A clean ticket may be marked done"""
        repo = Repo()
        repo.ticket("01")
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 0, out)
        self.assertIn("2 boxes proved, 1 for a person to judge", out)

    def test_a_box_may_quote_the_evidence_grammar_in_backticks(self):
        """A box may quote the evidence grammar in backticks"""
        repo = Repo()
        repo.ticket("01", boxes="- [x] A line ends `fixed \u2014 test: <title>` or not \u2014 test: saves the record and reads it back")
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 0, out)

    def test_a_judgement_may_hold_a_semicolon(self):
        """A judgement may hold a semicolon"""
        repo = Repo()
        repo.ticket("01", boxes="- [ ] Recording \u2014 needs-human: run the recorder; then commit what it writes\n- [x] Saves \u2014 needs-human: judge the wording; test: saves the record and reads it back")
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 0, out)
        handover = repo.gate("handover", "feat")[1]
        self.assertIn("## To judge (2)", handover)
        self.assertIn("run the recorder; then commit what it writes", handover)

    def test_an_unticked_box_without_needs_human_stops_it(self):
        """An unticked box without needs human stops it"""
        repo = Repo()
        repo.ticket("01", boxes="- [ ] Opens in the browser")
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 1)
        self.assertIn("open box", out)

    def test_a_tick_without_evidence_stops_it(self):
        """A tick without evidence stops it"""
        repo = Repo()
        repo.ticket("01", boxes="- [x] Saves the record")
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 1)
        self.assertIn("ticked without evidence", out)

    def test_evidence_that_names_nothing_stops_it(self):
        """Evidence that names nothing stops it"""
        repo = Repo()
        repo.ticket("01", boxes="- [x] Saves — test: a test nobody wrote\n- [x] Doc — doc: docs/missing.md\n- [x] Suite — check: nonesuch")
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 1)
        self.assertIn("no test titled", out)
        self.assertIn("no file `docs/missing.md`", out)
        self.assertIn("no check named", out)

    def test_an_aside_in_brackets_is_not_part_of_the_title(self):
        """An aside in brackets is not part of the title"""
        repo = Repo()
        repo.ticket("01", boxes="- [x] Opens \u2014 walk: 01 the form is on top (browser half; the API half is tested); test: saves the record and reads it back (see above)")
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 0, out)

    def test_other_headings_and_bold_forms_are_read(self):
        """Other headings and bold forms are read"""
        repo = Repo()
        repo.ticket("01")
        repo.write(".scratch/feat/issues/02-other.md", "# 02: Other\n\n## What to build\n\nA thing.\n\n**Blocked by**: 01\n\n**Status**: ready-for-agent\n\n## Acceptance criteria\n\n- [ ] Opens in the browser\n\n## Comments\n\n- [ ] not a box\n")
        code, out = repo.gate("ticket", "feat", "02")
        self.assertEqual(code, 1)
        self.assertIn("open box", out)
        self.assertNotIn("no acceptance boxes", out)
        self.assertIn("ready (1): 02", repo.gate("frontier", "feat")[1])

    def test_doc_and_check_evidence_resolve(self):
        """Doc and check evidence resolve"""
        repo = Repo()
        repo.ticket("01", boxes="- [x] Doc — doc: docs/agents/local/repo.md\n- [x] Suite green -- check: unit")
        self.assertEqual(repo.gate("ticket", "feat", "01")[0], 0)

    def test_an_open_blocker_stops_it(self):
        """An open blocker stops it"""
        repo = Repo()
        repo.ticket("01", status="ready-for-agent")
        repo.ticket("02", blocked="01 (Ticket 01)")
        code, out = repo.gate("ticket", "feat", "02")
        self.assertEqual(code, 1)
        self.assertIn("blocked by 01", out)

    def test_legacy_features_are_reported_not_failed(self):
        """Legacy features are reported not failed"""
        repo = Repo(legacy=True)
        repo.ticket("01", boxes="- [x] Saves the record")
        repo.ticket("02", status="ready-for-human", boxes="- [ ] Battery lasts four hours", slug="release")
        code, out = repo.gate("boxes", "feat")
        self.assertEqual(code, 0)
        self.assertIn("legacy: ticket 01 has 1 problem(s)", out)
        self.assertIn("0 open, 1 ticked without evidence", out)
        self.assertIn("not audited (the user's own tickets): 02", out)
        self.assertEqual(repo.gate("ticket", "feat", "01")[0], 1)

    def test_a_docstring_title_is_found_by_the_resolver(self):
        """A docstring title is found by the resolver"""
        repo = Repo(test_dirs=["tests"])
        repo.write("tests/test_a.py", 'class T:\n    def test_saves_quietly(self):\n        """Saves the record quietly"""\n')
        repo.ticket("01", boxes="- [x] Saves \u2014 test: Saves the record quietly")
        self.assertEqual(repo.gate("ticket", "feat", "01")[0], 0)
        repo.ticket("01", boxes="- [x] Saves \u2014 test: saves_the_record_quietly")
        self.assertEqual(repo.gate("ticket", "feat", "01")[0], 1)

    def test_every_test_method_has_a_docstring_title(self):
        """Every test method in both files has a docstring title"""
        for name in sorted(os.path.basename(f) for f in glob.glob(os.path.join(HERE, "test_*.py"))):
            with open(os.path.join(HERE, name), encoding="utf-8") as handle:
                tree = ast.parse(handle.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    doc = ast.get_docstring(node)
                    self.assertTrue(doc and len(doc.split("\n")[0]) >= 10, "%s.%s has no docstring title" % (name, node.name))

    def test_ticket_reads_several_kinds_on_one_line(self):
        """Ticket reads several kinds on one line"""
        repo = Repo()
        repo.ticket("01", boxes="- [x] Many \u2014 test: saves the record and reads it back; walk: 01 the form is on top; doc: docs/agents/local/repo.md; check: unit")
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 0, out)
        repo.ticket("01", boxes="- [x] Many \u2014 test: saves the record and reads it back; walk: a walk nobody wrote; doc: docs/agents/local/repo.md")
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 1)
        self.assertIn("no walk titled `a walk nobody wrote`", out)
        self.assertNotIn("no test titled", out)

    def test_ticket_refuses_an_empty_evidence_title(self):
        """Ticket refuses an empty evidence title"""
        repo = Repo()
        for body in ("doc: ", "check: ", "shot: ", "test: ", "test: ; walk: 01 the form is on top", "walk: 01 the form is on top; test:  "):
            repo.ticket("01", boxes="- [x] Saves \u2014 " + body)
            code, out = repo.gate("ticket", "feat", "01")
            self.assertEqual(code, 1, body)
            self.assertIn("evidence is empty", out, body)

    def test_a_fixture_string_in_a_test_folder_is_not_a_title(self):
        """A fixture string in a test folder is not a title"""
        repo = Repo(test_dirs=["tests"])
        repo.write("tests/test_a.py", 'FIXTURE = "a negative example nobody titled"\n\nclass T:\n    def test_x(self):\n        """The real title of the test"""\n        # a comment that is no title either\n')
        repo.write("tests/b.test.js", "const note = 'a js fixture string';\ntest('the js title', () => {});\n")
        for body, ok in (("The real title", True), ("the js title", True), ("a negative example nobody titled", False),
                         ("a comment that is no title either", False), ("a js fixture string", False)):
            repo.ticket("01", boxes="- [x] Saves \u2014 test: " + body)
            self.assertEqual(repo.gate("ticket", "feat", "01")[0], 0 if ok else 1, body)

    def test_ticket_refuses_a_test_title_found_in_no_test_file(self):
        """Ticket refuses a test title found in no test file"""
        repo = Repo()
        repo.ticket("01", boxes="- [x] Saves \u2014 test: a title no test file holds")
        code, out = repo.gate("ticket", "feat", "01")
        self.assertEqual(code, 1)
        self.assertIn("no test titled `a title no test file holds`", out)
        repo.ticket("01", boxes="- [x] Saves \u2014 test: ab")
        self.assertIn("too short", repo.gate("ticket", "feat", "01")[1])

    def test_a_bare_needs_human_is_an_open_box(self):
        """A bare needs-human is an open box"""
        repo = Repo()
        repo.ticket("01", status="ready-for-agent", boxes="- [ ] Looks right \u2014 needs-human: ")
        code, out = repo.gate("boxes", "feat")
        self.assertEqual(code, 1)
        self.assertIn("0 for a person to judge, 1 open", out)
        self.assertIn("open box", out)

    def test_boxes_counts_per_ticket(self):
        """Boxes counts per ticket"""
        repo = Repo()
        repo.ticket("01")
        repo.ticket("02", status="ready-for-agent", boxes="- [x] A \u2014 test: saves the record and reads it back\n- [ ] B\n- [ ] C \u2014 needs-human: judge it", slug="other")
        code, out = repo.gate("boxes", "feat")
        self.assertEqual(code, 1)
        self.assertIn("boxes in feat: 3 proved, 2 for a person to judge, 1 open, 0 ticked without evidence", out)
        self.assertIn("ticket 01: 2 proved, 1 for a person to judge, 0 open, 0 ticked without evidence", out)
        self.assertIn("ticket 02: 1 proved, 1 for a person to judge, 1 open, 0 ticked without evidence", out)
        one = repo.gate("boxes", "feat", "02")[1]
        self.assertIn("boxes in feat ticket 02: 1 proved", one)
        self.assertNotIn("ticket 01:", one)
