"""The refusal helper, the log grammar as the audit reads it, the report audit's allow marker and the tracker accessor.

Lacks: a real build's log, a real report and a repo whose tracker is not `.scratch`; the fixtures are the shared throwaway repo.
Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import glob
import json
import os
import re
import unittest

from fixtures import FACTORY, Repo
from gate import audit, log
from gate.config import allowed
from gate.refuse import RULES, refusal

GATE_DIR = os.path.join(FACTORY, "gate")
PREFIXES = ("gate:", "merge: refused", "close: refused", "release refused", "NOT READY", "merge: aborted",
            "merge: git could not", "merge: the commit failed", "merge: %s conflicts", "ticket %s may NOT")
SHAPE = re.compile(r"^gate: refused by [\w-]+: .+\. Needs: .+$", re.M)


def literal_refusals(path):
    """Lines of a module that print, raise or exit with a string starting a refusal prefix, other than a usage line."""
    found = []
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not re.search(r"\b(print\(|SystemExit\(|sys\.exit\()", line):
                continue
            for prefix in PREFIXES:
                if re.search(r"""\(\s*f?["']%s""" % re.escape(prefix), line) and not re.search(r"""["']gate: usage:""", line):
                    found.append("%s:%d" % (os.path.basename(path), number))
    return found


class OneHelper(unittest.TestCase):
    def test_no_module_words_a_refusal_outside_the_helper(self):
        """No module words a refusal outside the helper"""
        found = []
        for path in sorted(glob.glob(os.path.join(GATE_DIR, "*.py"))):
            if os.path.basename(path) != "refuse.py":
                found += literal_refusals(path)
        self.assertEqual(found, [])

    def test_the_scan_finds_a_refusal_printed_by_hand(self):
        """The scan finds a refusal printed by hand"""
        path = os.path.join(Repo().root, "m.py")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write('print("gate: usage: x")\nprint("NOT READY: 2 problem(s)")\nraise SystemExit("gate: no ticket")\nplain = "gate: x"\n')
        self.assertEqual(literal_refusals(path), ["m.py:2", "m.py:3"])


    def test_the_scan_finds_every_prefix_and_every_call_form(self):
        """The scan finds every prefix and every call form"""
        planted = [
            'print("gate: x")',
            'print("merge: refused. x")',
            'print("close: refused. x")',
            'print("release refused: x")',
            'print("NOT READY: x")',
            'raise SystemExit("gate: x")',
            'sys.exit("gate: x")',
            'sys.exit("NOT READY: x")',
            'print("merge: aborted. x")',
            'print("merge: git could not merge x")',
            'print("merge: the commit failed:")',
            'print("merge: %s conflicts in these files" % b)',
            'print("ticket %s may NOT be marked done" % n)',
        ]
        path = os.path.join(Repo().root, "m.py")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(planted) + "\n")
        self.assertEqual(literal_refusals(path), ["m.py:%d" % n for n in range(1, len(planted) + 1)])


CALL_RE = re.compile(r"""\b(?:refuse|refusal)\(\s*(["'][\w-]+["']|\w+)""")


def named_rules(path):
    """(line, first argument) of every refuse( or refusal( call in a module, other than the helper's own definitions."""
    found = []
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if re.match(r"\s*def ", line):
                continue
            for match in CALL_RE.finditer(line):
                found.append(("%s:%d" % (os.path.basename(path), number), match.group(1)))
    return found


class RuleVocabulary(unittest.TestCase):
    def test_every_refusal_in_the_gate_names_a_listed_rule(self):
        """Every refusal in the gate names a listed rule"""
        unlisted = []
        for path in sorted(glob.glob(os.path.join(GATE_DIR, "*.py"))):
            if os.path.basename(path) == "refuse.py":
                continue
            for where, argument in named_rules(path):
                if argument.strip("\"'") not in RULES or argument[0] not in "\"'":
                    unlisted.append("%s %s" % (where, argument))
        self.assertEqual(unlisted, [])

    def test_the_scan_finds_an_unlisted_rule_and_a_computed_one(self):
        """The scan finds an unlisted rule and a computed one"""
        path = os.path.join(Repo().root, "m.py")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write('return refuse("made-up", "a", "b")\nraise SystemExit(refusal(name, "a", "b"))\nreturn refuse("log-verb", "a", "b")\n')
        self.assertEqual(named_rules(path), [("m.py:1", '"made-up"'), ("m.py:2", "name"), ("m.py:3", '"log-verb"')])

    def test_every_listed_rule_has_a_meaning_and_is_used(self):
        """Every listed rule has a meaning and is used"""
        used = set()
        for path in sorted(glob.glob(os.path.join(GATE_DIR, "*.py"))):
            used |= {a.strip("\"'") for _, a in named_rules(path)}
        for rule, meaning in RULES.items():
            self.assertTrue(meaning.strip(), rule)
        self.assertEqual(sorted(set(RULES) - used), [])


class Helper(unittest.TestCase):
    def test_a_refusal_has_one_stop_before_needs_and_stays_one_line(self):
        """A refusal has one stop before Needs and stays one line"""
        line = refusal("r", "what happened.", "n")
        self.assertEqual(line, "gate: refused by r: what happened. Needs: n")
        self.assertEqual(line.count("."), 1)
        folded = refusal("r", "two\nlines", "a\n  b")
        self.assertNotIn("\n", folded)
        self.assertEqual(folded, "gate: refused by r: two lines. Needs: a b")


class EveryRefusal(unittest.TestCase):
    def last(self, out):
        return [l for l in out.strip().split("\n") if l][-1]

    def assert_refused(self, repo, *args):
        code, out = repo.gate(*args)
        self.assertNotEqual(code, 0, out)
        line = self.last(out)
        self.assertRegex(line, SHAPE, "%s: %s" % (" ".join(args), out))
        return line

    def repo(self):
        repo = Repo()
        repo.ticket("01", status="ready-for-agent", boxes="- [ ] Opens in the browser")
        repo.commit()
        return repo

    def test_ticket_merge_release_ready_and_close_each_name_a_rule_and_a_need(self):
        """Each gate command that refuses names a rule and a need"""
        repo = self.repo()
        self.assert_refused(repo, "ticket", "feat")
        self.assertRegex(self.assert_refused(repo, "ticket", "feat", "01"), r"^gate: refused by ticket-gate: ticket 01 may NOT be marked done: 1 problem\(s\), listed above\. Needs: .+")
        self.assert_refused(repo, "merge", "feat", "01", "ticket/none")
        self.assert_refused(repo, "release", "feat")
        self.assert_refused(repo, "ready", "feat")
        self.assert_refused(repo, "ready", "feat", "--records", "deadbeef")
        self.assert_refused(repo, "close", "feat")
        self.assert_refused(repo, "mutate", "feat", "01")

    def test_log_open_config_and_ledger_each_name_a_rule_and_a_need(self):
        """Log, open, config and ledger each name a rule and a need"""
        repo = self.repo()
        self.assert_refused(repo, "log", "feat", "merge-end", "01", "merged")
        self.assert_refused(repo, "log", "feat", "bogus", "x")
        for words in (("merge-start", "01"), ("merge-end", "01"), ("report", "01"), ("dispatch", "01")):
            line = self.assert_refused(repo, "log", "feat", *words)
            self.assertIn("refused by log-grammar", line)
            self.assertIn("Needs: %s" % log.LOG_USAGE[words[0]], line)
        self.assert_refused(repo, "open", "nofeat", "an item")
        self.assert_refused(repo, "ledger", "add", "--feature", "feat")
        self.assert_refused(repo, "frobnicate")
        repo.write("docs/agents/local/factory.json", json.dumps({"checks": "not a list"}))
        self.assert_refused(repo, "config")
        self.assert_refused(repo, "frontier", "feat")

    def test_a_refusal_is_one_line(self):
        """A refusal is one line"""
        repo = self.repo()
        code, out = repo.gate("log", "feat", "merge-end", "01", "merged")
        self.assertEqual(len([l for l in out.split("\n") if l.startswith("gate: refused")]), 1, out)


class LogGrammar(unittest.TestCase):
    def test_merge_end_takes_a_hash_or_an_abort_word_and_refuses_merged(self):
        """Merge-end takes a hash or an abort word and refuses merged"""
        repo = Repo()
        repo.ticket("01")
        repo.commit()
        for result in ("abc1234", "a" * 40, "refused", "red", "conflict", "failed"):
            code, out = repo.gate("log", "feat", "merge-end", "01", result)
            self.assertEqual(code, 0, "%s: %s" % (result, out))
        for result in ("merged", "abc123", "a" * 41, "xyz1234"):
            code, out = repo.gate("log", "feat", "merge-end", "01", result)
            self.assertEqual(code, 2, "%s: %s" % (result, out))
            self.assertIn("7 to 40 hex characters", out)
            self.assertRegex(out, SHAPE)


class OneAbortList(unittest.TestCase):
    def test_the_audit_and_the_writer_share_one_tuple_of_abort_words(self):
        """The audit and the writer share one tuple of abort words"""
        self.assertIs(audit.ABORT_WORDS, log.ABORT_WORDS)


class AllowMarker(unittest.TestCase):
    def test_the_marker_needs_a_why_and_must_not_be_quoted(self):
        """The marker needs a why and must not be quoted"""
        self.assertTrue(allowed("x = 1  # factory-allow: a reason"))
        self.assertFalse(allowed("x = 1  # factory-allow:"))
        self.assertFalse(allowed("x = 1  # factory-allow:   "))
        self.assertFalse(allowed("the doc says `factory-allow: <why>` is the marker"))
        self.assertFalse(allowed("quoted: `factory-allow: a real reason` inside backticks"))
        self.assertFalse(allowed("a hash on a line carrying `factory-allow: <why>`"))


class ReportHashes(unittest.TestCase):
    def audit(self, extra):
        repo = Repo()
        repo.ticket("01")
        repo.commit()
        repo.write(".scratch/feat/report.md", "- Built tip: %s\n%s\n" % (repo.head()[:7], extra))
        return repo.gate("audit", "feat", "--report", os.path.join(repo.root, ".scratch/feat/report.md"))

    def test_a_hash_from_another_repo_passes_on_a_line_with_the_allow_marker(self):
        """A hash from another repo passes on a line with the allow marker"""
        code, out = self.audit("Anchor Point was at 9f3a2c1 factory-allow: another repo's commit")
        self.assertNotIn("9f3a2c1", out)
        self.assertIn("ok: report", out)

    def test_a_marker_without_a_why_or_only_quoted_excuses_nothing(self):
        """A marker without a why or only quoted excuses nothing"""
        for tail in ("Anchor Point was at 9f3a2c1 factory-allow:", "the doc says `factory-allow: <why>` about 9f3a2c1"):
            code, out = self.audit(tail)
            self.assertEqual(code, 1, tail + out)
            self.assertIn("9f3a2c1", out)

    def test_the_same_hash_on_a_plain_line_is_refused_naming_the_marker(self):
        """The same hash on a plain line is refused naming the marker"""
        code, out = self.audit("Anchor Point was at 9f3a2c1")
        self.assertEqual(code, 1, out)
        self.assertIn("9f3a2c1", out)
        self.assertIn("factory-allow:", out)


class TrackerAccessor(unittest.TestCase):
    def test_only_the_accessor_and_load_config_read_the_tracker_key(self):
        """Only the accessor and load_config read the tracker key"""
        pattern = re.compile(r"""config\.get\(\s*["']tracker["']|config\[\s*["']tracker["']\s*\]""")
        found = []
        for path in sorted(glob.glob(os.path.join(GATE_DIR, "*.py"))):
            with open(path, encoding="utf-8") as handle:
                for number, line in enumerate(handle, 1):
                    if pattern.search(line) and not allowed(line):
                        found.append("%s:%d" % (os.path.basename(path), number))
        self.assertEqual(found, [])

    def test_a_tracker_written_with_a_dot_slash_or_a_trailing_slash_is_one_folder(self):
        """A tracker written with a dot slash or a trailing slash is one folder"""
        for written in ("./.scratch", ".scratch/", "./.scratch/"):
            repo = Repo()
            repo.ticket("01")
            repo.write("docs/agents/local/factory.json", json.dumps({"tracker": written, "checks": []}))
            code, out = repo.gate("config")
            self.assertEqual(code, 0, out)
            self.assertEqual(json.JSONDecoder().raw_decode(out)[0]["tracker"], ".scratch", written)
            code, out = repo.gate("features")
            self.assertEqual(out.strip(), "feat", written)
