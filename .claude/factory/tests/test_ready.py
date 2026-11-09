"""`gate.py ready`, `handover`, `close` and the records stamp.

Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import json
import re
import os
import subprocess
import unittest

from fixtures import GOOD_BOXES, Repo, TICKET, git


class Ready(unittest.TestCase):
    def ready_repo(self, **kwargs):
        repo = Repo(**kwargs)
        repo.ticket("01")
        repo.ticket("02", status="ready-for-human", blocked="01", boxes="- [ ] Battery lasts four hours", slug="release")
        repo.commit()
        return repo

    def test_passes_and_stamps_the_tip(self):
        """Passes and stamps the tip"""
        repo = self.ready_repo()
        code, out = repo.gate("ready", "feat")
        self.assertEqual(code, 0, out)
        self.assertIn("Left to the user (ready-for-human), not checked here: feat 02", out)
        head = subprocess.run(["git", "-C", repo.root, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        with open(os.path.join(repo.root, ".git", "factory-ready")) as handle:
            self.assertEqual(handle.readline().strip(), head)

    def test_two_features_are_gated_together(self):
        """Two features are gated together"""
        repo = self.ready_repo()
        repo.write(".scratch/fixes/issues/01-fix.md", TICKET.format(n="01", status="ready-for-agent", blocked="None", boxes=GOOD_BOXES, touches=""))
        repo.commit()
        code, out = repo.gate("ready", "feat", "fixes")
        self.assertEqual(code, 1)
        self.assertIn("fixes ticket 01 is ready-for-agent, not done", out)
        self.assertEqual(repo.gate("ready", "feat")[0], 0)

    def test_a_red_check_stops_it_and_leaves_no_stamp(self):
        """A red check stops it and leaves no stamp"""
        repo = self.ready_repo(checks=[{"name": "unit", "command": "true"}, {"name": "walks", "command": "echo boom; exit 3"}])
        code, out = repo.gate("ready", "feat")
        self.assertEqual(code, 1)
        self.assertIn("check walks: RED, exit 3", out)
        self.assertFalse(os.path.exists(os.path.join(repo.root, ".git", "factory-ready")))

    def test_no_checks_configured_is_not_green(self):
        """No checks configured is not green"""
        repo = self.ready_repo(checks=[])
        self.assertEqual(repo.gate("ready", "feat")[0], 1)

    def test_a_dirty_tree_stops_it(self):
        """A dirty tree stops it"""
        repo = self.ready_repo()
        repo.write("stray.txt", "x")
        code, out = repo.gate("ready", "feat")
        self.assertEqual(code, 1)
        self.assertIn("working tree is not clean", out)

    def test_an_unfinished_ticket_stops_it(self):
        """An unfinished ticket stops it"""
        repo = Repo()
        repo.ticket("01", status="ready-for-agent")
        repo.commit()
        code, out = repo.gate("ready", "feat")
        self.assertEqual(code, 1)
        self.assertIn("ticket 01 is ready-for-agent, not done", out)

    def test_a_done_ticket_with_an_open_box_stops_it(self):
        """A done ticket with an open box stops it"""
        repo = Repo()
        repo.ticket("01", boxes=GOOD_BOXES + "\n- [ ] Works in the browser")
        repo.commit()
        code, out = repo.gate("ready", "feat")
        self.assertEqual(code, 1)
        self.assertIn("open box", out)

    def test_a_forbidden_pattern_stops_it(self):
        """A forbidden pattern stops it"""
        rule = [{"name": "forced-click", "paths": ["walks/**/*.js"], "pattern": "force:\\s*true", "why": "a walk clicks as a user does"}]
        repo = self.ready_repo(forbid=rule)
        repo.write("walks/02.walk.js", "await btn.click({ force: true });\nawait other.click({ force: true }); // factory-allow: hidden input\n")
        repo.commit()
        code, out = repo.gate("ready", "feat")
        self.assertEqual(code, 1)
        self.assertIn("walks/02.walk.js:1 forced-click", out)
        self.assertNotIn("walks/02.walk.js:2", out)

    def test_handover_covers_the_review_fix_feature_too(self):
        """Handover covers the review fix feature too"""
        repo = self.ready_repo()
        repo.write(".scratch/fixes/issues/01-fix.md", TICKET.format(n="01", status="done", blocked="None", touches="",
                   boxes="- [x] Fixed \u2014 test: saves the record and reads it back; needs-human: judge the new wording"))
        code, out = repo.gate("handover", "feat", "fixes")
        self.assertEqual(code, 0)
        self.assertIn("## To judge (2)", out)
        self.assertIn("fixes 01, checked, judgement left", out)

    def test_the_build_log_never_dirties_the_tree(self):
        """The build log never dirties the tree"""
        repo = self.ready_repo()
        self.assertEqual(repo.gate("log", "feat", "note", "dispatched", "07", "(implementer, sonnet)")[0], 0)
        self.assertEqual(repo.gate("log", "feat", "note", "merged 07 at abc1234")[0], 0)
        code, out = repo.gate("log", "feat")
        self.assertIn("dispatched 07 (implementer, sonnet)", out)
        self.assertIn("merged 07 at abc1234", out)
        status = subprocess.run(["git", "-C", repo.root, "status", "--porcelain"], capture_output=True, text=True).stdout
        self.assertEqual(status, "")

    def test_log_refuses_words_without_a_feature(self):
        """Log refuses words without a feature"""
        repo = self.ready_repo()
        code, out = repo.gate("log", "merged", "07", "at", "abc1234")
        self.assertEqual(code, 2)
        self.assertIn("not a feature", out)
        self.assertEqual(repo.gate("log")[0], 2)
        self.assertFalse(os.path.exists(os.path.join(repo.root, ".git", "factory")))
        for spelled in ("feat/", "./feat", "../feat"):
            self.assertEqual(repo.gate("log", spelled, "hi")[0], 2, spelled)
        self.assertFalse(os.path.exists(os.path.join(repo.root, ".git", "factory")))

    def test_handover_lists_only_what_is_the_users(self):
        """Handover lists only what is the users"""
        repo = self.ready_repo()
        code, out = repo.gate("handover", "feat")
        self.assertEqual(code, 0)
        self.assertIn("## To judge (1)", out)
        self.assertIn("judge the Not saved wording", out)
        self.assertIn("Battery lasts four hours", out)
        self.assertIn("stub.js (stands in for: The real feed)", out)
        self.assertNotIn("Node (stands in", out)
        self.assertNotIn("Saves the record", out)


class Close(unittest.TestCase):
    """`gate.py close` and the records stamp, in a throwaway repo with a worktree and a log."""

    def made(self, roles=False, extra=None):
        repo = Repo(extra=extra)
        repo.write(".gitignore", ".claude/worktrees/\n")
        repo.write("docs/agents/local/ledger.md", "# Ledger\n\n## Builds\n\n| Feature | Dates | Tickets |\n|---|---|---|\n| old | then | 1 |\n\n## Recurring findings\n")
        repo.ticket("01")
        repo.ticket("02", status="ready-for-human", blocked="01", boxes="- [ ] Battery lasts four hours", slug="release")
        repo.write(".scratch/feat/reviews/01.md", "# Review: ticket 01\nTip reviewed: abc1234. Mutation sample: 4 tried, 3 caught.\n## Blocking\n1. one | fixed\n2. two | fixed\n## Notes\n1. n | left: x\n## Not checked\nNothing.\n")
        if roles:
            repo.write(".claude/agents/scorer.md", "---\nname: scorer\n---\n")
        repo.write("src/a.js", "one\n")
        repo.commit()
        git(repo.root, "worktree", "add", "-q", ".claude/worktrees/01-thing", "-b", "ticket/01-thing")
        for words in (("dispatch", "01", "implementer", "--agent", "a1"), ("report", "01", "implementer"), ("dispatch", "01", "ticket-reviewer", "--agent", "a2"),
                      ("dispatch", "02", "implementer", "--agent", "a3"), ("review-wave", "1")):
            repo.gate("log", "feat", *words)
        return repo

    def stamped(self, **kwargs):
        repo = self.made(**kwargs)
        code, out = repo.gate("ready", "feat")
        self.assertEqual(code, 0, out)
        return repo

    def jsonl(self, repo):
        with open(os.path.join(repo.root, "docs/agents/local/builds.jsonl"), encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def test_close_refuses_an_unstamped_tip(self):
        """Close refuses an unstamped tip"""
        repo = self.made()
        code, out = repo.gate("close", "feat")
        self.assertEqual(code, 1)
        self.assertIn("not stamped", out)
        self.assertFalse(os.path.exists(os.path.join(repo.root, "docs/agents/local/builds.jsonl")))
        repo = self.stamped()
        repo.write("src/a.js", "two\n")
        repo.commit()
        code, out = repo.gate("close", "feat")
        self.assertEqual(code, 1)
        self.assertIn("not stamped", out)

    def test_close_fills_the_build_row_from_the_log(self):
        """Close fills the build row from the log"""
        repo = self.stamped()
        code, out = repo.gate("close", "feat")
        self.assertEqual(code, 0, out)
        rows = self.jsonl(repo)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual((row["feature"], row["tip"], row["tickets"], row["reviews"], row["blocking"]), ("feat", repo.head(), 2, 1, 2))
        self.assertEqual((row["mutants_tried"], row["mutants_survived"]), (4, 1))
        self.assertEqual(row["subagents"], {"implementer": 2, "ticket-reviewer": 1})
        self.assertEqual((row["boxes_proved"], row["boxes_human"]), (2, 1))
        self.assertEqual(row["guard_refusals"], 0)
        with open(os.path.join(repo.root, "docs/agents/local/ledger.md"), encoding="utf-8") as handle:
            ledger = handle.read()
        self.assertRegex(ledger, r"\| old \| then \| 1 \|\n\| feat \|[^\n]*\n\n## Recurring findings")
        self.assertIn("1 reviews", ledger)

    def test_close_prints_the_facts_block(self):
        """Close prints the facts block"""
        repo = self.stamped()
        code, out = repo.gate("close", "feat")
        self.assertEqual(code, 0, out)
        self.assertIn("## Facts", out)
        self.assertIn("Built tip: %s" % repo.head(), out)
        self.assertIn("Subagents: implementer 2, ticket-reviewer 1", out)
        self.assertIn("Tickets: 1 done of 2 (1 for the user)", out)
        self.assertIn("Guard refusals: 0", out)
        removes = [l for l in out.split("\n") if l.startswith("git worktree remove")]
        self.assertEqual(len(removes), 1, out)
        self.assertIn(".claude/worktrees/01-thing", removes[0])
        self.assertIn("AUDIT: clean", out)
        self.assertIn("- Audit: passed", out)

    def test_close_waits_for_the_scorer_when_one_exists(self):
        """Close waits for the scorer when its role exists"""
        repo = self.stamped(roles=True)
        code, out = repo.gate("close", "feat")
        self.assertEqual(code, 0, out)
        self.assertIn("dispatch: scorer", out)
        self.assertFalse(os.path.exists(os.path.join(repo.root, "docs/agents/local/builds.jsonl")))
        code, out = repo.gate("close", "feat", "--collect")
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.jsonl(repo)), 1)

    def test_close_refuses_when_the_audit_does(self):
        """Close refuses when the audit refuses"""
        repo = self.stamped()
        code, out = self.in_process(repo, ["close", "feat"], audit=lambda root, config, names, report=None: 1)
        self.assertEqual(code, 1)
        self.assertFalse(os.path.exists(os.path.join(repo.root, "docs/agents/local/builds.jsonl")))

    def test_close_refusal_goes_to_the_captured_output(self):
        """Close's refusal goes to the captured output"""
        repo = self.stamped()
        code, out = self.in_process(repo, ["close", "feat"], audit=lambda root, config, names, report=None: 1)
        self.assertEqual(code, 1)
        self.assertIn("refused by close-audit", out)

    def transcripts(self, model="model-one"):
        """A projects root holding session s1 with agent a1's transcript (10+20+30+40 tokens), set as $GATE_PROJECTS_DIR."""
        import shutil
        import tempfile
        projects = tempfile.mkdtemp(prefix="gate-projects-")
        self.addCleanup(shutil.rmtree, projects, True)
        folder = os.path.join(projects, "-proj", "s1", "subagents")
        os.makedirs(folder)
        usage = {"input_tokens": 10, "output_tokens": 20, "cache_read_input_tokens": 30, "cache_creation_input_tokens": 40}
        with open(os.path.join(folder, "agent-a1.jsonl"), "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"timestamp": "2026-11-08T10:00:00.000Z", "message": {"id": "m1", "model": model, "usage": usage}}) + "\n")
        return projects

    def close_with(self, repo, projects=None, patches=(), env=None):
        """`close feat` in this process with $GATE_PROJECTS_DIR (an empty folder by default) and the named gate.ready attributes replaced."""
        import contextlib
        from unittest import mock
        from gate import ready
        import tempfile
        projects = projects or tempfile.mkdtemp(prefix="gate-projects-")
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.dict(os.environ, dict({"GATE_PROJECTS_DIR": projects}, **(env or {}))))
            for name, value in patches:
                stack.enter_context(mock.patch.object(ready, name, value))
            return self.in_process(repo, ["close", "feat"])

    def test_close_writes_the_tokens_record_beside_the_builds_line(self):
        """Close writes the tokens record beside the builds line"""
        repo = self.stamped()
        code, out = self.close_with(repo, self.transcripts())
        self.assertEqual(code, 0, out)
        with open(os.path.join(repo.root, "docs/agents/local/tokens.jsonl"), encoding="utf-8") as handle:
            lines = [json.loads(l) for l in handle if l.strip()]
        self.assertEqual([(l["feature"], l["agent"], l["output"]) for l in lines], [("feat", "a1", 20)])
        self.assertEqual([r["feature"] for r in self.jsonl(repo)], ["feat"])
        self.assertEqual(self.jsonl(repo)[0]["tip"], repo.head())

    def test_close_writes_lines_the_record_shapes_name_and_accept(self):
        """The lines close writes to builds.jsonl and tokens.jsonl are well typed and every field is named by their shape"""
        from gate.records import unclassified, well_typed
        repo = self.stamped()
        self.assertEqual(self.close_with(repo, self.transcripts())[0], 0)
        with open(os.path.join(repo.root, "docs/agents/local/tokens.jsonl"), encoding="utf-8") as handle:
            tokens = [json.loads(l) for l in handle if l.strip()]
        for name, lines in (("builds", self.jsonl(repo)), ("tokens", tokens)):
            self.assertTrue(lines, name)
            for line in lines:
                self.assertEqual(unclassified(name, line), [], name)
                self.assertTrue(well_typed(name, line), name)

    def test_close_facts_carry_tokens_and_cost(self):
        """Close's facts carry the tokens and the cost with the unpriced models"""
        prices = {"model-one": {"input": 1000000, "output": 0, "cache_read": 0, "cache_write": 0}}
        repo = self.stamped(extra={"prices": prices})
        code, out = self.close_with(repo, self.transcripts())
        self.assertIn("- Tokens: 100\n", out)
        self.assertIn("- Cost: $10.00 (0 model(s) unpriced)", out)
        repo = self.stamped(extra={"prices": {"other": prices["model-one"]}})
        code, out = self.close_with(repo, self.transcripts())
        self.assertIn("- Cost: $0.00 (1 model(s) unpriced)", out)
        repo = self.stamped()
        code, out = self.close_with(repo, self.transcripts())
        self.assertIn("- Tokens: 100\n", out)
        self.assertNotIn("- Cost:", out)

    def test_close_with_no_transcripts_says_tokens_not_read_and_prints_no_cost(self):
        """No transcripts found: Tokens: not read (the tokens line's reason) and no Cost line"""
        repo = self.stamped(extra={"prices": {"model-one": {"input": 3}}})
        code, out = self.close_with(repo)
        tokens_line = [l for l in out.split("\n") if l.startswith("tokens: ")][0]
        reason = tokens_line[len("tokens: "):]
        self.assertIn("- Tokens: not read (%s)\n" % reason, out)
        self.assertNotIn("- Cost:", out)
        self.assertNotIn("- Tokens: 0", out)

    def test_close_facts_count_a_model_missing_a_kind_it_used_as_unpriced(self):
        """A price without the cache kinds leaves the cache-read record unpriced in the Facts"""
        repo = self.stamped(extra={"prices": {"model-one": {"input": 3, "output": 15}}})
        code, out = self.close_with(repo, self.transcripts())
        self.assertIn("(1 model(s) unpriced)", out)
        full = {"input": 3, "output": 15, "cache_read": 0.3, "cache_write": 3.75}
        repo = self.stamped(extra={"prices": {"model-one": full}})
        code, out = self.close_with(repo, self.transcripts())
        self.assertIn("(0 model(s) unpriced)", out)

    def test_close_writes_the_page_and_the_handover_names_it(self):
        """Close writes the page and the hand-over names its path"""
        repo = self.stamped()
        code, out = self.close_with(repo)
        self.assertEqual(code, 0, out)
        line = [l for l in out.split("\n") if l.startswith("dashboard: ")]
        self.assertEqual(len(line), 1, out)
        path = line[0][len("dashboard: "):]
        self.assertTrue(os.path.isfile(path), path)
        self.assertLess(out.index("dashboard: "), out.index("git worktree remove"))
        code, text = repo.gate("handover", "feat")
        self.assertIn("Dashboard: %s" % path, text)

    def test_close_of_a_build_and_its_fix_round_gives_the_page_the_facts_figures(self):
        """The page after a close of two features has the Facts' build cost and tokens"""
        prices = {"model-one": {"input": 1000000, "output": 1000000, "cache_read": 1000000, "cache_write": 1000000}}
        repo = self.made(extra={"prices": prices})
        repo.write(".scratch/feat-review/spec.md", "# Fix\n")
        with open(os.path.join(repo.root, ".scratch/feat/issues/01-thing.md"), encoding="utf-8") as handle:
            repo.write(".scratch/feat-review/issues/01-fix.md", handle.read())
        repo.commit()
        repo.gate("log", "feat-review", "dispatch", "01", "implementer", "--agent", "a9")
        code, out = repo.gate("ready", "feat", "feat-review")
        self.assertEqual(code, 0, out)
        projects = self.transcripts()
        usage = {"input_tokens": 1, "output_tokens": 2, "cache_read_input_tokens": 3, "cache_creation_input_tokens": 4}
        with open(os.path.join(projects, "-proj", "s1", "subagents", "agent-a9.jsonl"), "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"timestamp": "2026-11-08T10:00:00.000Z", "message": {"id": "m9", "model": "model-one", "usage": usage}}) + "\n")
        from unittest import mock
        with mock.patch.dict(os.environ, {"GATE_PROJECTS_DIR": projects}):
            code, out = self.in_process(repo, ["close", "feat", "feat-review"])
        self.assertEqual(code, 0, out)
        tokens = re.search(r"- Tokens: (\d+)", out).group(1)
        cost = re.search(r"- Cost: (\$[\d.]+)", out).group(1)
        path = [l for l in out.split("\n") if l.startswith("dashboard: ")][0][len("dashboard: "):]
        with open(path, encoding="utf-8") as handle:
            page = handle.read()
        self.assertEqual(tokens, "110")
        self.assertIn('<div class="kpi-value">%s</div>' % cost, page)
        self.assertIn("<td>110</td>", page)

    def test_close_facts_total_the_tokens_file_and_name_a_feature_kept_from_an_earlier_read(self):
        """Close of a feature with transcripts and one with only old tokens lines totals both, as the page does, and names the older one"""
        prices = {"model-one": {"input": 1000000, "output": 1000000, "cache_read": 1000000, "cache_write": 1000000}}
        repo = self.made(extra={"prices": prices})
        repo.write(".scratch/feat-review/spec.md", "# Fix\n")
        with open(os.path.join(repo.root, ".scratch/feat/issues/01-thing.md"), encoding="utf-8") as handle:
            repo.write(".scratch/feat-review/issues/01-fix.md", handle.read())
        old = {"date": "2026-11-07", "feature": "feat-review", "ticket": "01", "role": "implementer", "agent": "a9", "model": "model-one",
               "input": 1, "output": 2, "cache_read": 3, "cache_write": 4}
        repo.write("docs/agents/local/tokens.jsonl", json.dumps(old) + "\n" + json.dumps(dict(old, feature="other", input=5000)) + "\n")
        repo.commit()
        code, out = repo.gate("ready", "feat", "feat-review")
        self.assertEqual(code, 0, out)
        from unittest import mock
        with mock.patch.dict(os.environ, {"GATE_PROJECTS_DIR": self.transcripts()}):
            code, out = self.in_process(repo, ["close", "feat", "feat-review"])
        self.assertEqual(code, 0, out)
        self.assertIn("- Tokens: 110\n", out)
        cost = re.search(r"- Cost: (\$[\d.]+)", out).group(1)
        self.assertEqual(cost, "$%.2f" % (110 / 1e6 * 1e6))
        self.assertIn("- Older figures: feat-review (lines kept from an earlier read)", out)
        path = [l for l in out.split("\n") if l.startswith("dashboard: ")][0][len("dashboard: "):]
        with open(path, encoding="utf-8") as handle:
            page = handle.read()
        self.assertIn('<div class="kpi-value">%s</div>' % cost, page)
        self.assertIn("<td>110</td>", page)

    def test_close_counts_a_flake_recorded_and_committed_before_the_close(self):
        """A committed flake is counted by the Facts, the hand-over and the page"""
        repo = self.made()
        repo.write("docs/agents/local/flakes.jsonl", json.dumps({"date": "d", "feature": "feat", "file": "w.js", "title": "walk A", "tip": "old0000"}) + "\n")
        repo.commit()
        self.assertEqual(repo.gate("ready", "feat")[0], 0)
        code, out = self.close_with(repo)
        self.assertEqual(code, 0, out)
        self.assertIn("- Flakes: 1", out)
        path = [l for l in out.split("\n") if l.startswith("dashboard: ")][0][len("dashboard: "):]
        with open(path, encoding="utf-8") as handle:
            self.assertIn('<div class="kpi-label">Flakes</div><div class="kpi-value">1</div>', handle.read())
        self.assertIn("## Flakes this build (1)", repo.gate("handover", "feat")[1])

    def test_a_flake_of_a_two_feature_ready_counts_once_for_the_close(self):
        """A flake recorded by ready x x-review counts once"""
        from gate.dashboard import count_flakes, feature_names
        rows = [{"feature": "feat, feat-review", "title": "t"}, {"feature": "other", "title": "u"}, {"feature": "feat", "title": "v"}]
        self.assertEqual(count_flakes(rows, ["feat", "feat-review"]), 2)
        self.assertEqual(feature_names("a, b"), ["a", "b"])

    def test_close_facts_count_a_two_feature_flake_once(self):
        """Close of two features prints Flakes: 1 for one flake"""
        repo = self.made()
        repo.write(".scratch/feat-review/spec.md", "# Fix\n")
        with open(os.path.join(repo.root, ".scratch/feat/issues/01-thing.md"), encoding="utf-8") as handle:
            repo.write(".scratch/feat-review/issues/01-fix.md", handle.read())
        repo.write("docs/agents/local/flakes.jsonl", json.dumps({"date": "d", "feature": "feat, feat-review", "file": "w.js", "title": "walk A", "tip": "old0000"}) + "\n"
                   + json.dumps({"date": "d", "feature": "feat-review", "file": "w.js", "title": "walk B", "tip": "old0000"}) + "\n")
        repo.commit()
        code, out = repo.gate("ready", "feat", "feat-review")
        self.assertEqual(code, 0, out)
        code, out = repo.gate("close", "feat", "feat-review")
        self.assertIn("- Flakes: 2", out)

    def test_a_raising_tokens_writer_is_said_and_close_still_writes_its_other_records(self):
        """A tokens writer that raises is said on a tokens: failed line and close still writes builds.jsonl"""
        def boom(*args, **kwargs):
            raise RuntimeError("boom")
        repo = self.stamped()
        code, out = self.close_with(repo, patches=(("write_tokens", boom),))
        self.assertEqual(code, 0, out)
        self.assertIn("tokens: failed (boom)", out)
        self.assertEqual([r["feature"] for r in self.jsonl(repo)], ["feat"])
        self.assertIn("## Facts", out)

    def test_close_exits_as_before_when_dashboard_or_github_fail(self):
        """Close exits as before when the dashboard or github fail"""
        def boom(*args, **kwargs):
            raise RuntimeError("boom")
        for patches, word in (((("cmd_dashboard", boom),), "dashboard"), ((("cmd_github", lambda *a: 1), ("has_github_remote", lambda root: True)), "github"),
                              ((("cmd_github", boom), ("has_github_remote", lambda root: True)), "github")):
            repo = self.stamped()
            code, out = self.close_with(repo, patches=patches)
            self.assertEqual(code, 0, out)
            failed = [l for l in out.split("\n") if l.startswith(word + ": ") and "failed" in l]
            self.assertEqual(len(failed), 1, out)
            self.assertIn("## Facts", out)
            self.assertIn("git worktree remove", out)

    def stub_gh(self):
        import stat
        import tempfile
        folder = tempfile.mkdtemp(prefix="gate-gh-")
        self.addCleanup(__import__("shutil").rmtree, folder, True)
        log = os.path.join(folder, "calls.txt")
        with open(os.path.join(folder, "gh"), "w", encoding="utf-8") as handle:
            handle.write("#!/bin/sh\necho \"$@\" >> '%s'\necho '{}'\n" % log)
        os.chmod(os.path.join(folder, "gh"), stat.S_IRWXU)
        return folder, log

    def test_close_runs_github_only_with_a_github_remote(self):
        """Close runs github with a GitHub remote and not without one"""
        folder, log = self.stub_gh()
        env = {"PATH": folder + os.pathsep + os.environ["PATH"]}
        repo = self.stamped()
        code, out = self.close_with(repo, env=env)
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(log), out)
        self.assertNotIn("github:", out)
        repo = self.stamped()
        git(repo.root, "remote", "add", "origin", "git@github.com:owner/repo.git")
        code, out = self.close_with(repo, env=env)
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.exists(log), out)
        with open(log, encoding="utf-8") as handle:
            self.assertIn("auth status", handle.read())

    def test_a_records_commit_may_hold_the_github_storage_file(self):
        """A records commit may hold the github storage file"""
        from gate.audit import record_paths_ok
        self.assertTrue(record_paths_ok("docs/agents/local/github-storage.json", ".scratch"))
        self.assertFalse(record_paths_ok("docs/agents/local/factory.json", ".scratch"))

    def closed(self):
        repo = self.stamped()
        built = repo.head()
        self.assertEqual(repo.gate("close", "feat")[0], 0)
        repo.write(".scratch/feat/report.md", "# Report\n\n## Facts\n\nBuilt tip: %s\n" % built)
        return repo, built

    def test_ready_records_stamp_accepts_a_records_only_close_commit(self):
        """Ready records stamp accepts a records-only close commit"""
        repo, built = self.closed()
        repo.commit()
        y = repo.head()
        code, out = repo.gate("ready", "feat", "--records", y)
        self.assertEqual(code, 0, out)
        self.assertIn("built tip %s" % built[:7], out)
        with open(os.path.join(repo.root, ".git", "factory-ready"), encoding="utf-8") as handle:
            lines = handle.read().split("\n")
        self.assertEqual((lines[0], lines[3]), (y, "built " + built))

    def test_ready_records_stamp_refuses_a_code_change_after_the_built_tip(self):
        """Ready records stamp refuses a code change after the built tip"""
        repo, built = self.closed()
        repo.write("src/a.js", "changed after the stamp\n")
        repo.commit()
        code, out = repo.gate("ready", "feat", "--records", repo.head())
        self.assertEqual(code, 1)
        self.assertIn("src/a.js", out)
        with open(os.path.join(repo.root, ".git", "factory-ready"), encoding="utf-8") as handle:
            self.assertEqual(handle.readline().strip(), built)

    def test_ready_records_stamp_refuses_a_report_naming_another_tip(self):
        """Ready records stamp refuses a report naming another tip"""
        repo, built = self.closed()
        repo.write(".scratch/feat/report.md", "# Report\n\nBuilt tip: %s\n" % ("1234567" + "0" * 33))
        repo.commit()
        code, out = repo.gate("ready", "feat", "--records", repo.head())
        self.assertEqual(code, 1)
        self.assertIn("names built tip 1234567", out)
        repo.write(".scratch/feat/report.md", "# Report\n\nNo facts.\n")
        repo.commit()
        code, out = repo.gate("ready", "feat", "--records", repo.head())
        self.assertEqual(code, 1)
        self.assertIn("does not name a built tip", out)

    def test_ready_records_stamp_refuses_a_second_commit(self):
        """Ready records stamp refuses a close that is not one commit"""
        repo, built = self.closed()
        repo.commit()
        repo.write(".scratch/feat/extra.md", "x\n")
        repo.commit()
        code, out = repo.gate("ready", "feat", "--records", repo.head())
        self.assertEqual(code, 1)
        self.assertIn("not the built tip", out)

    def in_process(self, repo, args, audit=None):
        """Runs the gate's `main` in this process, in the repo, with its output captured; (code, output).
        `audit` replaces the audit command; None removes it, so the gate runs as if it were not built."""
        import contextlib
        import io
        from unittest import mock
        from gate import audit as audit_module
        from gate.cli import main
        cwd = os.getcwd()
        os.chdir(repo.root)
        saved = {k: v for k, v in os.environ.items() if k.startswith("GIT_")}
        for key in saved:
            del os.environ[key]
        out = io.StringIO()
        try:
            with mock.patch.dict(audit_module.__dict__):
                if audit is None:
                    del audit_module.cmd_audit
                else:
                    audit_module.cmd_audit = audit
                with contextlib.redirect_stdout(out):
                    code = main(["gate.py"] + list(args))
        finally:
            os.chdir(cwd)
            os.environ.update(saved)
        return code, out.getvalue()

    def test_close_says_the_audit_was_skipped(self):
        """Close says the audit was skipped"""
        repo, built = self.closed()
        repo.commit()
        code, out = self.in_process(repo, ["ready", "feat", "--records", repo.head()])
        self.assertEqual(code, 0, out)
        self.assertIn("audit skipped", out)
        repo2 = self.stamped()
        self.assertIn("- Audit: skipped", self.in_process(repo2, ["close", "feat"])[1])

    def test_close_refuses_on_audit_violation(self):
        """Close refuses on audit violation"""
        repo = self.stamped()
        repo.gate("log", "feat", "dispatch", "01", "implementer", "--agent", "a9")
        code, out = repo.gate("close", "feat")
        self.assertEqual(code, 1, out)
        self.assertIn("has 2 dispatch lines for its implementer", out)
        self.assertIn("refused by close-audit", out)
        self.assertFalse(os.path.exists(os.path.join(repo.root, "docs/agents/local/builds.jsonl")))

    def test_ready_records_stamp_refuses_a_failing_report_audit(self):
        """Ready records stamp refuses a failing report audit"""
        repo, built = self.closed()
        repo.write(".scratch/feat/report.md", "# Report\n\n- Built tip: %s\n\n| Measure | Value |\n|---|---|\n| Tickets | 9 |\n" % built[:7])
        repo.commit()
        code, out = repo.gate("ready", "feat", "--records", repo.head())
        self.assertEqual(code, 1, out)
        self.assertIn("`Tickets` says 9, the gate computes 2", out)
        self.assertIn("the audit of the report refused it", out)
        with open(os.path.join(repo.root, ".git", "factory-ready"), encoding="utf-8") as handle:
            self.assertEqual(handle.readline().strip(), built)

    def test_close_refuses_a_second_close_after_the_records_stamp(self):
        """Close refuses a second close after the records stamp"""
        repo, built = self.closed()
        repo.commit()
        self.assertEqual(repo.gate("ready", "feat", "--records", repo.head())[0], 0)
        code, out = repo.gate("close", "feat")
        self.assertEqual(code, 1)
        self.assertIn("already closed", out)
        self.assertEqual(len(self.jsonl(repo)), 1)

    def test_ready_records_stamp_refuses_a_code_file_moved_into_the_records(self):
        """Ready records stamp refuses a code file moved into the records"""
        repo, built = self.closed()
        git(repo.root, "mv", "src/a.js", ".scratch/feat/a.js")
        repo.commit()
        code, out = repo.gate("ready", "feat", "--records", repo.head())
        self.assertEqual(code, 1)
        self.assertIn("src/a.js", out)


class Handover(unittest.TestCase):
    """`gate.py handover` reads everything the user must hear about."""

    LEDGER = ("# Ledger\n\n## Escapes\n\n| Date | Feature | Defect | Found by | Should | Change made |\n|---|---|---|---|---|---|\n"
              "| 2026-11-06 | feat | UNRESOLVED app defect: the map view is not restored. Walk (02k2 back to list) shows it | user | review | Not fixed |\n"
              "| 2026-11-06 | feat | A red todo walk exits 0 | review | gate | Fixed in ticket 03: the UNRESOLVED row is read |\n"
              "| 2026-11-07 | feat | A flake in the 02k walk | review | gate | UNRESOLVED. The app defect behind it is open |\n")
    WALKS = ("walk('02k2 back to list', async () => {\n}, { todo: 'UNRESOLVED defect' });\n"
             "walk('03 loose walk', async () => {\n}, { todo: 'no row' });\n")

    def repo(self):
        repo = Repo()
        repo.ticket("01")
        repo.write("docs/agents/local/ledger.md", self.LEDGER)
        repo.write("walks/02.walk.js", self.WALKS)
        repo.commit()
        return repo

    def test_handover_lists_an_unresolved_row(self):
        """Handover lists an UNRESOLVED row"""
        out = self.repo().gate("handover", "feat")[1]
        self.assertIn("## Open defects (3)", out)
        section = out.split("## Open defects (3)")[1].split("## Todo walks")[0]
        self.assertIn("2026-11-06", section)
        self.assertIn("02k2 back to list", section)
        self.assertIn("A flake in the 02k walk", section)
        self.assertIn("names ticket 03", section)

    def test_handover_lists_a_todo_walk_with_its_tie(self):
        """Handover lists a todo walk with its tie"""
        out = self.repo().gate("handover", "feat")[1]
        section = out.split("## Todo walks (2)")[1].split("\n## ")[0]
        self.assertIn("02k2 back to list", section)
        self.assertIn("tied to the ledger row of 2026-11-06", section)
        self.assertIn("03 loose walk", section)
        self.assertIn("UNTIED", section)

    def test_handover_lists_the_open_list_from_both_specs(self):
        """Handover lists the open list from both specs"""
        repo = self.repo()
        repo.write(".scratch/feat/spec.md", "# Feat\n\n## Open list\n\n1. **First item.** More words.\n2. **Second.**\n\n## Other\n3. not one\n")
        repo.write(".scratch/fixes/spec.md", "# Fixes\n\n## Open list\n\n1. **Fix item.**\n")
        repo.write(".scratch/fixes/issues/01-x.md", TICKET.format(n="01", status="done", blocked="None", touches="", boxes="- [ ] a \u2014 needs-human: look"))
        repo.commit()
        out = repo.gate("handover", "feat", "fixes")[1]
        self.assertIn("## Open list (3)", out)
        self.assertIn(".scratch/feat/spec.md (2)", out)
        self.assertIn(".scratch/fixes/spec.md (1)", out)
        self.assertIn("**First item.** More words.", out)
        self.assertIn("**Fix item.**", out)
        self.assertNotIn("not one", out)

    def test_handover_lists_unadopted_proposed_rules(self):
        """Handover lists unadopted proposed rules"""
        repo = self.repo()
        repo.write("docs/agents/local/rules.md", "# Rules\n\n| id | rule | kind | escape ids | proposed | adopted (commit) | review by | retired |\n|---|---|---|---|---|---|---|---|\n"
                   "| R1 | Lint the walks | mechanical | E4 | 2026-11-07 |  | 3 |  |\n| R2 | Old one | prose | E1 | 2026-11-06 | abc1234 | 3 |  |\n")
        repo.commit()
        out = repo.gate("handover", "feat")[1]
        self.assertIn("## Proposed rules (1)", out)
        self.assertIn("R1: Lint the walks (escape E4)", out)
        self.assertNotIn("Old one", out)

    def test_handover_says_an_absent_rule_queue_is_zero_rows(self):
        """Handover says an absent rule queue is zero rows"""
        out = self.repo().gate("handover", "feat")[1]
        self.assertIn("## Proposed rules (0)", out)
        self.assertIn("no rule queue file", out)

    def test_a_flakes_line_of_the_wrong_type_does_not_crash_handover(self):
        """Handover and the flake count read flakes.jsonl through the shared reader and skip a list title and an array line"""
        repo = self.repo()
        rows = [{"date": "d", "feature": "feat", "file": "w.js", "title": "walk A", "tip": "t"}, {"date": "d", "feature": "feat", "file": "w.js", "title": ["walk A"], "tip": "t"}]
        repo.write("docs/agents/local/flakes.jsonl", "".join(json.dumps(r) + "\n" for r in rows) + "[1]\n")
        repo.commit()
        code, out = repo.gate("handover", "feat")
        self.assertEqual(code, 0, out)
        self.assertIn("walk A: 1", out)

    def test_handover_lists_flakes(self):
        """Handover lists flakes"""
        repo = self.repo()
        rows = [{"date": "d", "feature": "feat", "file": "w.js", "title": "walk A", "tip": "t"}] * 3
        rows.append({"date": "d", "feature": "other", "file": "w.js", "title": "walk B", "tip": "t"})
        repo.write("docs/agents/local/flakes.jsonl", "".join(json.dumps(r) + "\n" for r in rows))
        repo.commit()
        out = repo.gate("handover", "feat")[1]
        section = out.split("## Flakes this build (1)")[1].split("\n## ")[0]
        self.assertIn("walk A: 3", section)
        self.assertIn("no ledger row names a ticket", section)
        self.assertNotIn("walk B", section)

    def test_a_comma_list_of_brief_items_is_cited(self):
        """A comma list of brief items is cited"""
        from gate.ready import brief_numbers
        self.assertEqual(brief_numbers("Source: brief findings 4, 14 and 25; x"), {4, 14, 25})
        self.assertEqual(brief_numbers("brief findings 4, 14, and 25"), {4, 14, 25})
        self.assertEqual(brief_numbers("brief findings 3, 4"), {3, 4})

    BRIEF = "# Brief\n\n1. **First claim.** text\n2. **Second claim.** text\n3. **Third claim.** text\n"

    def briefed(self, cited_by_open_list=True):
        repo = self.repo()
        repo.write(".scratch/feat/brief.md", self.BRIEF)
        open_list = "## Open list\n\n1. **Declined.** Not doing brief 3.\n" if cited_by_open_list else ""
        repo.write(".scratch/feat/spec.md", "# Feat\n\n**Brief:** `brief.md` in this folder.\n\n" + open_list)
        path = ".scratch/feat/issues/01-thing.md"
        with open(os.path.join(repo.root, path), encoding="utf-8") as handle:
            text = handle.read()
        text = text.replace("**What to build:** something.", "**What to build:** x. Source: brief findings 1 (a claim; 9 words) and 2.")
        repo.write(path, text)
        repo.commit()
        return repo

    def test_handover_lists_the_briefs_claims_with_their_tickets(self):
        """Handover lists the briefs claims with their tickets"""
        out = self.briefed().gate("handover", "feat")[1]
        section = out.split("## The brief's claims (3)")[1].split("\n## ")[0]
        self.assertIn("1. First claim.: ticket 01", section)
        self.assertIn("2. Second claim.: ticket 01", section)
        self.assertIn("3. Third claim.: Open list item 1", section)
        self.assertNotIn("uncited", section)
        self.assertNotIn("9.", section)

    def test_handover_marks_an_uncited_brief_item(self):
        """Handover marks an uncited brief item"""
        out = self.briefed(cited_by_open_list=False).gate("handover", "feat")[1]
        self.assertIn("3. Third claim.: uncited", out)

    def test_handover_lists_merged_design_decisions_first(self):
        """Handover lists merged design decisions first"""
        repo = self.repo()
        repo.write(".scratch/fixes-review/spec.md", "# Fixes\n\n## Open list\n\n1. **Tab order changed.** ticket 01 moves focus.\n")
        text = TICKET.format(n="01", status="done", blocked="None", touches="", boxes="- [ ] a \u2014 needs-human: look")
        repo.write(".scratch/fixes-review/issues/01-x.md", text.replace("**Status:** done", "**Status:** done\n**Kind:** design"))
        repo.commit()
        out = repo.gate("handover", "feat", "fixes-review")[1]
        self.assertIn("## Merged design decisions (1)", out)
        self.assertLess(out.index("## Merged design decisions"), out.index("## To judge"))
        self.assertIn("**Tab order changed.**", out.split("## Merged design decisions (1)")[1].split("\n## ")[0])

    def test_handover_names_the_built_and_stamped_tips(self):
        """Handover names the built and stamped tips"""
        repo = self.repo()
        stamp = subprocess.run(["git", "-C", repo.root, "rev-parse", "--git-path", "factory-ready"], capture_output=True, text=True).stdout.strip()
        with open(os.path.join(repo.root, stamp), "w", encoding="utf-8") as handle:
            handle.write("%s\nfeat\n2026-11-07T10:00:00\nbuilt 1234567890abcdef\n" % repo.head())
        out = repo.gate("handover", "feat")[1]
        self.assertIn("built 1234567", out)
        self.assertIn("stamped %s" % repo.head()[:7], out)

    def test_handover_says_when_the_stamp_names_another_feature(self):
        """Handover says when the stamp names another feature"""
        repo = self.repo()
        stamp = subprocess.run(["git", "-C", repo.root, "rev-parse", "--git-path", "factory-ready"], capture_output=True, text=True).stdout.strip()
        with open(os.path.join(repo.root, stamp), "w", encoding="utf-8") as handle:
            handle.write("%s\nother\n2026-11-07T10:00:00\nbuilt 1234567890abcdef\n" % repo.head())
        out = repo.gate("handover", "feat")[1]
        self.assertIn("the stamp names other, not feat", out)
