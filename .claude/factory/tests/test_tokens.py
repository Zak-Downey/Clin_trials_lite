"""The stats --write command and the tokens record it writes.

Data: a fixture session transcript with a `subagents/` folder under a temporary `$GATE_PROJECTS_DIR`. Lacks: a real
harness transcript (the shape is the one `gate.ledger.read_usage` states); a log whose times are in another zone than
the machine's; a transcript of hundreds of megabytes.

Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

from fixtures import CLEAN_ENV, GATE, Repo

TOKENS = "docs/agents/local/tokens.jsonl"
M1, M2 = "model-one", "model-two"


def utc(local_text):
    """A transcript timestamp for a log time written in the machine's local zone."""
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(time.mktime(time.strptime(local_text, "%Y-%m-%dT%H:%M:%S"))))


def line(mid, model, at, i=1, o=2, cr=3, cw=4):
    usage = {"input_tokens": i, "output_tokens": o, "cache_read_input_tokens": cr, "cache_creation_input_tokens": cw}
    return json.dumps({"timestamp": at, "message": {"id": mid, "model": model, "usage": usage}})


def write_lines(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


class Tokens(unittest.TestCase):
    def build(self, log_agents=("a1", "a2", "gone"), roles=None):
        """A repo with feature `feat`, a log from 10:00 to 11:00 and a projects root holding session `s1`."""
        repo = Repo()
        projects = tempfile.mkdtemp(prefix="gate-projects-")
        atexit.register(shutil.rmtree, projects, True)
        log = ["2026-11-08T10:00:00 note start"]
        for n, agent in enumerate(log_agents, 1):
            log.append("2026-11-08T10:%02d:00 dispatch %02d %s --agent %s" % (n, n, (roles or {}).get(agent, "implementer"), agent))
        log.append("2026-11-08T11:00:00 note end")
        write_lines(os.path.join(repo.root, ".git", "factory", "build-log-feat.md"), log)
        session = os.path.join(projects, "-proj", "s1")
        write_lines(os.path.join(session, "subagents", "agent-a1.jsonl"), [
            line("m1", M1, utc("2026-11-08T10:05:00"), 10, 20, 30, 40),
            line("m1", M1, utc("2026-11-08T10:05:00"), 10, 20, 30, 40),  # the same message again: counted once
            "not json",
            line("m2", M2, utc("2026-11-08T10:06:00"), 100, 200, 300, 400)])
        write_lines(os.path.join(session, "subagents", "agent-a2.jsonl"), [line("m3", M1, utc("2026-11-08T10:07:00"), 1, 2, 3, 4)])
        write_lines(session + ".jsonl", [
            line("o0", M1, utc("2026-11-08T09:59:59"), 1000, 1000, 1000, 1000),   # before the window
            line("o1", M1, utc("2026-11-08T10:00:00"), 1, 10, 100, 1000),         # on the first line's second
            line("o2", M2, utc("2026-11-08T10:30:00"), 2, 20, 200, 2000),
            line("o2", M2, utc("2026-11-08T10:30:00"), 2, 20, 200, 2000),         # duplicate
            line("o3", M1, utc("2026-11-08T11:00:00"), 3, 30, 300, 3000),         # on the last line's second
            line("o4", M1, utc("2026-11-08T11:00:01"), 5000, 5000, 5000, 5000)])  # after the window
        repo.commit()
        return repo, projects

    def gate_in(self, repo, projects, *args):
        result = subprocess.run([sys.executable, GATE] + list(args), cwd=repo.root, capture_output=True, text=True,
                                env=dict(CLEAN_ENV, GATE_PROJECTS_DIR=projects, **({"TZ": os.environ["TZ"]} if "TZ" in os.environ else {})))
        return result.returncode, result.stdout + result.stderr

    def text(self, repo):
        with open(os.path.join(repo.root, TOKENS), encoding="utf-8") as handle:
            return handle.read()

    def records(self, repo):
        with open(os.path.join(repo.root, TOKENS), encoding="utf-8") as handle:
            return [json.loads(l) for l in handle.read().split("\n") if l]

    def test_stats_write_with_wrong_arguments_prints_the_usage_line_and_exits_2(self):
        """Stats --write with wrong arguments prints the usage line and exits 2"""
        repo = Repo()
        for args, said in ((("stats", "--write"), "usage: stats --write <feature> [more]"),
                           (("stats", "--bogus"), "usage: stats [--write <feature> [more]]")):
            with self.subTest(args=args):
                code, out = repo.gate(*args)
                self.assertEqual(code, 2, out)
                self.assertIn(said, out)

    def test_stats_write_with_a_name_that_is_not_a_feature_is_refused(self):
        """stats --write with a name that is not a feature is refused by the known-feature rule"""
        code, out = Repo().gate("stats", "--write", "nope")
        self.assertEqual(code, 2, out)
        self.assertIn("known-feature", out)

    def test_stats_write_writes_one_line_per_subagent_and_model(self):
        """Stats write writes one line per subagent and model and names the agent with no transcript"""
        repo, projects = self.build()
        code, out = self.gate_in(repo, projects, "stats", "--write", "feat")
        self.assertEqual(code, 0, out)
        self.assertIn("tokens: 2 agent(s) read, 1 not found: gone", out)
        self.assertNotIn("not counted", out)
        agents = [r for r in self.records(repo) if r["role"] == "implementer"]
        self.assertEqual([(r["ticket"], r["agent"], r["model"], r["input"], r["output"], r["cache_read"], r["cache_write"]) for r in agents],
                         [("01", "a1", M1, 10, 20, 30, 40), ("01", "a1", M2, 100, 200, 300, 400), ("02", "a2", M1, 1, 2, 3, 4)])
        self.assertEqual({r["feature"] for r in agents}, {"feat"})
        self.assertEqual({r["date"] for r in agents}, {"2026-11-08"})

    def test_stats_write_counts_the_orchestrator_inside_the_log_window_only(self):
        """Stats write counts the orchestrator inside the log window only"""
        repo, projects = self.build()
        self.gate_in(repo, projects, "stats", "--write", "feat")
        orch = [r for r in self.records(repo) if r["role"] == "orchestrator"]
        self.assertEqual([(r["ticket"], r["agent"], r["model"], r["input"], r["output"], r["cache_read"], r["cache_write"]) for r in orch],
                         [("-", "s1", M1, 4, 40, 400, 4000), ("-", "s1", M2, 2, 20, 200, 2000)])

    def test_a_second_write_replaces_the_features_lines_and_keeps_the_others_byte_for_byte(self):
        """A second write replaces the feature's lines and keeps every other feature's lines byte for byte"""
        repo, projects = self.build()
        other = '{"feature":"other",  "agent":"zz","input":1}\n'
        old = '{"feature": "feat", "agent": "stale"}\n'
        repo.write(TOKENS, other + old + "not json\n")
        self.gate_in(repo, projects, "stats", "--write", "feat")
        first = self.text(repo)
        self.assertTrue(first.startswith(other))
        self.assertIn("not json\n", first)
        self.assertNotIn("stale", first)
        self.gate_in(repo, projects, "stats", "--write", "feat")
        second = self.text(repo)
        self.assertEqual(second.count('"agent": "a1"'), 2)
        self.assertEqual(second.count("\n"), first.count("\n"))
        self.assertTrue(second.startswith(other + "not json\n"))

    def test_a_last_log_line_without_seconds_reaches_the_end_of_its_minute(self):
        """A last log line without seconds reaches the end of its minute"""
        repo, projects = self.build()
        write_lines(os.path.join(repo.root, ".git", "factory", "build-log-feat.md"),
                    ["2026-11-08T10:00 dispatch 01 implementer --agent a1", "2026-11-08T11:00 note end"])
        self.gate_in(repo, projects, "stats", "--write", "feat")
        orch = [r for r in self.records(repo) if r["role"] == "orchestrator"]
        self.assertEqual(sum(r["input"] for r in orch), 4 + 2 + 5000)

    def test_an_orchestrator_with_no_messages_in_the_window_is_said(self):
        """An orchestrator with no messages in the window is said and the subagent lines are still written"""
        repo, projects = self.build()
        write_lines(os.path.join(projects, "-proj", "s1.jsonl"), [line("o0", M1, utc("2026-11-07T10:00:00"))])
        code, out = self.gate_in(repo, projects, "stats", "--write", "feat")
        self.assertEqual(code, 0, out)
        self.assertIn("orchestrator: no messages of s1.jsonl inside the build log's window", out)
        self.assertEqual({r["role"] for r in self.records(repo)}, {"implementer"})

    def test_a_repeated_message_id_counts_its_last_line(self):
        """A repeated message id counts its last line, as a streamed message grows"""
        repo, projects = self.build()
        write_lines(os.path.join(projects, "-proj", "s1", "subagents", "agent-a2.jsonl"), [
            line("m3", M1, utc("2026-11-08T10:07:00"), 1, 2, 3, 4), line("m3", M1, utc("2026-11-08T10:07:01"), 1, 50, 3, 4)])
        self.gate_in(repo, projects, "stats", "--write", "feat")
        a2 = [r for r in self.records(repo) if r["agent"] == "a2"]
        self.assertEqual([r["output"] for r in a2], [50])

    def test_a_missing_transcripts_root_writes_no_lines_and_exits_0(self):
        """A missing transcripts root writes no lines for the feature, says so and exits 0"""
        repo, projects = self.build()
        code, out = self.gate_in(repo, os.path.join(projects, "nowhere"), "stats", "--write", "feat")
        self.assertEqual(code, 0, out)
        self.assertIn("no transcripts root", out)
        self.assertFalse(os.path.exists(os.path.join(repo.root, TOKENS)))

    def test_a_log_with_no_agent_ids_writes_no_lines_and_exits_0(self):
        """A log with no agent ids writes no lines for the feature, says so and exits 0"""
        repo, projects = self.build(log_agents=())
        code, out = self.gate_in(repo, projects, "stats", "--write", "feat")
        self.assertEqual(code, 0, out)
        self.assertIn("no agent ids", out)
        self.assertFalse(os.path.exists(os.path.join(repo.root, TOKENS)))

    def test_stats_write_reads_the_default_root_when_the_variable_is_unset(self):
        """Stats write with GATE_PROJECTS_DIR unset reads the home default and exits 0"""
        repo, _ = self.build()
        home = tempfile.mkdtemp(prefix="gate-home-")
        atexit.register(shutil.rmtree, home, True)
        env = {k: v for k, v in CLEAN_ENV.items() if k != "GATE_PROJECTS_DIR"}
        env["HOME"] = home
        result = subprocess.run([sys.executable, GATE, "stats", "--write", "feat"], cwd=repo.root, capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(os.path.join(home, ".claude", "projects"), result.stdout)

    def two_windows(self, repo, projects):
        """A parent log 10:00 to 12:00 (a line at 10:30 and one at 11:30) and a fix feature `feat-review` inside it, 10:40 to 11:00."""
        write_lines(os.path.join(repo.root, ".git", "factory", "build-log-feat.md"), [
            "2026-11-08T10:00:00 dispatch 01 implementer --agent a1", "2026-11-08T10:30:00 note mid", "2026-11-08T11:30:00 note later", "2026-11-08T12:00:00 note end"])
        write_lines(os.path.join(repo.root, ".git", "factory", "build-log-feat-review.md"), [
            "2026-11-08T10:40:00 dispatch 01 implementer --agent a2", "2026-11-08T11:00:00 note end"])
        os.makedirs(os.path.join(repo.root, ".scratch", "feat-review", "issues"), exist_ok=True)
        repo.write(".scratch/feat-review/spec.md", "# s\n")
        write_lines(os.path.join(projects, "-proj", "s1.jsonl"), [
            line("p1", M1, utc("2026-11-08T10:10:00"), 1, 0, 0, 0),    # the parent's
            line("c1", M1, utc("2026-11-08T10:50:00"), 10, 0, 0, 0),   # inside the fix feature's lines
            line("p2", M1, utc("2026-11-08T11:10:00"), 100, 0, 0, 0),  # after the fix feature's last line: the parent's
            line("x1", M1, utc("2026-11-08T12:00:01"), 5000, 0, 0, 0)])
        repo.commit()

    def test_a_message_inside_another_features_window_counts_for_the_feature_with_the_latest_log_line(self):
        """A message counts once, for the feature whose build log has the latest line at or before it"""
        repo, projects = self.build()
        self.two_windows(repo, projects)
        self.gate_in(repo, projects, "stats", "--write", "feat", "feat-review")
        orch = {r["feature"]: r["input"] for r in self.records(repo) if r["role"] == "orchestrator"}
        self.assertEqual(orch, {"feat": 101, "feat-review": 10})

    def test_two_logs_with_the_same_latest_line_time_give_the_message_to_the_first_name(self):
        """Two logs whose latest line before a message has the same time give it to the first name in sort order"""
        repo, projects = self.build()
        self.two_windows(repo, projects)
        write_lines(os.path.join(repo.root, ".git", "factory", "build-log-feat-review.md"), [
            "2026-11-08T10:30:00 dispatch 01 implementer --agent a2", "2026-11-08T11:00:00 note end"])
        self.gate_in(repo, projects, "stats", "--write", "feat", "feat-review")
        orch = {r["feature"]: r["input"] for r in self.records(repo) if r["role"] == "orchestrator"}
        self.assertEqual(orch, {"feat": 111})

    def test_a_write_for_the_parent_alone_still_leaves_the_fix_features_messages_out(self):
        """Stats write for the parent alone reads the other features' logs and leaves their messages out"""
        repo, projects = self.build()
        self.two_windows(repo, projects)
        self.gate_in(repo, projects, "stats", "--write", "feat")
        orch = [r["input"] for r in self.records(repo) if r["role"] == "orchestrator"]
        self.assertEqual(orch, [101])

    def test_the_window_holds_in_a_zone_that_is_not_utc(self):
        """Stats write reads transcript times as UTC whatever zone the machine is in"""
        old = os.environ.get("TZ")
        os.environ["TZ"] = "America/New_York"
        time.tzset()
        try:
            repo, projects = self.build()
            code, out = self.gate_in(repo, projects, "stats", "--write", "feat")
        finally:
            if old is None:
                del os.environ["TZ"]
            else:
                os.environ["TZ"] = old
            time.tzset()
        self.assertEqual(code, 0, out)
        orch = [r for r in self.records(repo) if r["role"] == "orchestrator"]
        self.assertEqual(sum(r["input"] for r in orch), 4 + 2)

    def test_a_message_of_zeros_is_not_a_record_line(self):
        """A synthetic message of four zeros makes no record line"""
        repo, projects = self.build()
        write_lines(os.path.join(projects, "-proj", "s1", "subagents", "agent-a2.jsonl"), [
            line("m3", M1, utc("2026-11-08T10:07:00"), 1, 2, 3, 4), line("z", "<synthetic>", utc("2026-11-08T10:07:30"), 0, 0, 0, 0)])
        self.gate_in(repo, projects, "stats", "--write", "feat")
        self.assertNotIn("<synthetic>", self.text(repo))

    def test_agents_in_more_than_one_session_say_which_orchestrator_sessions_are_not_counted(self):
        """Agents in two sessions say the orchestrator of the other session is not counted"""
        repo, projects = self.build()
        write_lines(os.path.join(projects, "-proj", "s2", "subagents", "agent-a2.jsonl"), [line("m9", M1, utc("2026-11-08T10:07:00"), 1, 2, 3, 4)])
        os.remove(os.path.join(projects, "-proj", "s1", "subagents", "agent-a2.jsonl"))
        code, out = self.gate_in(repo, projects, "stats", "--write", "feat")
        self.assertEqual(code, 0, out)
        self.assertIn("tokens: orchestrator of s2 not counted (agents ran in 2 sessions; s1 counted)", out)

    def test_a_session_transcript_that_is_absent_is_said_as_absent(self):
        """A session with no transcript file beside its folder says the file is absent"""
        repo, projects = self.build()
        os.remove(os.path.join(projects, "-proj", "s1.jsonl"))
        code, out = self.gate_in(repo, projects, "stats", "--write", "feat")
        self.assertEqual(code, 0, out)
        self.assertIn("orchestrator: s1.jsonl is not beside the subagents folder", out)

    def test_the_writer_returns_the_records_it_wrote(self):
        """The writer returns the records of the features it wrote, for close to total"""
        repo, projects = self.build()
        from gate.tokens import write_tokens
        old = os.environ.get("GATE_PROJECTS_DIR")
        os.environ["GATE_PROJECTS_DIR"] = projects
        try:
            records = write_tokens(repo.root, {"tracker": ".scratch"}, ["feat"])
        finally:
            if old is None:
                del os.environ["GATE_PROJECTS_DIR"]
            else:
                os.environ["GATE_PROJECTS_DIR"] = old
        self.assertEqual(records, self.records(repo))
        self.assertEqual(len(records), 5)

    def test_the_existing_stats_totals_are_unchanged(self):
        """Stats totals for a subagent are the four kinds summed, each message once"""
        repo, projects = self.build(roles={"a1": "ticket-reviewer"})
        out = self.gate_in(repo, projects, "stats")[1]
        self.assertIn("feat ticket-reviewer: 1100 tokens (220 output) in 1 transcript(s)", out)


if __name__ == "__main__":
    unittest.main()
