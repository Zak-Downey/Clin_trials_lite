"""The entry shim and the command line: every subcommand reached, an unknown one a usage error, and the package's shape.

Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import ast
import glob
import os
import re
import subprocess
import sys
import tempfile
import unittest

from fixtures import CLEAN_ENV, FACTORY, GATE, HERE, Repo

from gate import cli

PACKAGE = os.path.join(FACTORY, "gate")
PARENT = "." * 2  # a test that climbs out of the kit names the parent folder; this file builds the word, so it does not trip itself
PARENT_ATTR = "par" + "dir"  # the same word as an attribute of os


def usage_commands():
    """The subcommands the usage header names: `gate.py <command>` at the start of a line."""
    return sorted({m.group(1) for m in re.finditer(r"^  gate\.py (\w+)", cli.__doc__, re.M)})


class Shim(unittest.TestCase):
    def run_shim(self, repo, *args):
        result = subprocess.run([sys.executable, GATE] + list(args), cwd=repo.root, capture_output=True, text=True, env=CLEAN_ENV)
        return result.returncode, result.stdout + result.stderr

    def test_every_subcommand_is_reached_through_the_shim(self):
        """Every subcommand is reached through the shim"""
        commands = usage_commands()
        self.assertGreaterEqual(len(commands), 15, commands)
        repo = Repo()
        for command in commands:
            with self.subTest(command=command):
                code, out = self.run_shim(repo, command)
                self.assertIn(code, (0, 1, 2), out)
                self.assertNotIn("unknown command", out)
                self.assertNotIn("what an agent used to decide by memory", out, "the usage header, not the command")
                self.assertNotIn("Traceback", out)
        self.assertEqual(self.run_shim(repo, "features")[0], 0)

    def test_an_unknown_subcommand_is_a_usage_error_through_the_shim(self):
        """An unknown subcommand is a usage error through the shim"""
        code, out = self.run_shim(Repo(), "frobnicate")
        self.assertEqual(code, 2)
        self.assertIn("frobnicate is not a command", out)

    def test_no_command_prints_the_usage_and_exits_2(self):
        """No command prints the usage and exits 2"""
        code, out = self.run_shim(Repo())
        self.assertEqual(code, 2)
        self.assertIn("gate.py frontier <feature>", out)
        self.assertIn(".claude/factory/RULES", out)


class Package(unittest.TestCase):
    def modules(self):
        return sorted(glob.glob(os.path.join(PACKAGE, "*.py")))

    def test_no_gate_module_imports_the_command_line_module(self):
        """No gate module imports the command line module"""
        self.assertGreaterEqual(len(self.modules()), 14)
        for path in self.modules():
            if os.path.basename(path) == "cli.py":
                continue
            with open(path, encoding="utf-8") as handle:
                tree = ast.parse(handle.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    named = [node.module or ""] + ["%s.%s" % (node.module, a.name) for a in node.names]
                    self.assertFalse(any(n in ("gate.cli", "cli", ".cli") for n in named), "%s imports cli" % path)
                if isinstance(node, ast.Import):
                    self.assertFalse(any(a.name in ("gate.cli", "cli") for a in node.names), "%s imports cli" % path)

    def test_a_module_imports_only_what_it_uses(self):
        """A module imports only what it uses"""
        for path in self.modules():
            with open(path, encoding="utf-8") as handle:
                tree = ast.parse(handle.read())
            imported = set()
            for node in tree.body:
                if isinstance(node, ast.Import):
                    imported |= {(a.asname or a.name).split(".")[0] for a in node.names}
                if isinstance(node, ast.ImportFrom) and node.module != "__future__":
                    imported |= {a.asname or a.name for a in node.names}
            used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
            self.assertEqual(imported - used, set(), path)

    def test_every_module_has_its_own_test_file(self):
        """Every module has its own test file"""
        for path in self.modules():
            name = os.path.basename(path)[:-3]
            if name in ("__init__",):
                continue
            self.assertTrue(os.path.isfile(os.path.join(HERE, "test_%s.py" % name)), "no tests/test_%s.py" % name)


def climbs(source, path="<source>"):
    """The ways a test source climbs out of the kit: a problem per line, or an empty list."""
    problems = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Constant) and node.value == PARENT:
            problems.append("%s climbs a folder with the parent-folder name" % path)
        if isinstance(node, ast.Attribute) and node.attr == PARENT_ATTR:
            problems.append("%s climbs a folder with the parent-folder attribute of os" % path)
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "dirname":
            inner = node.args[0] if node.args else None
            if isinstance(inner, ast.Call) and getattr(inner.func, "attr", "") == "dirname":
                deeper = inner.args[0] if inner.args else None
                if isinstance(deeper, ast.Call) and getattr(deeper.func, "attr", "") == "dirname":
                    problems.append("%s takes the third parent folder of a path" % path)
    return problems


class Isolation(unittest.TestCase):
    def test_no_test_reads_outside_the_kit(self):
        """No test reads outside the kit"""
        for path in sorted(glob.glob(os.path.join(HERE, "*.py"))):
            with open(path, encoding="utf-8") as handle:
                self.assertEqual(climbs(handle.read(), path), [])

    def test_the_isolation_check_sees_each_way_of_climbing(self):
        """The isolation check sees each way of climbing"""
        self.assertEqual(len(climbs("import os\nX = os." + PARENT_ATTR)), 1)
        self.assertEqual(len(climbs("X = '" + PARENT + "'")), 1)
        self.assertEqual(len(climbs("import os\nX = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))")), 1)
        self.assertEqual(climbs("import os\nX = os.path.dirname(os.path.dirname(__file__))"), [])

    def test_the_gate_runs_with_no_local_factory_json(self):
        """The gate runs with no local factory.json"""
        with tempfile.TemporaryDirectory() as root:
            subprocess.run(["git", "-C", root, "init", "-q"], check=True, capture_output=True, env=CLEAN_ENV)
            self.assertFalse(os.path.exists(os.path.join(root, "docs")))
            result = subprocess.run([sys.executable, GATE, "lint"], cwd=root, capture_output=True, text=True, env=CLEAN_ENV)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("lint: clean", result.stdout)
            self.assertEqual(subprocess.run([sys.executable, GATE, "features"], cwd=root, capture_output=True, env=CLEAN_ENV).returncode, 0)
