"""Reading factory.json: what a missing file and a missing key fall back to.

Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import json
import os
import tempfile
import unittest

from fixtures import Repo

from gate.config import DEFAULT_CONFIG, load_config, schema_keys, validate, without_comments


class Config(unittest.TestCase):
    def test_a_missing_factory_json_is_the_defaults(self):
        """A missing factory json is the defaults"""
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(load_config(root), DEFAULT_CONFIG)

    def test_a_key_in_factory_json_replaces_its_default(self):
        """A key in factory json replaces its default"""
        repo = Repo(forbid=[{"pattern": "x"}])
        config = load_config(repo.root)
        self.assertEqual(config["forbid"], [{"pattern": "x"}])
        self.assertEqual(config["protected_branches"], DEFAULT_CONFIG["protected_branches"])
        self.assertTrue(os.path.isfile(os.path.join(repo.root, "docs", "agents", "local", "factory.json")))


def seed_path(here=None):
    """The seed factory.json, when this suite runs from the kit's source repo (the kit root is a folder named `kit`); else None."""
    parts = (here or os.path.dirname(os.path.abspath(__file__))).split(os.sep)
    kit_root = os.sep.join(parts[:parts.index("_claude")]) if "_claude" in parts else ""
    if os.path.basename(kit_root) != "kit":
        return None
    return os.path.join(os.path.dirname(kit_root), "seed", "docs", "agents", "local", "factory.json")


SEED = seed_path()
GOOD_CHECK = {"name": "unit", "command": "true", "proves": ["test"], "red_marker": "FAIL:"}


def write_config(repo, **keys):
    """Replace the repo's factory.json with exactly `keys`."""
    repo.write("docs/agents/local/factory.json", json.dumps(keys))


class ConfigCommand(unittest.TestCase):
    """`gate.py config` against throwaway repos. Fixture: small factory.json files; they lack a real repo's size."""

    def test_config_prints_the_effective_configuration_with_defaults(self):
        """Config prints the effective configuration with defaults"""
        repo = Repo()
        write_config(repo, checks=[GOOD_CHECK])
        code, out = repo.gate("config")
        self.assertEqual(code, 0, out)
        shown = json.loads(out[:out.rindex("}") + 1])
        self.assertEqual(shown["tracker"], ".scratch")
        self.assertEqual(shown["protected_branches"], ["main"])
        self.assertEqual(shown["standins_doc"], "docs/agents/local/repo.md")
        self.assertEqual(shown["checks"], [GOOD_CHECK])
        self.assertEqual(sorted(shown), sorted(schema_keys()))

    def test_config_refuses_an_unknown_key_by_name(self):
        """Config refuses an unknown key by name"""
        repo = Repo()
        write_config(repo, kit_prefx="kit-")
        code, out = repo.gate("config")
        self.assertEqual(code, 1, out)
        self.assertIn("kit_prefx", out)

    def test_config_ignores_a_comment_key_anywhere(self):
        """Config ignores a comment key anywhere"""
        repo = Repo()
        write_config(repo, checks=[dict(GOOD_CHECK, **{"$comment": "x"})], **{"$comment": "y"})
        code, out = repo.gate("config")
        self.assertEqual(code, 0, out)

    def test_config_refuses_a_check_without_a_command(self):
        """Config refuses a check without a command"""
        repo = Repo()
        write_config(repo, checks=[{"name": "unit"}])
        code, out = repo.gate("config")
        self.assertEqual(code, 1, out)
        self.assertIn("checks[0].command", out)

    def test_config_refuses_a_proves_value_outside_test_and_walk(self):
        """Config refuses a proves value outside test and walk"""
        repo = Repo()
        write_config(repo, checks=[dict(GOOD_CHECK, proves=["unit"])])
        code, out = repo.gate("config")
        self.assertEqual(code, 1, out)
        self.assertIn("checks[0].proves", out)

    def test_config_refuses_a_walk_check_without_walk_folders(self):
        """Config refuses a walk check without walk folders"""
        repo = Repo()
        write_config(repo, checks=[dict(GOOD_CHECK, proves=["walk"])])
        code, out = repo.gate("config")
        self.assertEqual(code, 1, out)
        self.assertIn("evidence.walk", out)

    def test_config_refuses_a_red_marker_that_does_not_compile(self):
        """Config refuses a red marker that does not compile"""
        repo = Repo()
        write_config(repo, checks=[dict(GOOD_CHECK, red_marker="(")])
        code, out = repo.gate("config")
        self.assertEqual(code, 1, out)
        self.assertIn("checks[0].red_marker", out)

    def test_config_refuses_mutate_paths_without_a_mutate_command(self):
        """Config refuses mutate paths without a mutate command"""
        repo = Repo()
        write_config(repo, mutate_paths=["src/"], mutate_report="r.json")
        code, out = repo.gate("config")
        self.assertEqual(code, 1, out)
        self.assertIn("mutate_command", out)

    def test_config_refuses_mutate_paths_without_a_mutate_report(self):
        """Config refuses mutate paths without a mutate report"""
        repo = Repo()
        write_config(repo, mutate_paths=["src/"], mutate_command="true")
        code, out = repo.gate("config")
        self.assertEqual(code, 1, out)
        self.assertIn("mutate_report", out)

    def test_config_reports_a_configured_folder_that_does_not_exist(self):
        """Config reports a configured folder that does not exist"""
        repo = Repo()
        write_config(repo, evidence={"test": ["nowhere/tests"], "walk": []})
        code, out = repo.gate("config")
        self.assertEqual(code, 0, out)
        self.assertIn("evidence.test: nowhere/tests does not exist", out)

    def test_config_says_when_no_mutation_runner_is_configured(self):
        """Config says when no mutation runner is configured"""
        repo = Repo()
        write_config(repo)
        code, out = repo.gate("config")
        self.assertIn("no mutation runner is configured", out)

    def test_config_advises_when_the_gate_s_tests_are_not_a_check(self):
        """Config advises when the gate's tests are not a check"""
        repo = Repo()
        write_config(repo, checks=[GOOD_CHECK])
        code, out = repo.gate("config")
        self.assertEqual(code, 0, out)
        self.assertEqual(out.count("gate's own tests"), 1)
        write_config(repo, checks=[dict(GOOD_CHECK, command="python3 -m unittest discover -s .claude/factory/tests")],
                     evidence={"test": [".claude/factory/tests"], "walk": []})
        code, out = repo.gate("config")
        self.assertNotIn("gate's own tests", out)

    def test_config_keys_prints_every_schema_key_once(self):
        """Config keys prints every schema key once"""
        code, out = Repo().gate("config", "--keys")
        self.assertEqual(code, 0, out)
        printed = [line.split()[0] for line in out.split("\n") if line and not line.startswith(" ")]
        self.assertEqual(printed, list(schema_keys()))

    def test_config_refuses_a_boolean_or_string_timeout(self):
        """Config refuses a boolean or string timeout"""
        for bad in (True, "600"):
            repo = Repo()
            write_config(repo, checks=[dict(GOOD_CHECK, timeout_s=bad)])
            code, out = repo.gate("config")
            self.assertEqual(code, 1, out)
            self.assertIn("checks[0].timeout_s", out)

    def test_config_advice_needs_both_a_check_and_the_evidence_folder_for_the_gate_s_tests(self):
        """Config advice needs both a check and the evidence folder for the gate's tests"""
        runs = dict(GOOD_CHECK, command="python3 -m unittest discover -s .claude/factory/tests")
        for checks, folders in (([runs], ["test"]), ([GOOD_CHECK], [".claude/factory/tests"])):
            repo = Repo()
            write_config(repo, checks=checks, evidence={"test": folders, "walk": []})
            code, out = repo.gate("config")
            self.assertEqual(code, 0, out)
            self.assertEqual(out.count("gate's own tests"), 1, out)

    def test_config_names_a_factory_json_that_is_not_json(self):
        """Config names a factory json that is not json"""
        repo = Repo()
        repo.write("docs/agents/local/factory.json", "{ nope")
        code, out = repo.gate("config")
        self.assertEqual(code, 1, out)
        self.assertIn("factory.json is not valid JSON", out)
        self.assertNotIn("Traceback", out)

    def test_config_keys_lists_the_fields_of_a_list_key(self):
        """Config keys lists the fields of a list key"""
        code, out = Repo().gate("config", "--keys")
        for field in schema_keys()["checks"]["fields"]:
            self.assertIn("  .%s  " % field, out)

    def test_checks_refuses_an_invalid_factory_json_before_running_anything(self):
        """Checks refuses an invalid factory.json before running anything"""
        repo = Repo()
        write_config(repo, checks=[{"name": "unit", "command": "touch ran"}], bogus=1)
        code, out = repo.gate("checks")
        self.assertEqual(code, 1, out)
        self.assertIn("bogus", out)
        self.assertFalse(os.path.exists(os.path.join(repo.root, "ran")))

    def test_ready_refuses_an_invalid_factory_json(self):
        """Ready refuses an invalid factory.json"""
        repo = Repo()
        write_config(repo, bogus=1)
        code, out = repo.gate("ready", "feat")
        self.assertEqual(code, 1, out)
        self.assertIn("bogus", out)

    def test_merge_and_release_refuse_an_invalid_factory_json(self):
        """Merge and release refuse an invalid factory.json"""
        repo = Repo()
        write_config(repo, bogus=1)
        for args in (("merge", "feat", "01", "ticket/01"), ("release", "feat")):
            code, out = repo.gate(*args)
            self.assertEqual(code, 1, out)
            self.assertIn("bogus", out)

    def test_the_seed_is_found_only_under_a_folder_named_kit(self):
        """The seed is found only under a folder named kit"""
        tests = os.sep.join(["", "r", "kit", "_claude", "factory", "tests"])
        self.assertEqual(seed_path(tests), os.sep.join(["", "r", "seed", "docs", "agents", "local", "factory.json"]))
        self.assertIsNone(seed_path(tests.replace("kit", "kitx")))
        self.assertIsNone(seed_path(os.sep.join(["", "r", ".claude", "factory", "tests"])))

    @unittest.skipUnless(SEED and os.path.isfile(SEED), "the seed is in the kit's source repo, not in an installed copy")
    def test_the_seed_factory_json_validates_with_every_key_present(self):
        """The seed factory.json validates with every key present"""
        with open(SEED, encoding="utf-8") as handle:
            raw = json.load(handle)
        self.assertEqual([k for k in raw if not k.startswith("$comment")], [k for k in schema_keys() if k != "prices"])
        self.assertEqual([k for k in schema_keys() if k != "prices" and "$comment " + k not in raw], [])
        with tempfile.TemporaryDirectory() as root:
            problems, _ = validate(without_comments(raw), root)
        self.assertEqual(problems, [])


class Prices(unittest.TestCase):
    """`prices` in factory.json. Fixture: one model; the real ids are whatever the user names."""

    def config_with(self, prices):
        repo = Repo()
        write_config(repo, checks=[GOOD_CHECK], prices=prices)
        return repo

    def test_a_well_formed_prices_block_passes_config_and_frontier_runs(self):
        """A well formed prices block passes config and frontier runs"""
        repo = self.config_with({"claude-opus": {"input": 15, "output": 75.5, "cache_read": 1.5, "cache_write": 0}, "claude-haiku": {}})
        code, out = repo.gate("config")
        self.assertEqual(code, 0, out)
        repo.write(".scratch/f/issues/01-a.md", "# 01\n\n**Status:** ready-for-agent\n")
        code, out = repo.gate("frontier", "f")
        self.assertNotIn("factory.json", out)

    def test_config_refuses_a_string_price_naming_the_model_and_kind(self):
        """Config refuses a string price naming the model and kind"""
        code, out = self.config_with({"claude-opus": {"input": "15"}}).gate("config")
        self.assertEqual(code, 1, out)
        self.assertIn("prices.claude-opus.input", out)

    def test_config_refuses_a_negative_price_naming_the_model_and_kind(self):
        """Config refuses a negative price naming the model and kind"""
        code, out = self.config_with({"claude-opus": {"output": -1}}).gate("config")
        self.assertEqual(code, 1, out)
        self.assertIn("prices.claude-opus.output", out)

    def test_config_checks_every_model_not_only_the_first(self):
        """Config checks every model not only the first"""
        code, out = self.config_with({"claude-opus": {"input": 1}, "claude-haiku": {"input": -2}}).gate("config")
        self.assertEqual(code, 1, out)
        self.assertIn("prices.claude-haiku.input", out)

    def test_config_refuses_a_boolean_price(self):
        """Config refuses a boolean price"""
        code, out = self.config_with({"claude-opus": {"input": True}}).gate("config")
        self.assertEqual(code, 1, out)

    def test_config_refuses_an_unknown_token_kind_naming_the_model_and_kind(self):
        """Config refuses an unknown token kind naming the model and kind"""
        code, out = self.config_with({"claude-opus": {"thinking": 3}}).gate("config")
        self.assertEqual(code, 1, out)
        self.assertIn("prices.claude-opus.thinking", out)

    def test_config_refuses_a_model_whose_prices_are_not_an_object(self):
        """Config refuses a model whose prices are not an object"""
        code, out = self.config_with({"claude-opus": 5}).gate("config")
        self.assertEqual(code, 1, out)
        self.assertIn("prices.claude-opus", out)

    def test_config_keys_lists_prices_with_type_default_and_fields(self):
        """Config keys lists prices with type default and fields"""
        code, out = Repo().gate("config", "--keys")
        line = [l for l in out.splitlines() if l.startswith("prices ")][0]
        self.assertIn("object", line)
        self.assertIn("default none", line)
        for kind in ("input", "output", "cache_read", "cache_write"):
            self.assertIn("  .%s " % kind, out)

    def test_the_seed_has_no_prices_key(self):
        """The seed has no prices key"""
        if not (SEED and os.path.isfile(SEED)):
            self.skipTest("the seed is in the kit's source repo")
        with open(SEED, encoding="utf-8") as handle:
            self.assertNotIn("prices", handle.read())


class ConfigReach(unittest.TestCase):
    def test_config_advises_a_forbid_rule_that_matches_no_file(self):
        """Config advises a forbid rule that matches no file"""
        repo = Repo()
        write_config(repo, checks=[GOOD_CHECK], forbid=[{"name": "no-x", "pattern": "x", "paths": ["nowhere/"], "why": "w"}])
        code, out = repo.gate("config")
        self.assertEqual(code, 0, out)
        advice = [l for l in out.split("\n") if l.startswith("advice:") and "no-x" in l]
        self.assertEqual(len(advice), 1, out)
        self.assertIn("nowhere/", advice[0])

    def test_red_names_an_invalid_factory_json_without_a_traceback(self):
        """Red names an invalid factory json without a traceback"""
        repo = Repo()
        write_config(repo, checks=[dict(GOOD_CHECK, timeout_s="600")])
        for args in (("red", "f", "01", "unit"), ("lint",), ("frontier", "f"), ("ticket", "f", "01"), ("mutate", "f", "01")):
            code, out = repo.gate(*args)
            self.assertNotEqual(code, 0, out)
            self.assertIn("checks[0].timeout_s", out)
            self.assertNotIn("Traceback", out)

    def test_every_command_that_reads_factory_json_refuses_an_invalid_one(self):
        """Every command that reads factory json refuses an invalid one"""
        repo = Repo()
        write_config(repo, checks=[dict(GOOD_CHECK, timeout_s="600")])
        commands = ("checks", "ready", "merge", "release", "red", "ticket", "mutate", "lint", "frontier", "boxes", "handover", "audit", "close", "features", "log", "open")
        for command in commands:
            with self.subTest(command=command):
                code, out = repo.gate(command)
                self.assertEqual(code, 1, out)
                self.assertIn("checks[0].timeout_s", out)
