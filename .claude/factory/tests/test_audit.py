"""`gate.py audit` and the loop's rules.

Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import os
import subprocess
import time
import unittest

from fixtures import CLEAN_ENV, Repo, git, two_feature_line


class AuditRules(unittest.TestCase):
    """`gate.py audit`: the build log and the git history against the loop's rules, in a throwaway repo with a dated history."""

    T0 = int(time.time()) - 100000
    HUMAN = "- [ ] Reads well \u2014 needs-human: judge the wording"
    CLOSED = "fixed \u2014 test: saves the record and reads it back \u2014 red: .scratch/feat/red/01-unit-abc1234.txt"

    def make(self, tickets=("01",), kind=""):
        repo = Repo()
        git(repo.root, "branch", "-m", "feature/feat")
        repo.write(".scratch/feat/spec.md", "# Feat\n\n**Status:** ready-for-agent\n")
        for n in tickets:
            repo.ticket(n, status="ready-for-agent", boxes=self.HUMAN, kind=kind)
        self.dated(repo, "state", self.T0)
        return repo

    def dated(self, repo, message, epoch, *args):
        env = dict(CLEAN_ENV, GIT_AUTHOR_DATE="%d +0000" % epoch, GIT_COMMITTER_DATE="%d +0000" % epoch)
        base = ["git", "-C", repo.root, "-c", "user.name=t", "-c", "user.email=t@example.com"]
        subprocess.run(base + ["add", "-A"], check=True, capture_output=True, env=env)
        subprocess.run(base + ["commit", "-q", "--allow-empty", "-m", message] + list(args), check=True, capture_output=True, env=env)

    def merge_ticket(self, repo, label, epoch, review="closed", follow_up=False, issue=True):
        """Merges ticket/<label>-thing into feature/feat at `epoch`, its branch carrying a review file unless review is None.
        With follow_up the branch is ticket/<label>-fix, the subject `Merge ticket <label> follow-up:` and the file `<label>-followup`."""
        env = dict(CLEAN_ENV, GIT_AUTHOR_DATE="%d +0000" % epoch, GIT_COMMITTER_DATE="%d +0000" % epoch)
        branch, name, subject = ("ticket/%s-fix" % label, "%s-followup" % label, "Merge ticket %s follow-up: Ticket %s" % (label, label)) if follow_up else (
            "ticket/%s-thing" % label, label, "Merge ticket %s: Ticket %s" % (label, label))
        git(repo.root, "checkout", "-q", "-b", branch)
        repo.write("src/%s.txt" % name, "work\n")
        with (open if issue else (lambda *a, **k: open(os.devnull, "w")))(os.path.join(repo.root, ".scratch/feat/issues/%s-thing.md" % label), "a", encoding="utf-8") as handle:
            handle.write("\n- worked on %s\n" % branch)  # the branch changes its own issue file
        if review:
            status = self.CLOSED if review == "closed" else "open"
            repo.write(".scratch/feat/reviews/%s.md" % name, "# Review: ticket %s\nTip reviewed: abc1234.\n## Blocking\n1. one thing | %s\n## Notes\n1. a note | left: fine\n" % (label, status))
        self.dated(repo, "work on %s" % label, epoch - 50)
        git(repo.root, "checkout", "-q", "feature/feat")
        subprocess.run(["git", "-C", repo.root, "-c", "user.name=t", "-c", "user.email=t@example.com", "merge", "--no-ff", "-q", "-m", subject, branch],
                       check=True, capture_output=True, env=env)
        return repo.head()

    def log(self, repo, *lines):
        """Each line is (epoch, 'verb args')."""
        path = os.path.join(repo.root, ".git", "factory", "build-log-feat.md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            for epoch, text in lines:
                handle.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(epoch)), text))

    def prose(self, repo, epoch, text):
        """A line in the form the log had before the grammar: dash-prefixed, minutes only."""
        path = os.path.join(repo.root, ".git", "factory", "build-log-feat.md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("- %s %s\n" % (time.strftime("%Y-%m-%d %H:%M", time.localtime(epoch)), text))

    def stamp(self, repo, built=None, records=None):
        path = os.path.join(repo.root, ".git", "factory-ready")
        with open(path, "w", encoding="utf-8") as handle:
            if records:
                handle.write("%s\nfeat\n2026-11-07T10:00:00\nbuilt %s\n" % (records, built))
            else:
                handle.write("%s\nfeat\n2026-11-07T10:00:00\n" % (built or repo.head()))

    def test_audit_reports_a_merge_without_a_review(self):
        """Audit reports a foundational merge without a review; an ordinary ticket needs none"""
        repo = self.make(kind="foundational")
        self.merge_ticket(repo, "01", self.T0 + 1000, review=None)
        code, out = repo.gate("audit", "feat")
        self.assertEqual(code, 1, out)
        self.assertIn("no .scratch/feat/reviews/01.md on its branch", out)
        self.assertIn("a `Kind: foundational` ticket is reviewed before it merges", out)
        tooling = self.make(kind="walk-tooling")
        self.merge_ticket(tooling, "01", self.T0 + 1000, review=None)
        self.assertIn("no .scratch/feat/reviews/01.md on its branch", tooling.gate("audit", "feat")[1])
        plain = self.make()
        self.merge_ticket(plain, "01", self.T0 + 1000, review=None)
        out = plain.gate("audit", "feat")[1]
        self.assertNotIn("reviews/01.md", out)  # its second read is the whole-branch review's
        other = self.make()
        self.merge_ticket(other, "01", self.T0 + 1000, review="open")
        code, out = other.gate("audit", "feat")
        self.assertEqual(code, 1, out)
        self.assertIn("blocking finding 1 was not closed (status `open`)", out)
        closed = self.make()
        self.merge_ticket(closed, "01", self.T0 + 1000)
        out = closed.gate("audit", "feat")[1]
        self.assertNotIn("reviews/01.md", out)
        self.assertNotIn("was not closed", out)

    def test_the_audit_expects_a_follow_up_review(self):
        """The audit expects a follow-up review"""
        def follow_up(review, rules="red-audit\nfollow-up\n"):
            repo = self.make(kind="foundational")  # a reviewed kind: an ordinary ticket's follow-up needs no review file either
            repo.write(".claude/factory/RULES", rules)
            self.dated(repo, "rules", self.T0 + 10)
            self.merge_ticket(repo, "01", self.T0 + 1000)
            self.merge_ticket(repo, "01", self.T0 + 2000, review=review, follow_up=True)
            return repo.gate("audit", "feat")[1]
        out = follow_up(None)
        self.assertIn("no .scratch/feat/reviews/01-followup.md (or 01-followup-<n>.md) on its branch", out)
        self.assertIn("blocking finding 1 was not closed (status `open`)", follow_up("open"))
        out = follow_up("closed")
        self.assertNotIn("followup", out)
        self.assertNotIn("was not closed", out)
        self.assertNotIn("followup", follow_up(None, rules="red-audit\n"))  # merged by a gate that had no follow-up rule: judged as before

    def test_audit_lists_a_follow_up_merge_that_changes_only_its_review_file(self):
        """Audit lists a follow-up merge that changes only its review file"""
        repo = self.make()
        repo.write(".claude/factory/RULES", "red-audit\nfollow-up\n")
        self.dated(repo, "rules", self.T0 + 10)
        self.merge_ticket(repo, "01", self.T0 + 1000)
        merged = self.merge_ticket(repo, "01", self.T0 + 2000, review="open", follow_up=True, issue=False)
        out = repo.gate("audit", "feat")[1]
        self.assertIn("blocking finding 1 was not closed (status `open`)", out)
        self.assertIn(merged[:7], out)

    def test_audit_reports_a_merge_without_log_lines(self):
        """Audit reports a merge without log lines"""
        repo = self.make()
        merged = self.merge_ticket(repo, "01", self.T0 + 1000)
        code, out = repo.gate("audit", "feat")
        self.assertEqual(code, 1, out)
        self.assertIn("expected and did not find: feat: merge reviews and log pairs: merge-end 01 %s" % merged[:7], out)
        self.log(repo, (self.T0 + 990, "merge-start 01 abc1234"), (self.T0 + 1010, "merge-end 01 %s" % merged))
        out = repo.gate("audit", "feat")[1]
        self.assertIn("ok: feat: merge reviews and log pairs", out)
        self.assertNotIn("expected and did not find: feat: merge reviews", out)

    def test_audit_reports_overlapping_merges(self):
        """Audit reports overlapping merges"""
        repo = self.make()
        self.log(repo, (self.T0 + 100, "merge-start 01 abc1234"), (self.T0 + 110, "merge-start 02 def5678"),
                 (self.T0 + 120, "merge-end 01 conflict"), (self.T0 + 130, "merge-end 02 conflict"))
        code, out = repo.gate("audit", "feat")
        self.assertEqual(code, 1, out)
        self.assertIn("merge-start 02", out)
        self.assertIn("while the merge of 01", out)
        resumed = self.make()
        self.log(resumed, (self.T0 + 100, "merge-start 01 abc1234"), (self.T0 + 110, "merge-end 01 conflict"),
                 (self.T0 + 120, "merge-start 01 abc1234"), (self.T0 + 130, "merge-end 01 " + "a" * 40))
        out = resumed.gate("audit", "feat")[1]
        self.assertIn("ok: feat: merges did not overlap", out)

    def test_audit_reports_a_commit_during_a_merge(self):
        """Audit reports a commit during a merge"""
        repo = self.make()
        repo.write("notes.txt", "a commit made in the integration worktree\n")
        self.dated(repo, "side commit", self.T0 + 995)
        repo.write("more.txt", "the last commit before the merge\n")
        self.dated(repo, "last commit", self.T0 + 996)
        merged = self.merge_ticket(repo, "01", self.T0 + 1000)
        self.log(repo, (self.T0 + 990, "merge-start 01 abc1234"), (self.T0 + 1010, "merge-end 01 %s" % merged))
        code, out = repo.gate("audit", "feat")
        self.assertEqual(code, 1, out)
        self.assertIn("violation: feat: no commit landed during a merge", out)
        self.assertIn("between merge-start 01", out)
        clear = self.make()
        clear.write("notes.txt", "made well before the merge\n")
        self.dated(clear, "side commit", self.T0 + 500)
        merged = self.merge_ticket(clear, "01", self.T0 + 1000)
        self.log(clear, (self.T0 + 990, "merge-start 01 abc1234"), (self.T0 + 1010, "merge-end 01 %s" % merged))
        self.assertIn("ok: feat: no commit landed during a merge", clear.gate("audit", "feat")[1])

    def test_audit_still_reads_an_old_hand_logged_merged_result(self):
        """Audit still reads an old hand-logged merge-end merged"""
        repo = self.make()
        repo.write("notes.txt", "a commit made in the integration worktree\n")
        self.dated(repo, "side commit", self.T0 + 995)
        repo.write("more.txt", "the last commit before the merge\n")
        self.dated(repo, "last commit", self.T0 + 996)
        self.merge_ticket(repo, "01", self.T0 + 1000)
        self.log(repo, (self.T0 + 990, "merge-start 01 abc1234"), (self.T0 + 1010, "merge-end 01 merged"))
        code, out = repo.gate("audit", "feat")
        self.assertIn("ok: feat: merges did not overlap", out)
        self.assertIn("violation: feat: no commit landed during a merge", out)

    def test_audit_exempts_the_merges_first_parent_from_its_window(self):
        """Audit exempts the merge's first parent from its window"""
        repo = self.make()
        repo.write("notes.txt", "records commit, then gate.py merge straight away\n")
        self.dated(repo, "records commit", self.T0 + 990)  # the same second as merge-start
        merged = self.merge_ticket(repo, "01", self.T0 + 1000)
        self.log(repo, (self.T0 + 990, "merge-start 01 abc1234"), (self.T0 + 1010, "merge-end 01 %s" % merged))
        code, out = repo.gate("audit", "feat")
        self.assertNotIn("violation: feat: no commit landed during a merge", out)
        self.assertIn("ok: feat: no commit landed during a merge", out)

    def test_audit_reports_a_lone_first_parent_made_after_merge_start(self):
        """Audit reports a lone first parent made after merge-start"""
        repo = self.make()
        repo.write("notes.txt", "landed while the merge was running\n")
        self.dated(repo, "mid-merge commit", self.T0 + 995)  # becomes the merge's first parent, but was not in place at merge-start
        merged = self.merge_ticket(repo, "01", self.T0 + 1000)
        self.log(repo, (self.T0 + 990, "merge-start 01 abc1234"), (self.T0 + 1010, "merge-end 01 %s" % merged))
        code, out = repo.gate("audit", "feat")
        self.assertEqual(code, 1, out)
        self.assertIn("violation: feat: no commit landed during a merge", out)

    def test_audit_exempts_a_first_parent_only_from_its_own_merges_window(self):
        """Audit exempts a first parent only from its own merge's window"""
        repo = self.make(tickets=("01", "02"))
        first = self.merge_ticket(repo, "01", self.T0 + 1000)
        repo.write("notes.txt", "the first parent of merge 02, made in merge 01's start second\n")
        self.dated(repo, "records commit", self.T0 + 990)
        second = self.merge_ticket(repo, "02", self.T0 + 2000)
        self.log(repo, (self.T0 + 990, "merge-start 01 abc1234"), (self.T0 + 1010, "merge-end 01 %s" % first),
                 (self.T0 + 1990, "merge-start 02 abc1234"), (self.T0 + 2010, "merge-end 02 %s" % second))
        code, out = repo.gate("audit", "feat")
        self.assertEqual(code, 1, out)
        self.assertIn("landed between merge-start 01", out)

    def kind(self, repo, label, kind, blocked=None):
        path = os.path.join(repo.root, ".scratch/feat/issues/%s-thing.md" % label)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        text = text.replace("**Status:**", "**Kind:** %s\n\n**Status:**" % kind, 1)
        if blocked:
            text = text.replace("**Blocked by:** None (can start immediately)", "**Blocked by:** %s" % blocked)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        self.dated(repo, "kind %s" % label, self.T0 + 10)

    def test_audit_reports_a_late_foundation_read(self):
        """Audit reports a late foundation read"""
        repo = self.make(("01", "02"))
        self.kind(repo, "01", "foundational")
        self.kind(repo, "02", "design", blocked="01")
        self.log(repo, (self.T0 + 100, "dispatch 02 implementer --agent a2"), (self.T0 + 200, "foundation-read 01 --agent a1"))
        code, out = repo.gate("audit", "feat")
        self.assertEqual(code, 1, out)
        self.assertIn("violation: feat: foundation read before dependents: foundation-read 01", out)
        self.assertIn("is after the dispatch of ticket 02", out)
        early = self.make(("01", "02"))
        self.kind(early, "01", "foundational")
        self.kind(early, "02", "design", blocked="01")
        self.log(early, (self.T0 + 100, "foundation-read 01 --agent a1"), (self.T0 + 200, "dispatch 02 implementer --agent a2"))
        self.assertIn("ok: feat: foundation read before dependents", early.gate("audit", "feat")[1])
        silent = self.make(("01", "02"))
        self.kind(silent, "01", "foundational")
        self.kind(silent, "02", "design", blocked="01")
        self.log(silent, (self.T0 + 200, "dispatch 02 implementer --agent a2"))
        self.assertIn("expected and did not find: feat: foundation read before dependents: foundation-read 01", silent.gate("audit", "feat")[1])

    def test_audit_reports_an_unlogged_design_decision(self):
        """Audit reports an unlogged design decision"""
        repo = self.make()
        self.kind(repo, "01", "design")
        merged = self.merge_ticket(repo, "01", self.T0 + 1000)
        code, out = repo.gate("audit", "feat")
        self.assertEqual(code, 1, out)
        self.assertIn("expected and did not find: feat: design decisions logged", out)
        self.assertIn("before the merge of ticket 01", out)
        self.log(repo, (self.T0 + 900, 'open 1 "Pick the wording for ticket 01"'))
        self.assertIn("ok: feat: design decisions logged", repo.gate("audit", "feat")[1])

    def stamp_time(self, epoch):
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(epoch))

    def test_audit_reads_a_merge_abort_logged_later(self):
        """Audit reads a merge-abort logged later"""
        repo = self.make(("04",))
        t1, t2 = self.stamp_time(self.T0 + 100), self.stamp_time(self.T0 + 110)
        self.log(repo, (self.T0 + 100, "merge-start 04 abc1234"), (self.T0 + 110, "merge-start 04 abc1234"),
                 (self.T0 + 120, "merge-end 04 " + "a" * 40))
        code, out = repo.gate("audit", "feat")
        self.assertIn("violation: feat: merges did not overlap", out)
        self.log(repo, (self.T0 + 200, 'merge-abort 04 %s "stopped by the user"' % t1))
        out = repo.gate("audit", "feat")[1]
        self.assertIn("ok: feat: merges did not overlap: merge-start 04 %s aborted (logged later): stopped by the user" % t1, out)
        self.assertNotIn("violation: feat: merges did not overlap", out)

    def test_audit_reports_a_merge_abort_naming_no_open_start(self):
        """Audit reports a merge-abort naming no open start"""
        repo = self.make(("04",))
        self.log(repo, (self.T0 + 100, "merge-start 04 abc1234"), (self.T0 + 120, "merge-end 04 " + "a" * 40),
                 (self.T0 + 200, 'merge-abort 04 %s "no such start"' % self.stamp_time(self.T0 + 50)))
        out = repo.gate("audit", "feat")[1]
        self.assertIn("violation: feat: merges did not overlap: merge-abort 04 %s names no merge-start" % self.stamp_time(self.T0 + 50), out)
        ended = self.make(("04",))
        self.log(ended, (self.T0 + 100, "merge-start 04 abc1234"), (self.T0 + 120, "merge-end 04 " + "a" * 40),
                 (self.T0 + 200, 'merge-abort 04 %s "already ended"' % self.stamp_time(self.T0 + 100)))
        out = ended.gate("audit", "feat")[1]
        self.assertIn("violation: feat: merges did not overlap: merge-abort 04 %s names a merge-start that was ended" % self.stamp_time(self.T0 + 100), out)
        other = self.make(("04", "05"))
        self.log(other, (self.T0 + 100, "merge-start 04 abc1234"), (self.T0 + 120, "merge-start 05 abc1234"),
                 (self.T0 + 130, "merge-end 05 " + "a" * 40),
                 (self.T0 + 200, 'merge-abort 05 %s "wrong ticket"' % self.stamp_time(self.T0 + 100)))
        self.assertIn("violation: feat: merges did not overlap: merge-abort 05", other.gate("audit", "feat")[1])

    def decide(self, spec_text, side=False):
        """A design ticket 01 merged at T0+1000; the spec changed in one commit, on the feature (an ancestor of the merge) or on a side branch."""
        repo = self.make()
        self.kind(repo, "01", "design")
        if side:
            git(repo.root, "checkout", "-q", "-b", "side")
        repo.write(".scratch/feat/spec.md", spec_text)
        self.dated(repo, "the user decided", self.T0 + 500)
        commit = repo.head()
        if side:
            git(repo.root, "checkout", "-q", "feature/feat")
        self.merge_ticket(repo, "01", self.T0 + 1000)
        return repo, commit

    SPEC = "# Feat\n\n**Status:** ready-for-agent\n\n## Open list\n\n1. Pick the wording (ticket 01)\n2. Something else\n"

    def test_audit_reads_a_decided_item_logged_later(self):
        """Audit reads a decided item logged later"""
        repo, commit = self.decide(self.SPEC)
        self.assertIn("expected and did not find: feat: design decisions logged", repo.gate("audit", "feat")[1])
        self.log(repo, (self.T0 + 2000, "decided 1 " + commit))
        out = repo.gate("audit", "feat")[1]
        self.assertIn("ok: feat: design decisions logged: ticket 01 decided in %s (logged later)" % commit[:7], out)
        other, commit = self.decide(self.SPEC)
        self.log(other, (self.T0 + 2000, "decided 2 " + commit))
        out = other.gate("audit", "feat")[1]
        self.assertIn("violation: feat: design decisions logged: decided 2", out)
        self.assertIn("item 2 does not name ticket 01", out)

    def test_audit_reports_a_decided_commit_that_is_not_an_ancestor_or_changes_no_spec(self):
        """Audit reports a decided commit that is not an ancestor or changes no spec"""
        repo, commit = self.decide(self.SPEC, side=True)
        self.log(repo, (self.T0 + 2000, "decided 1 " + commit))
        out = repo.gate("audit", "feat")[1]
        self.assertIn("violation: feat: design decisions logged: decided 1 %s is not an ancestor of the merge of ticket 01" % commit[:7], out)
        plain, commit = self.decide(self.SPEC)
        elsewhere = subprocess.run(["git", "-C", plain.root, "log", "--format=%H", "--grep", "work on 01", "-n1"], capture_output=True, text=True).stdout.strip()
        self.log(plain, (self.T0 + 2000, "decided 1 " + elsewhere))
        out = plain.gate("audit", "feat")[1]
        self.assertIn("violation: feat: design decisions logged: decided 1 %s does not change the spec" % elsewhere[:7], out)
        plain_ticket = self.make()
        self.merge_ticket(plain_ticket, "01", self.T0 + 1000)
        self.log(plain_ticket, (self.T0 + 2000, "decided 1 " + commit))
        self.assertIn("violation: feat: design decisions logged: decided 1 %s: the feature has no merged Kind: design ticket" % commit[:7], plain_ticket.gate("audit", "feat")[1])
        gone = self.make()
        self.kind(gone, "01", "design")
        self.merge_ticket(gone, "01", self.T0 + 1000)
        self.log(gone, (self.T0 + 2000, "decided 1 " + "f" * 40))
        self.assertIn("violation: feat: design decisions logged: decided 1 fffffff is not a commit", gone.gate("audit", "feat")[1])

    def test_log_refuses_merge_abort_and_decided_with_the_wrong_shape(self):
        """Log refuses merge-abort and decided with the wrong shape"""
        repo = self.make()
        for words in (("merge-abort", "04"), ("merge-abort", "x", "2026-11-08T10:00:00", "why"), ("merge-abort", "04", "yesterday", "why"),
                      ("merge-abort", "04", "2026-11-08T10:00:00"), ("decided", "1"), ("decided", "x", "abcdef1"), ("decided", "1", "abcdef1", "extra"), ("decided", "1", "not-a-hash")):
            code, out = repo.gate("log", "feat", *words)
            self.assertEqual(code, 2, (words, out))
            self.assertIn("gate: refused by log-grammar", out)
            self.assertIn("merge-abort <NN> <start time>" if words[0] == "merge-abort" else "decided <n> <commit>", out)
        self.assertEqual(repo.gate("log", "feat", "merge-abort", "4", "2026-11-08T10:00:00", "stopped", "by", "the", "user")[0], 0)
        self.assertEqual(repo.gate("log", "feat", "decided", "1", "abcdef1")[0], 0)
        self.assertIn("merge-abort 04 2026-11-08T10:00:00 stopped by the user", repo.gate("log", "feat")[1])

    def test_audit_does_not_count_lines_from_before_the_grammar(self):
        """Audit does not count lines from before the grammar"""
        repo = self.make(("01", "02"))
        self.merge_ticket(repo, "01", self.T0 + 1000)
        self.prose(repo, self.T0 + 900, "merged 01 by hand")
        self.log(repo, (self.T0 + 2000, "dispatch 02 implementer --agent a2"))
        out = repo.gate("audit", "feat")[1]
        self.assertIn("expected and did not find: feat: merge reviews and log pairs: merge-end 01", out)
        self.assertIn("(before the log grammar began; not counted)", out)
        self.assertNotIn("violation: feat: merge", out)

    def test_audit_counts_a_late_first_dispatch_in_an_iso_log(self):
        """Audit counts a late first dispatch in an iso log"""
        repo = self.make(("01", "02"))
        self.merge_ticket(repo, "01", self.T0 + 1000)
        self.log(repo, (self.T0 + 2000, "dispatch 02 implementer --agent a2"))
        code, out = repo.gate("audit", "feat")
        self.assertEqual(code, 1, out)
        self.assertIn("expected and did not find: feat: merge reviews and log pairs: merge-end 01", out)
        self.assertIn("expected and did not find: feat: dispatched once: dispatch 01 implementer", out)
        self.assertNotIn("not counted", out)

    def test_audit_does_not_match_a_merge_end_for_another_commit(self):
        """Audit does not match a merge end for another commit"""
        repo = self.make()
        merged = self.merge_ticket(repo, "01", self.T0 + 1000)
        other = ("f" if merged[0] != "f" else "e") * 40
        self.log(repo, (self.T0 + 990, "merge-start 01 abc1234"), (self.T0 + 1010, "merge-end 01 %s" % other))
        out = repo.gate("audit", "feat")[1]
        self.assertIn("expected and did not find: feat: merge reviews and log pairs: merge-end 01 %s" % merged[:7], out)

    def test_audit_catches_a_commit_in_the_second_a_merge_starts(self):
        """Audit catches a commit in the second a merge starts"""
        repo = self.make()
        repo.write("notes.txt", "x\n")
        self.dated(repo, "side commit", self.T0 + 990)
        repo.write("more.txt", "y\n")
        self.dated(repo, "last commit", self.T0 + 991)  # the first parent; the side commit is not
        merged = self.merge_ticket(repo, "01", self.T0 + 1000)
        self.log(repo, (self.T0 + 990, "merge-start 01 abc1234"), (self.T0 + 1010, "merge-end 01 %s" % merged))
        code, out = repo.gate("audit", "feat")
        self.assertEqual(code, 1, out)
        self.assertIn("violation: feat: no commit landed during a merge", out)

    def test_audit_counts_only_attempts_not_review_rounds(self):
        """Audit counts only attempts not review rounds"""
        repo = self.make()
        self.merge_ticket(repo, "01", self.T0 + 1000)
        self.log(repo, (self.T0 + 100, "dispatch 01 implementer --agent a1"), (self.T0 + 110, "report 01 implementer"),
                 (self.T0 + 120, "report 01 ticket-reviewer"), (self.T0 + 130, "resume 01 implementer"), (self.T0 + 140, "report 01 implementer"),
                 (self.T0 + 150, "merge-end 01 conflict"), (self.T0 + 160, "resume 01 implementer"), (self.T0 + 170, "report 01 implementer"))
        self.assertIn("ok: feat: dispatched once", repo.gate("audit", "feat")[1])
        again = self.make()
        self.merge_ticket(again, "01", self.T0 + 1000)
        self.log(again, (self.T0 + 100, "dispatch 01 implementer --agent a1"), (self.T0 + 110, "report 01 implementer"),
                 (self.T0 + 130, "resume 01 implementer"), (self.T0 + 140, "report 01 implementer"), (self.T0 + 160, "resume 01 implementer"))
        self.assertIn("attempted 3 times", again.gate("audit", "feat")[1])

    def test_the_audit_counts_a_follow_up_as_an_attempt(self):
        """The audit counts a follow-up as an attempt"""
        repo = self.make()
        self.merge_ticket(repo, "01", self.T0 + 1000)
        self.log(repo, (self.T0 + 100, "dispatch 01 implementer --agent a1"), (self.T0 + 150, "report 01 implementer"),
                 (self.T0 + 1500, "dispatch 01 implementer --agent a2 --follow-up"))
        out = repo.gate("audit", "feat")[1]
        self.assertIn("ok: feat: dispatched once", out)
        self.assertNotIn("dispatch lines", out)
        three = self.make()
        self.merge_ticket(three, "01", self.T0 + 1000)
        self.log(three, (self.T0 + 100, "dispatch 01 implementer --agent a1"), (self.T0 + 150, "report 01 implementer"),
                 (self.T0 + 1500, "dispatch 01 implementer --agent a2 --follow-up"), (self.T0 + 1600, "dispatch 01 implementer --agent a3 --follow-up"))
        out = three.gate("audit", "feat")[1]
        self.assertIn("attempted 3 times (1 dispatch, 0 resume, 2 follow-up)", out)
        self.assertIn("a resume after a reviewer's report or a merge abort is a round", out)

    def test_needs_triage_then_done_by_hand_clears_the_third_follow_up_attempt(self):
        """Needs-triage then done by hand clears the third follow-up attempt"""
        repo = self.make()
        self.merge_ticket(repo, "01", self.T0 + 1000)
        self.log(repo, (self.T0 + 100, "dispatch 01 implementer --agent a1"), (self.T0 + 150, "report 01 implementer"),
                 (self.T0 + 1500, "dispatch 01 implementer --agent a2 --follow-up"), (self.T0 + 1600, "dispatch 01 implementer --agent a3 --follow-up"))
        for at, status in ((1700, "needs-triage"), (1800, "done")):
            repo.ticket("01", status=status, boxes=self.HUMAN)
            self.dated(repo, "Status: %s" % status, self.T0 + at)
        out = repo.gate("audit", "feat")[1]
        self.assertNotIn("attempted 3 times", out)
        self.assertIn("ok: feat: dispatched once", out)

    def test_audit_reports_a_second_dispatch_and_a_third_attempt(self):
        """Audit reports a second dispatch and a third attempt"""
        repo = self.make()
        self.merge_ticket(repo, "01", self.T0 + 1000)
        self.log(repo, (self.T0 + 100, "dispatch 01 implementer --agent a1"), (self.T0 + 200, "dispatch 01 implementer --agent a2"))
        out = repo.gate("audit", "feat")[1]
        self.assertIn("has 2 dispatch lines for its implementer", out)
        third = self.make()
        self.merge_ticket(third, "01", self.T0 + 1000)
        self.log(third, (self.T0 + 100, "dispatch 01 implementer --agent a1"), (self.T0 + 150, "report 01 implementer"), (self.T0 + 200, "resume 01 implementer"),
                 (self.T0 + 250, "report 01 implementer"), (self.T0 + 300, "resume 01 implementer"))
        out = third.gate("audit", "feat")[1]
        self.assertIn("attempted 3 times", out)
        second = self.make()
        self.merge_ticket(second, "01", self.T0 + 1000)
        self.log(second, (self.T0 + 100, "dispatch 01 implementer --agent a1"), (self.T0 + 150, "report 01 implementer"), (self.T0 + 200, "resume 01 implementer"))
        self.assertIn("ok: feat: dispatched once", second.gate("audit", "feat")[1])

    def stamped_report(self, text):
        repo = self.make()
        built = repo.head()
        self.stamp(repo, built)
        repo.write(".scratch/feat/report.md", text.replace("BUILT", built[:7]))
        return repo, built

    def test_audit_checks_a_reports_tip(self):
        """Audit checks a report's tip"""
        repo, built = self.stamped_report("# Report\n\n- Built tip: BUILT\n")
        code, out = repo.gate("audit", "feat", "--report", ".scratch/feat/report.md")
        self.assertEqual(code, 0, out)
        self.assertIn("ok: report .scratch/feat/report.md", out)
        wrong, _ = self.stamped_report("# Report\n\n- Built tip: 1234567\n")
        code, out = wrong.gate("audit", "feat", "--report", ".scratch/feat/report.md")
        self.assertEqual(code, 1, out)
        self.assertIn("names built tip 1234567, but the built-tip stamp is", out)
        stray, _ = self.stamped_report("# Report\n\n- Built tip: BUILT\n\nSee 7654321 for the rest.\n")
        code, out = stray.gate("audit", "feat", "--report", ".scratch/feat/report.md")
        self.assertEqual(code, 1, out)
        self.assertIn("names 7654321, which is not a commit here", out)
        side, built = self.stamped_report("# Report\n")
        git(side.root, "checkout", "-q", "-b", "elsewhere")
        side.write("other.txt", "x\n")
        side.commit()
        off = side.head()[:7]
        git(side.root, "checkout", "-q", "feature/feat")
        side.write(".scratch/feat/report.md", "# Report\n\n- Built tip: %s\n\nSee %s.\n" % (built[:7], off))
        code, out = side.gate("audit", "feat", "--report", ".scratch/feat/report.md")
        self.assertEqual(code, 1, out)
        self.assertIn("names %s, which is not on this branch" % off, out)

    def test_audit_checks_a_reports_counts(self):
        """Audit checks a report's counts"""
        repo, _ = self.stamped_report("# Report\n\n- Built tip: BUILT\n\n| Measure | Value |\n|---|---|\n| Tickets | 1 |\n| Boxes for a person to judge | 1 |\n| Wall-clock hours | 9 |\n")
        code, out = repo.gate("audit", "feat", "--report", ".scratch/feat/report.md")
        self.assertEqual(code, 0, out)
        wrong, _ = self.stamped_report("# Report\n\n- Built tip: BUILT\n\n| Measure | Value |\n|---|---|\n| Tickets | 7 |\n| Boxes proved | 0 |\n")
        code, out = wrong.gate("audit", "feat", "--report", ".scratch/feat/report.md")
        self.assertEqual(code, 1, out)
        self.assertIn("`Tickets` says 7, the gate computes 1", out)
        self.assertNotIn("Boxes proved", out)

    def test_audit_checks_the_facts_blocks_boxes_and_tickets(self):
        """Audit checks the facts block's boxes and tickets"""
        repo, _ = self.stamped_report("# Report\n\n- Built tip: BUILT\n- Tickets: 0 done of 1 (0 for the user)\n- Boxes: 0 proved, 1 for a person to judge\n")
        code, out = repo.gate("audit", "feat", "--report", ".scratch/feat/report.md")
        self.assertEqual(code, 0, out)
        wrong, _ = self.stamped_report("# Report\n\n- Built tip: BUILT\n- Tickets: 0 done of 1 (0 for the user)\n- Boxes: 99 proved, 98 for a person to judge\n")
        code, out = wrong.gate("audit", "feat", "--report", ".scratch/feat/report.md")
        self.assertEqual(code, 1, out)
        self.assertIn("`Boxes: proved` says 99, the gate computes 0", out)
        self.assertIn("`Boxes: for a person` says 98, the gate computes 1", out)
        user = self.make()
        path = os.path.join(user.root, ".scratch/feat/issues/01-thing.md")
        with open(path, encoding="utf-8") as handle:
            text = handle.read().replace("ready-for-agent", "ready-for-human")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        self.dated(user, "user ticket", self.T0 + 5)
        built = user.head()
        self.stamp(user, built)
        user.write(".scratch/feat/report.md", "# Report\n\n- Built tip: %s\n- Tickets: 0 done of 1 (1 for the user)\n" % built[:7])
        code, out = user.gate("audit", "feat", "--report", ".scratch/feat/report.md")
        self.assertEqual(code, 0, out)

    def test_audit_needs_the_built_tip_stamp(self):
        """Audit needs the built tip stamp"""
        repo = self.make()
        code, out = repo.gate("audit", "feat")
        self.assertEqual(code, 1, out)
        self.assertIn("expected and did not find: stamps: the built-tip stamp", out)
        built = repo.head()
        repo.write("records.txt", "x\n")
        self.dated(repo, "Close feat", self.T0 + 5)
        self.stamp(repo, built, records=repo.head())
        self.assertIn("records stamp %s is its child" % repo.head()[:7], repo.gate("audit", "feat")[1])
        repo.write("more.txt", "y\n")
        self.dated(repo, "another", self.T0 + 6)
        self.stamp(repo, built, records=repo.head())
        out = repo.gate("audit", "feat")[1]
        self.assertIn("has parent", out)

    def test_audit_refuses_a_stamp_for_another_feature(self):
        """Audit refuses a stamp for another feature"""
        repo = self.make()
        path = os.path.join(repo.root, ".git", "factory-ready")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("%s\nother-feature\n2026-11-07T10:00:00\n" % repo.head())
        code, out = repo.gate("audit", "feat")
        self.assertEqual(code, 1, out)
        self.assertIn("the stamp is for other-feature, not feat: run `gate.py ready feat`", out)
        self.assertNotIn("stamped (no records stamp yet)", out)

    def test_audit_refuses_a_stale_stamp(self):
        """Audit refuses a stale stamp"""
        repo = self.make()
        self.stamp(repo, repo.head())
        stale = repo.head()
        repo.write("later.txt", "x\n")
        self.dated(repo, "after the stamp", self.T0 + 5)
        code, out = repo.gate("audit", "feat")
        self.assertEqual(code, 1, out)
        self.assertIn("the stamp is at %s, HEAD is %s: commits after the stamp need a new `ready`" % (stale[:7], repo.head()[:7]), out)

    def test_audit_lets_a_records_close_be_audited_before_its_stamp(self):
        """Audit lets a records close be audited before its stamp"""
        repo = self.make()
        built = repo.head()
        self.stamp(repo, built)
        repo.write(".scratch/feat/notes.md", "x\n")
        self.dated(repo, "Close feat", self.T0 + 5)
        repo.write(".scratch/feat/report.md", "# Report\n\n- Built tip: %s\n" % built[:7])
        code, out = repo.gate("audit", "feat", "--report", ".scratch/feat/report.md")
        self.assertIn("ok: stamps: built tip %s stamped (no records stamp yet)" % built[:7], out)
        self.assertNotIn("the stamp is at", out)

    def report_audit(self, repo):
        repo.write(".scratch/feat/report.md", "# Report\n\n- Built tip: %s\n" % repo.head()[:7])
        return repo.gate("audit", "feat", "--report", ".scratch/feat/report.md")[1]

    def test_audit_with_a_report_refuses_a_stamp_two_commits_behind(self):
        """Audit with a report refuses a stamp two commits behind"""
        repo = self.make()
        self.stamp(repo, repo.head())
        for n, name in enumerate(("one", "two")):
            repo.write(".scratch/feat/%s.md" % name, "x\n")
            self.dated(repo, name, self.T0 + 5 + n)
        self.assertIn("the stamp is at", self.report_audit(repo))

    def test_audit_with_a_report_refuses_a_commit_above_a_records_stamp(self):
        """Audit with a report refuses a commit above a records stamp"""
        repo = self.make()
        built = repo.head()
        repo.write(".scratch/feat/one.md", "x\n")
        self.dated(repo, "Close feat", self.T0 + 5)
        self.stamp(repo, built, records=repo.head())
        repo.write(".scratch/feat/two.md", "x\n")
        self.dated(repo, "after the close", self.T0 + 6)
        self.assertIn("the stamp is at", self.report_audit(repo))

    def test_audit_with_a_report_refuses_a_code_commit_above_the_stamp(self):
        """Audit with a report refuses a code commit above the stamp"""
        repo = self.make()
        self.stamp(repo, repo.head())
        repo.write("code.txt", "x\n")
        self.dated(repo, "a code change", self.T0 + 5)
        self.assertIn("the stamp is at", self.report_audit(repo))

    def test_audit_report_ignores_another_features_stamp(self):
        """Audit report ignores another features stamp"""
        repo = self.make()
        path = os.path.join(repo.root, ".git", "factory-ready")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("%s\nother-feature\n2026-11-07T10:00:00\n" % repo.head())
        repo.write(".scratch/feat/report.md", "# Report\n\n- Built tip: 1234567\n")
        out = repo.gate("audit", "feat", "--report", ".scratch/feat/report.md")[1]
        self.assertIn("the stamp is for other-feature", out)
        self.assertNotIn("but the built-tip stamp is", out)


class AuditScope(unittest.TestCase):
    def test_audit_does_not_cite_another_feature_s_merge(self):
        """Audit does not cite another feature's merge"""
        repo, mine, theirs = two_feature_line()
        code, out = repo.gate("audit", "feat")
        self.assertNotIn(theirs[:7], out)
