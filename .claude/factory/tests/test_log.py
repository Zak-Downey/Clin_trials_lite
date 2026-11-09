"""The build log, `open`, `stats` and the checklists printed when a phase ends.

Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import os
import unittest

from fixtures import Repo


class Phases(unittest.TestCase):
    """The checklists the gate prints when a phase ends, the log grammar, `open` and `stats`."""

    def done_repo(self):
        repo = Repo()
        repo.ticket("01")
        repo.commit()
        return repo

    def log_text(self, repo):
        path = os.path.join(repo.root, ".git", "factory", "build-log-feat.md")
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def test_frontier_prints_the_next_phase_when_empty(self):
        """Frontier prints the next phase when empty"""
        repo = self.done_repo()
        code, out = repo.gate("frontier", "feat")
        self.assertEqual(code, 0, out)
        self.assertIn("frontier is empty", out)
        self.assertIn("When the frontier is empty", out)
        self.assertIn("gate.py boxes feat", out)
        self.assertTrue(out.rstrip().split("\n")[-1].strip().startswith("3."), out)
        repo.ticket("02", status="ready-for-agent", blocked="01", slug="more")
        code, out = repo.gate("frontier", "feat")
        self.assertNotIn("When the frontier is empty", out)
        repo.ticket("02", status="needs-info", blocked="01", slug="more")
        self.assertNotIn("When the frontier is empty", repo.gate("frontier", "feat")[1])

    def test_boxes_prints_the_review_wave_when_clean(self):
        """Boxes prints the review wave when clean"""
        repo = self.done_repo()
        code, out = repo.gate("boxes", "feat")
        self.assertEqual(code, 0, out)
        self.assertIn("Review the whole branch", out)
        self.assertIn(".scratch/feat-review/findings/", out)
        self.assertIn("standards-reviewer", out)
        self.assertIn("review-merger", out)
        self.assertNotIn("Review the whole branch", repo.gate("boxes", "feat", "01")[1])
        repo.ticket("01", boxes="- [ ] Opens in the browser")
        code, out = repo.gate("boxes", "feat")
        self.assertEqual(code, 1)
        self.assertNotIn("Review the whole branch", out)

    def test_ready_prints_close_out_on_stamp(self):
        """Ready prints close out on stamp"""
        repo = self.done_repo()
        code, out = repo.gate("ready", "feat")
        self.assertEqual(code, 0, out)
        self.assertIn("Close-out", out)
        self.assertIn("gate.py close feat", out)
        self.assertIn("--records", out)
        self.assertIn(repo.head()[:7], out)
        repo.ticket("01", status="ready-for-agent")
        repo.commit()
        code, out = repo.gate("ready", "feat")
        self.assertEqual(code, 1)
        self.assertNotIn("Close-out", out)

    def test_log_writes_each_verb_in_the_grammar(self):
        """Log writes each verb in the grammar"""
        repo = self.done_repo()
        lines = [
            ("dispatch", "01", "implementer", "--agent", "a1"),
            ("report", "01", "implementer"),
            ("resume", "01", "implementer"),
            ("foundation-read", "01", "--agent", "a2"),
            ("review-wave", "1"),
            ("spec-against-brief", ".scratch/feat/reviews/00.md"),
            ("merge-start", "01", "abc1234"),
            ("merge-end", "01", "def5678"),
            ("observation", "the walker found a thing"),
            ("note", "free prose, said in a sentence"),
        ]
        for words in lines:
            code, out = repo.gate("log", "feat", *words)
            self.assertEqual(code, 0, "%s: %s" % (words, out))
        text = self.log_text(repo).split("\n")
        for words, line in zip(lines, text):
            self.assertRegex(line, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2} %s" % words[0])
        self.assertTrue(text[0].endswith("dispatch 01 implementer --agent a1"), text[0])
        self.assertTrue(text[8].endswith("observation the walker found a thing"), text[8])
        for bad in (("dispatch", "01", "implementer"), ("dispatch", "x", "implementer", "--agent", "a"), ("merged", "07", "at", "abc"),
                    ("report", "01"), ("review-wave", "one"), ("note",), ("merge-end", "01"), ("foundation-read", "01")):
            code, out = repo.gate("log", "feat", *bad)
            self.assertEqual(code, 2, "%s: %s" % (bad, out))
            self.assertIn("refused by log-", out)
        self.assertEqual(len(self.log_text(repo).strip().split("\n")), len(lines))

    def test_a_follow_up_dispatch_is_a_valid_log_line(self):
        """A follow-up dispatch is a valid log line"""
        repo = self.done_repo()
        code, out = repo.gate("log", "feat", "dispatch", "3", "implementer", "--agent", "f1", "--follow-up")
        self.assertEqual(code, 0, out)
        self.assertIn(" dispatch 03 implementer --agent f1 --follow-up", self.log_text(repo))
        self.assertIn(" dispatch 03 implementer --agent f1 --follow-up", repo.gate("log", "feat")[1])
        self.assertEqual(repo.gate("log", "feat", "--agents")[1].strip(), "03 implementer f1")
        for bad in (("dispatch", "03", "implementer", "--follow-up"), ("dispatch", "03", "implementer", "--agent", "--follow-up"),
                    ("dispatch", "03", "implementer", "--follow-up", "--agent", "f2"), ("dispatch", "03", "implementer", "--agent", "f2", "--again")):
            code, out = repo.gate("log", "feat", *bad)
            self.assertEqual(code, 2, "%s: %s" % (bad, out))
            self.assertIn("refused by log-", out)
        code, out = repo.gate("log", "feat", "dispatch", "03", "implementer", "--agent", "f1", "--follow-up")
        self.assertEqual(code, 2, out)
        self.assertIn("already in the feat log", out)

    def test_log_lists_agent_ids(self):
        """Log lists agent ids"""
        repo = self.done_repo()
        path = os.path.join(repo.root, ".git", "factory")
        os.makedirs(path)
        with open(os.path.join(path, "build-log-feat.md"), "w", encoding="utf-8") as handle:
            handle.write("- 2026-11-07 14:26 Dispatched implementer for 01. Agent id zzz.\n- 2026-11-07 14:30 dispatch: merger prose\n")
        repo.gate("log", "feat", "dispatch", "02", "implementer", "--agent", "a2")
        repo.gate("log", "feat", "dispatch", "01", "implementer", "--agent", "a1")
        repo.gate("log", "feat", "foundation-read", "01", "--agent", "r1")
        repo.gate("log", "feat", "dispatch", "01", "ticket-reviewer", "--agent", "a3")
        code, out = repo.gate("log", "feat", "--agents")
        self.assertEqual(code, 0, out)
        self.assertEqual([l for l in out.split("\n") if l.strip()],
                         ["01 foundation-read r1", "01 implementer a1", "01 ticket-reviewer a3", "02 implementer a2"])

    def test_log_refuses_a_malformed_dispatch_line(self):
        """Log refuses a malformed dispatch line"""
        repo = self.done_repo()
        for bad in (("dispatch", "03", "implementer"), ("dispatch", "03", "implementer", "agent-x", "extra"), ("dispatch", "03", "implementer", "agent-x")):
            code, out = repo.gate("log", "feat", *bad)
            self.assertEqual(code, 2, "%s: %s" % (bad, out))
        path = os.path.join(repo.root, ".git", "factory")
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "build-log-feat.md"), "w", encoding="utf-8") as handle:
            handle.write("2026-11-07T10:00:00 dispatch 03 implementer\n2026-11-07T10:01:00 dispatch 03 implementer agent-x extra\n")
        self.assertEqual(repo.gate("log", "feat", "--agents")[1].strip(), "no agent ids logged for feat")

    def test_log_treats_3_and_03_as_one_ticket(self):
        """Log treats 3 and 03 as one ticket"""
        repo = self.done_repo()
        repo.gate("log", "feat", "dispatch", "3", "implementer", "--agent", "a1")
        repo.gate("log", "feat", "report", "03", "implementer")
        self.assertIn(" dispatch 03 implementer --agent a1", self.log_text(repo))
        self.assertIn(" report 03 implementer", self.log_text(repo))
        self.assertEqual(repo.gate("log", "feat", "--agents")[1].strip(), "03 implementer a1")

    def test_open_appends_a_numbered_item(self):
        """Open appends a numbered item"""
        repo = self.done_repo()
        code, out = repo.gate("open", "feat", "Keep the log in the git directory. Recommended: do.")
        self.assertEqual(code, 0, out)
        repo.write(".scratch/feat/spec.md", "# Feat\n\n## Open list\n\nSilence accepts.\n\n1. **First.** text\n2. **Second.** text\n\n## Comments\n\n- c\n")
        code, out = repo.gate("open", "feat", "Third thing.")
        self.assertEqual(code, 0, out)
        with open(os.path.join(repo.root, ".scratch/feat/spec.md"), encoding="utf-8") as handle:
            spec = handle.read()
        self.assertIn("2. **Second.** text\n3. Third thing.\n\n## Comments", spec)
        self.assertIn("open 3 Third thing.", self.log_text(repo))
        self.assertEqual(repo.gate("open", "feat")[0], 2)
        self.assertEqual(repo.gate("open", "nosuch", "x")[0], 2)

    def test_open_creates_the_section(self):
        """Open creates the section when the spec has none"""
        repo = self.done_repo()
        self.assertEqual(repo.gate("open", "feat", "A first item.")[0], 0)
        with open(os.path.join(repo.root, ".scratch/feat/spec.md"), encoding="utf-8") as handle:
            self.assertTrue(handle.read().rstrip().endswith("## Open list\n\n1. A first item."))

    def test_stats_prints_the_log_span(self):
        """Stats prints the log's span"""
        repo = self.done_repo()
        path = os.path.join(repo.root, ".git", "factory")
        os.makedirs(path)
        with open(os.path.join(path, "build-log-feat.md"), "w", encoding="utf-8") as handle:
            handle.write("- 2026-11-07 14:26 free prose\n2026-11-07T15:30:00 note later\n")
        code, out = repo.gate("stats")
        self.assertEqual(code, 0, out)
        self.assertIn("build log feat: first 2026-11-07 14:26, last 2026-11-07T15:30:00 (2 lines)", out)
        self.assertIn("guard: no refusals logged", out)

    def test_merge_lines_in_the_form_merge_writes_them_are_read(self):
        """Merge lines are read as written"""
        repo = self.done_repo()
        path = os.path.join(repo.root, ".git", "factory")
        os.makedirs(path)
        with open(os.path.join(path, "build-log-feat.md"), "w", encoding="utf-8") as handle:
            handle.write("- 2026-11-07 15:30 merge-start 01 abc1234\n- 2026-11-07 15:31 merge-end 01 red unit\n- 2026-11-07 15:32 merge-end 01 failed\n")
        from gate.log import read_log
        entries = read_log(repo.root, "feat")
        self.assertEqual([(e["verb"], e["args"]) for e in entries],
                         [("merge-start", ["01", "abc1234"]), ("merge-end", ["01", "red", "unit"]), ("merge-end", ["01", "failed"])])
