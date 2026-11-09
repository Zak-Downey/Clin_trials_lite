"""Every guard rule shown to refuse, and the nearest innocent command shown to pass.

Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
# guard-unchanged: these tests and guard_bash.py are the hardened copy's, taken over with this line and the folder named in the docstring changed.
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import guard_bash  # noqa: E402

GUARD = os.path.join(os.path.dirname(HERE), "guard_bash.py")


def git(cwd, *args):
    subprocess.run(["git", "-C", cwd, "-c", "user.name=t", "-c", "user.email=t@example.com"] + list(args),
                   check=True, capture_output=True)


def make_repo(branch="feature/x"):
    repo = tempfile.mkdtemp(prefix="guard-test-")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "commit", "-q", "--allow-empty", "-m", "first")
    if branch != "main":
        git(repo, "checkout", "-q", "-b", branch)
    return repo


def rule(command, cwd=None, subagent=False, platform="darwin", background=False):
    os.environ["FACTORY_GUARD_PLATFORM"] = platform
    os.environ.pop("CLAUDE_PROJECT_DIR", None)
    data = {"tool_name": "Bash", "cwd": cwd or tempfile.gettempdir(),
            "tool_input": {"command": command, "run_in_background": background}}
    if subagent:
        data["agent_id"] = "a1"
        data["agent_type"] = "implementer"
    refusal = guard_bash.decide(data)
    return refusal.rule if refusal else None


class Refused(unittest.TestCase):
    def test_kill_by_name(self):
        """Killing a process by name is refused"""
        for command in ["pkill -f chrom", "killall node", "echo hi; pkill x", "sudo pkill x",
                        "echo $(pkill x)", "echo `pkill x`", "bash -c 'pkill -f chrom'",
                        "pgrep -f chrom | xargs kill", "kill $(pgrep node)", "FOO=1 pkill x",
                        "cd walks && npm run walk\npkill -f chrom", "echo \"it's\" ' ; pkill x",
                        "cat <<EOF > notes.md\nsome text\nEOF\npkill -f chrom",
                        "{ pkill -f chrom; }", "if true; then pkill x; fi", "for p in a b; do killall $p; done",
                        "kill \"$(pgrep -f vite)\"", "kill `pgrep node`", "ps aux | grep chrom | awk '{print $2}' | xargs kill",
                        "echo \"$(pkill x)\"", "pgrep -f chrom |\\\n  xargs kill -9"]:
            self.assertEqual(rule(command), "kill-by-name", command)

    def test_hook_bypass(self):
        """Bypassing a git hook is refused"""
        for command in ["git commit --no-verify -m x", "git commit -n -m x", "git commit -nm x",
                        "git commit -anm x", "git push --no-verify", "git merge --no-verify b",
                        "git -c core.hooksPath=/dev/null commit -m x", "git config core.hooksPath /dev/null",
                        "git config --unset core.hooksPath", "git -C ../x commit --no-verify -m y",
                        "git commit -m x \\\n  --no-verify", "if ! git commit -m x; then git commit -n -m x; fi"]:
            self.assertEqual(rule(command), "hook-bypass", command)

    def test_stash(self):
        """Git stash is refused"""
        for command in ["git stash", "git stash push -m wip", "git stash -u", "git stash pop", "git add . && git stash",
                        "if test -n \"$dirty\"; then git stash; fi"]:
            self.assertEqual(rule(command), "stash", command)

    def test_sed_in_place(self):
        """Sed in place without a backup suffix is refused"""
        for command in ["sed -i 's/a/b/' f", "sed -i -e 's/a/b/' f", "sed -Ei 's/a/b/' f", "sed --in-place 's/a/b/' f",
                        "sed -i'' 's/a/b/' f", "find . -name '*.md' | xargs sed -i 's/a/b/'",
                        "for f in a b; do sed -i 's/a/b/' \"$f\"; done", "find . -name '*.md' -exec sed -i 's/a/b/' {} +"]:
            self.assertEqual(rule(command, platform="darwin"), "sed-in-place", command)
        self.assertEqual(rule("sed -i '' 's/a/b/' f", platform="linux"), "sed-in-place")

    def test_push(self):
        """A force push and a push to a protected branch are refused"""
        repo = make_repo()
        for command in ["git push --force", "git push -f origin feature/x", "git push --force-with-lease",
                        "git push origin +feature/x", "git push --mirror", "git push -fu origin feature/x",
                        "git push \\\n  --force origin feature/x"]:
            self.assertEqual(rule(command, cwd=repo), "force-push", command)
        for command in ["git push origin main", "git push origin feature/x:main", "git push origin HEAD:refs/heads/main",
                        "git push --all"]:
            self.assertEqual(rule(command, cwd=repo), "protected-branch", command)
        on_main = make_repo(branch="main")
        self.assertEqual(rule("git push", cwd=on_main), "protected-branch")
        self.assertEqual(rule("git push origin HEAD", cwd=on_main), "protected-branch")
        self.assertEqual(rule("git merge feature/x", cwd=on_main), "protected-branch")
        self.assertEqual(rule("cd %s && git merge feature/x" % on_main), "protected-branch")
        self.assertEqual(rule("git checkout main && git merge feature/x", cwd=repo), "protected-branch")
        self.assertIsNone(rule("(cd %s && git status); git merge ticket/07-x" % on_main, cwd=repo))
        self.assertEqual(rule("git switch main; git push", cwd=repo), "protected-branch")
        self.assertEqual(rule("gh pr merge 3 --squash", cwd=repo), "protected-branch")

    def test_pull_request(self):
        """A pull request is opened as a draft and readied only on a stamped tip"""
        repo = make_repo()
        self.assertEqual(rule("gh pr create --title x --body y", cwd=repo), "draft-first")
        self.assertEqual(rule("gh pr ready 3", cwd=repo), "ready-gate")
        # a stamp for another commit does not pass
        stamp = os.path.join(repo, ".git", "factory-ready")
        with open(stamp, "w") as handle:
            handle.write("0000000000000000000000000000000000000000\nfeature\n")
        self.assertEqual(rule("gh pr ready", cwd=repo), "ready-gate")

    def test_subagent(self):
        """A subagent may not push, open a pull request or run in the background"""
        repo = make_repo()
        self.assertEqual(rule("npm test", subagent=True, background=True), "subagent-background")
        self.assertEqual(rule("git push origin feature/x", cwd=repo, subagent=True), "subagent-push")
        self.assertEqual(rule("gh pr create --draft", cwd=repo, subagent=True), "subagent-push")
        self.assertEqual(rule("gh pr ready", cwd=repo, subagent=True), "subagent-push")


ORCHESTRATOR_VERBS = ("dispatch 01 implementer --agent a1", "resume 01 implementer", "foundation-read 01 --agent a1", "review-wave 1",
                      "spec-against-brief .scratch/feat/reviews/00.md", "merge-start 01 abc1234", "merge-end 01 abc1234", "merge-abort 01 2026-11-08T10:00:00 why", "decided 1 abc1234", "observation 'x'", "note 'x'")


class LogVerbs(unittest.TestCase):
    GATE = "python3 .claude/factory/gate.py"

    def test_a_subagent_cannot_write_the_orchestrator_s_log_verbs(self):
        """A subagent cannot write the orchestrator's log verbs"""
        for verb in ORCHESTRATOR_VERBS:
            command = "%s log feat %s" % (self.GATE, verb)
            self.assertEqual(rule(command, subagent=True), "subagent-log", command)
            self.assertIsNone(rule(command), command)  # the main session may
        self.assertEqual(rule("%s open feat 'an item'" % self.GATE, subagent=True), "subagent-log")
        self.assertIsNone(rule("%s open feat 'an item'" % self.GATE))
        self.assertEqual(rule("cd x && python3 -B .claude/factory/gate.py log feat note 'x' > /dev/null", subagent=True), "subagent-log")
        refusal = guard_bash.decide({"tool_name": "Bash", "agent_id": "a1", "cwd": tempfile.gettempdir(),
                                     "tool_input": {"command": "%s log feat note x" % self.GATE}})
        self.assertIn("report", refusal.message)
        for verb in guard_bash.ORCHESTRATOR_LOG_VERBS:
            self.assertIn(verb, refusal.message)
        self.assertEqual(set(guard_bash.ORCHESTRATOR_LOG_VERBS), {v.split()[0] for v in ORCHESTRATOR_VERBS} | {"open"})

    def test_the_guards_orchestrator_verbs_are_the_logs_verbs_but_report(self):
        """The guard's orchestrator verbs are the log's verbs but report"""
        from gate.log import LOG_USAGE
        self.assertEqual(set(LOG_USAGE) - {"report"}, set(guard_bash.ORCHESTRATOR_LOG_VERBS))

    def test_a_subagent_can_write_report(self):
        """A subagent can write report"""
        self.assertIsNone(rule("%s log feat report 06 implementer" % self.GATE, subagent=True))
        self.assertIsNone(rule("%s log feat" % self.GATE, subagent=True))
        self.assertIsNone(rule("%s log feat --agents" % self.GATE, subagent=True))
        self.assertIsNone(rule("%s ticket feat 06" % self.GATE, subagent=True))
        self.assertIsNone(rule("echo gate.py log feat note x", subagent=True))


class Allowed(unittest.TestCase):
    def test_mentions_are_not_commands(self):
        """A refused word only mentioned in text is not a command"""
        for command in ["git commit -m 'never pkill by name'", "grep -rn pkill docs", "echo 'git stash is banned'",
                        "git commit -m \"walkers don't --no-verify\"", "git commit -m '--no-verify'",
                        "git log --grep=stash", "cat <<'EOF' > notes.md\npkill -f chrom\ngit stash\nEOF",
                        "# pkill -f chrom\necho done", "rg 'sed -i' docs", "kill 4242", "kill $pid; wait $pid",
                        "git commit -m 'unbalanced \" quote in message'",
                        "kill $SERVER_PID; sleep 1; pgrep -f server.js || echo stopped", "pgrep -lf node; kill 4242",
                        "pgrep -f server.js | head -1", "grep -q ready log.txt || echo 4242 | xargs kill", "ps aux | grep node | wc -l", "kill \"$pid\" 2>/dev/null || true",
                        "for f in a b; do echo $f; done", "git commit -m\"renaming things\"", "git commit -uno -m x",
                        "# don't worry about this line\ngit commit -m 'mentions --no-verify here'"]:
            self.assertIsNone(rule(command), command)

    def test_right_forms(self):
        """The right form of each refused command passes"""
        repo = make_repo()
        for command in ["sed -i '' 's/a/b/' f", "sed -i.bak 's/a/b/' f", "sed -n '1,5p' f", "sed 's/a/b/' f > g",
                        "git stash list", "git stash show -p", "git config --get core.hooksPath", "git config core.hooksPath",
                        "git commit -m x", "git commit -am 'narrow n'", "git commit --amend --no-edit",
                        "git merge --no-ff --no-commit ticket/07-x", "git merge --abort", "git push -n origin feature/x",
                        "git push origin feature/x", "git push -u origin feature/x", "git push",
                        "gh pr create \\\n  --draft \\\n  --title x --body y", "git checkout -b ticket/09-new main && git merge ticket/08-x",
                        "(cd /tmp && git status); git merge ticket/07-x",
                        "gh pr create --draft --title x --body y", "gh pr ready --undo", "gh pr checks 3 --watch",
                        "gh pr view 3", "gh run list --commit abc --status success"]:
            self.assertIsNone(rule(command, cwd=repo), command)
        self.assertIsNone(rule("sed -i 's/a/b/' f", platform="linux"))
        self.assertIsNone(rule("npm test", background=True))  # the orchestrating session may
        self.assertIsNone(rule("npm test", subagent=True))

    def test_ready_passes_on_a_stamped_tip(self):
        """Ready passes on a stamped tip"""
        repo = make_repo()
        head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        with open(os.path.join(repo, ".git", "factory-ready"), "w") as handle:
            handle.write(head + "\nfeature\n")
        self.assertIsNone(rule("gh pr ready", cwd=repo))
        git(repo, "commit", "-q", "--allow-empty", "-m", "one more")
        self.assertEqual(rule("gh pr ready", cwd=repo), "ready-gate")

    def test_other_tools_and_bad_input(self):
        """Other tools and bad input"""
        self.assertIsNone(guard_bash.decide({"tool_name": "Edit", "tool_input": {"file_path": "x"}}))
        self.assertIsNone(guard_bash.decide({"tool_name": "Bash"}))


class AsAHook(unittest.TestCase):
    """The script as Claude Code runs it: JSON on stdin, exit code and stderr out."""

    def run_hook(self, payload, cwd):
        env = dict(os.environ, FACTORY_GUARD_PLATFORM="darwin")
        return subprocess.run([sys.executable, GUARD], input=payload, capture_output=True, text=True, cwd=cwd, env=env)

    def test_exit_codes_and_log(self):
        """Exit codes and log"""
        repo = make_repo()
        blocked = self.run_hook(json.dumps({"tool_name": "Bash", "cwd": repo, "agent_id": "a", "agent_type": "exploratory-walker",
                                            "tool_input": {"command": "pkill -f chrom"}}), repo)
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("kill-by-name", blocked.stderr)
        with open(os.path.join(repo, ".git", "factory", "guard.log")) as handle:
            record = json.loads(handle.readline())
        self.assertEqual((record["rule"], record["agent"]), ("kill-by-name", "exploratory-walker"))
        allowed = self.run_hook(json.dumps({"tool_name": "Bash", "cwd": repo, "tool_input": {"command": "ls"}}), repo)
        self.assertEqual((allowed.returncode, allowed.stderr), (0, ""))

    def test_a_broken_call_lets_the_command_run(self):
        """A broken call lets the command run"""
        self.assertEqual(self.run_hook("not json", tempfile.gettempdir()).returncode, 0)

    def test_protected_branches_come_from_config(self):
        """Protected branches come from config"""
        repo = make_repo(branch="release")
        os.makedirs(os.path.join(repo, "docs", "agents", "local"))
        with open(os.path.join(repo, "docs", "agents", "local", "factory.json"), "w") as handle:
            json.dump({"protected_branches": ["release"]}, handle)
        env = dict(os.environ, CLAUDE_PROJECT_DIR=repo)
        result = subprocess.run([sys.executable, GUARD], capture_output=True, text=True, env=env, input=json.dumps(
            {"tool_name": "Bash", "cwd": repo, "tool_input": {"command": "git push"}}))
        self.assertEqual(result.returncode, 2)
        self.assertIn("protected-branch", result.stderr)


if __name__ == "__main__":
    unittest.main()
