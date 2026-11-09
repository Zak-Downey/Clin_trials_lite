"""`gate.py lint`, `checks`, `red` and walk results.

Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import ast
import glob
import json
import os
import re
import unittest

from fixtures import FACTORY, Repo


class Lint(unittest.TestCase):
    RULE = {"name": "forced-click", "paths": ["walks/[!l]*.js"], "pattern": "force:\\s*true", "why": "click as a user does"}

    def test_lint_reports_a_matching_line(self):
        """Lint reports a matching line"""
        repo = Repo(forbid=[self.RULE, dict(self.RULE, name="nothing-here", paths=["nowhere/*.js"])])
        repo.write("walks/02.js", "ok();\nawait b.click({ force: true });\nawait c.click({ force: true }); // factory-allow: hidden\n")
        code, out = repo.gate("lint")
        self.assertEqual(code, 1)
        self.assertIn("walks/02.js:2 forced-click: click as a user does", out)
        self.assertNotIn("walks/02.js:3", out)
        self.assertNotIn("nothing-here", out)
        self.assertIn("lint: 1 problem(s)", out)

    def test_lint_reports_nothing_when_no_file_matches(self):
        """Lint reports nothing when a glob matches no file"""
        repo = Repo(forbid=[dict(self.RULE, paths=["nowhere/*.js"])])
        code, out = repo.gate("lint")
        self.assertEqual((code, out.strip()), (0, "lint: clean"))

    def test_lint_excludes_the_helper_by_glob(self):
        """Lint excludes the helper by glob"""
        repo = Repo(forbid=[self.RULE])
        repo.write("walks/lib.js", "await b.click({ force: true });\n")
        self.assertEqual(repo.gate("lint")[0], 0)
        repo.write("walks/02.js", "await b.click({ force: true });\n")
        code, out = repo.gate("lint")
        self.assertEqual(code, 1)
        self.assertIn("walks/02.js:1", out)
        self.assertNotIn("walks/lib.js", out)


GATE_PACKAGE = os.path.join(FACTORY, "gate")
REPO_TOOL = re.compile(r"\b(npm|npx|stryker|playwright)\b|scripts/run-|run-walks|run-tests", re.I)
OTHER_TRACKER = re.compile(r"\b[a-z]+(-[a-z]+)+ (ticket|review) (\d+|%[sd])", re.I)


def gate_strings():
    """(file, line, text) of each string a gate module could print: every string constant outside a docstring."""
    found = []
    for path in sorted(glob.glob(os.path.join(GATE_PACKAGE, "*.py")) + [os.path.join(FACTORY, "gate.py")]):
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        docstrings = {id(n.body[0].value) for n in ast.walk(tree) if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))
                      and n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
        found += [(os.path.basename(path), n.lineno, n.value) for n in ast.walk(tree)
                  if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings]
    return found


class GateMessages(unittest.TestCase):
    """What the gate prints names no repo's tool and cites no other tracker. Fixture: the gate's own source, read as a syntax tree.
    It lacks: strings built at run time from configuration, which are the repo's own words."""

    def test_no_gate_message_names_a_repo_tool(self):
        """No gate message names a repo tool"""
        strings = gate_strings()
        self.assertTrue(strings)
        bad = ["%s:%d %r" % (f, n, t[:60]) for f, n, t in strings if REPO_TOOL.search(t) and not t.startswith("(?:")]  # the directive's pattern is a format
        self.assertEqual(bad, [])
        code, out = Repo().gate()
        self.assertFalse(REPO_TOOL.search(out), out)

    def test_no_gate_message_cites_another_repos_tracker(self):
        """No gate message cites another repo's tracker"""
        bad = ["%s:%d %r" % (f, n, t[:60]) for f, n, t in gate_strings() if OTHER_TRACKER.search(t)]
        self.assertEqual(bad, [])


class Checks(unittest.TestCase):
    def test_checks_names_a_red_check(self):
        """Checks names a red check"""
        repo = Repo(checks=[{"name": "unit", "command": "echo fine-output"}, {"name": "walks", "command": "echo boom-output; exit 3"}])
        code, out = repo.gate("checks")
        self.assertEqual(code, 1)
        self.assertIn("check walks: RED, exit 3", out)
        self.assertIn("check unit: green", out)
        for name, said in (("unit", "fine-output"), ("walks", "boom-output")):
            line = [l for l in out.split("\n") if l.startswith("check %s:" % name)][0]
            path = line.split("output: ")[1].rstrip(")") if "output: " in line else line.split("Read ")[1]
            with open(path) as handle:
                self.assertEqual(handle.read().strip(), said)

    def test_checks_only_runs_one_check(self):
        """Checks --only runs one check"""
        repo = Repo(checks=[{"name": "unit", "command": "exit 4"}, {"name": "walks", "command": "true"}])
        code, out = repo.gate("checks", "--only", "walks")
        self.assertEqual(code, 0, out)
        self.assertIn("check walks: green", out)
        self.assertNotIn("check unit", out)
        lint = Repo(checks=[{"name": "walks", "command": "true"}], forbid=[Lint.RULE])
        lint.write("walks/02.js", "await b.click({ force: true });\n")
        code, out = lint.gate("checks", "--only", "walks")
        self.assertEqual(code, 1)
        self.assertIn("lint: walks/02.js:1 forced-click", out)
        code, out = repo.gate("checks", "--only", "nonesuch")
        self.assertEqual(code, 2)
        self.assertIn("no check named nonesuch", out)


class RedCommand(unittest.TestCase):
    def test_red_copies_a_unit_run_into_the_feature_folder(self):
        """Red copies a unit run into the feature folder"""
        repo = Repo(checks=[{"name": "unit", "command": "echo 'not ok 1 - the broken thing'; exit 1"}])
        repo.ticket("01")
        repo.commit()
        tip = repo.head()
        code, out = repo.gate("red", "feat", "01", "unit")
        self.assertEqual(code, 0, out)
        path = os.path.join(repo.root, ".scratch", "feat", "red", "01-unit-%s.txt" % tip[:7])
        self.assertTrue(os.path.isfile(path), out)
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().split("\n")
        self.assertEqual(lines[0], "# tip %s" % tip)
        self.assertIn("not ok 1 - the broken thing", lines)
        self.assertEqual(repo.gate("red", "feat", "01", "nothing")[0], 2)
        green = Repo(checks=[{"name": "unit", "command": "echo 'ok 1 - fine'"}])
        green.ticket("01")
        green.commit()
        self.assertIn("passed", green.gate("red", "feat", "01", "unit")[1])

    def test_red_keeps_the_runners_tip_line(self):
        """Red keeps the runner's tip line"""
        runner = "echo '# tip 0123456789abcdef0123456789abcdef01234567'; echo 'not ok 1 - the broken thing'; echo '## Result'; exit 1"
        repo = Repo(checks=[{"name": "unit", "command": runner}])
        repo.ticket("01")
        repo.commit()
        tip = repo.head()
        self.assertEqual(repo.gate("red", "feat", "01", "unit")[0], 0)
        with open(os.path.join(repo.root, ".scratch", "feat", "red", "01-unit-%s.txt" % tip[:7]), encoding="utf-8") as handle:
            lines = handle.read().split("\n")
        self.assertEqual(lines[0], "# tip %s" % tip)  # the runner's own tip line is the first line's source; ours is the commit the run was made at
        self.assertEqual([l for l in lines if l.startswith("# tip")], ["# tip %s" % tip])
        self.assertEqual(lines[1:3], ["not ok 1 - the broken thing", "## Result"])


class WalkResult(unittest.TestCase):
    """The walk runner's Result section, read by the checks and the ready gate."""

    TITLE = "stale page: Refresh warnings shows the banner"

    def walk_repo(self, result_lines, exit_code):
        repo = Repo(checks=[{"name": "walks", "command": "echo 'Walk output written to OUT (exit %d); read that file.'; exit %d" % (exit_code, exit_code)}])
        out = os.path.join(repo.root, "walk-output.txt")
        with open(out, "w", encoding="utf-8") as handle:
            handle.write("# tip abc1234\n...spec output...\n\n## Result\n\ntotal duration: 3s\n" + "\n".join(result_lines) + "\n")
        repo.write("docs/agents/local/factory.json", json.dumps({
            "tracker": ".scratch", "evidence": {"test": ["test"], "walk": ["walks"]},
            "checks": [{"name": "walks", "command": "echo 'Walk output written to %s (exit %d); read that file.'; exit %d" % (out, exit_code, exit_code)}]}))
        repo.ticket("01")
        repo.write(".gitignore", "walk-output.txt\n")
        repo.commit()
        return repo

    def flake_line(self, path="/tmp/retry-1-x.txt"):
        return "walks/06.walk.js \u203a %s: red under load, green alone (retry: %s)" % (self.TITLE, path)

    def test_checks_names_the_failing_walk_test(self):
        """Checks names the failing walk test"""
        repo = self.walk_repo(["walks/01.walk.js \u203a the form is on top: red alone (retry: /tmp/retry-1-01.txt)", self.flake_line()], 1)
        code, out = repo.gate("checks")
        self.assertEqual(code, 1)
        self.assertIn("RED walks: walks/01.walk.js \u203a the form is on top (/tmp/retry-1-01.txt)", out)
        self.assertIn("FLAKE walks: walks/06.walk.js \u203a %s (retry: /tmp/retry-1-x.txt)" % self.TITLE, out)

    def test_ready_records_a_flake(self):
        """Ready records a flake"""
        repo = self.walk_repo([self.flake_line()], 0)
        code, out = repo.gate("ready", "feat")
        self.assertEqual(code, 0, out)
        self.assertIn("flaked 1 time(s)", out)
        with open(os.path.join(repo.root, "docs", "agents", "local", "flakes.jsonl"), encoding="utf-8") as handle:
            entry = json.loads(handle.readline())
        self.assertEqual((entry["file"], entry["title"], entry["feature"], entry["tip"]), ("walks/06.walk.js", self.TITLE, "feat", repo.head()))
        self.assertRegex(entry["date"], r"^\d{4}-\d{2}-\d{2}$")
        from gate.records import unclassified, well_typed
        self.assertEqual(unclassified("flakes", entry), [])
        self.assertTrue(well_typed("flakes", entry))

    def test_ready_counts_flakes_past_a_line_of_the_wrong_type(self):
        """Ready's flake count skips a flakes line with a list title instead of crashing"""
        repo = self.walk_repo([self.flake_line()], 0)
        repo.write("docs/agents/local/flakes.jsonl", json.dumps({"date": "d", "feature": "feat", "file": "f", "title": [self.TITLE], "tip": "t"}) + "\n[1]\n")
        repo.commit()
        code, out = repo.gate("ready", "feat")
        self.assertEqual(code, 0, out)
        self.assertIn("flaked 1 time(s)", out)

    def test_ready_refuses_the_third_flake_without_a_ticket(self):
        """Ready refuses the third flake without a ticket"""
        repo = self.walk_repo([self.flake_line()], 0)
        old = json.dumps({"date": "2026-11-06", "feature": "x", "file": "walks/06.walk.js", "title": self.TITLE, "tip": "841f557"})
        repo.write("docs/agents/local/flakes.jsonl", old + "\n" + old + "\n")
        repo.write("docs/agents/local/ledger.md", "| 2026-11-06 | x | `%s` flaked | y | z | UNRESOLVED. Needs a ticket if it is seen again; see .scratch/x/spec.md |\n" % self.TITLE)
        repo.commit()
        code, out = repo.gate("ready", "feat")
        self.assertEqual(code, 1, out)
        self.assertIn("has flaked 3 times", out)
        self.assertFalse(os.path.exists(os.path.join(repo.root, ".git", "factory-ready")))
        # The same count with a ticket named in the row passes.
        repo.write("docs/agents/local/flakes.jsonl", old + "\n" + old + "\n")
        repo.write("docs/agents/local/ledger.md", "| 2026-11-06 | x | `%s` flaked | y | z | Fixed in kit-hardening ticket 09 |\n" % self.TITLE)
        repo.commit()
        code, out = repo.gate("ready", "feat")
        self.assertEqual(code, 0, out)
        # A bug spec folder under .scratch/ also lifts it.
        repo.write("docs/agents/local/flakes.jsonl", old + "\n" + old + "\n")
        repo.write("docs/agents/local/ledger.md", "| 2026-11-06 | x | `%s` flaked | y | z | Bug spec .scratch/walk-flake/ |\n" % self.TITLE)
        repo.commit()
        self.assertEqual(repo.gate("ready", "feat")[0], 0)

    def test_a_ticket_in_an_earlier_ledger_cell_does_not_lift_the_flake_refusal(self):
        """A ticket in an earlier ledger cell does not lift the flake refusal"""
        repo = self.walk_repo([self.flake_line()], 0)
        old = json.dumps({"date": "2026-11-06", "feature": "x", "file": "walks/06.walk.js", "title": self.TITLE, "tip": "841f557"})
        repo.write("docs/agents/local/flakes.jsonl", old + "\n" + old + "\n")
        repo.write("docs/agents/local/ledger.md", "| 2026-11-06 | x | `%s` flaked after ticket 07's walk | y | z | Not fixed |\n" % self.TITLE)
        repo.commit()
        code, out = repo.gate("ready", "feat")
        self.assertEqual(code, 1, out)
        self.assertIn("has flaked 3 times", out)


class LintDirectory(unittest.TestCase):
    def test_lint_reads_a_forbid_path_naming_a_directory(self):
        """Lint reads a forbid path naming a directory"""
        repo = Repo(forbid=[{"name": "no-console-log", "pattern": "console\\.log", "paths": ["src/"], "why": "Use the logger."}])
        repo.write("src/a.js", "console.log(1)\n")
        code, out = repo.gate("lint")
        self.assertEqual(code, 1, out)
        self.assertIn("src/a.js:1 no-console-log: Use the logger.", out)

    def test_lint_reads_a_file_nested_under_a_forbid_directory(self):
        """Lint reads a file nested under a forbid directory"""
        repo = Repo(forbid=[{"name": "no-console-log", "pattern": "console\\.log", "paths": ["src/"], "why": "Use the logger."}])
        repo.write("src/deep/er/b.js", "ok();\nconsole.log(2)\n")
        code, out = repo.gate("lint")
        self.assertEqual(code, 1, out)
        self.assertIn("src/deep/er/b.js:2 no-console-log", out)
