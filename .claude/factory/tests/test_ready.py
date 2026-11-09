"""`gate.py ready`, `handover`, `close` and the records stamp.

Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import json
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

    def made(self, roles=False):
        repo = Repo()
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
