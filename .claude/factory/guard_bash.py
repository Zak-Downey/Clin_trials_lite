#!/usr/bin/env python3
"""Bash guard: a PreToolUse hook that refuses commands the rule files used to forbid in prose.

Wired in .claude/settings.json for the Bash tool. It runs before every Bash call
of the main session and of every subagent. Exit 0 lets the command run. Exit 2
refuses it, and the text on stderr is what the agent reads.

What it refuses (rule id, then why):

  kill-by-name       pkill / killall, or kill fed by pgrep. Other agents' browsers,
                     and the user's own, match the same name. Stop your own
                     processes by id.
  hook-bypass        --no-verify, `git commit -n`, a changed core.hooksPath.
  stash              git stash (except list / show). Work in progress is a commit.
  sed-in-place       the `sed -i` form that is wrong on this platform
                     (macOS wants `sed -i '' ...`; Linux wants `sed -i ...`).
  force-push         git push --force / -f / --force-with-lease / +refspec / --mirror.
  protected-branch   pushing to, or merging into, a protected branch (main);
                     `gh pr merge`. Merging into main is the user's act.
  draft-first        `gh pr create` without --draft.
  ready-gate         `gh pr ready` on a tip the ready gate has not passed
                     (python3 .claude/factory/gate.py ready <feature>).
  subagent-background  run_in_background from a subagent: each exit wakes the
                     orchestrating session.
  subagent-log       `gate.py log <feature> <verb>` for any verb but `report`, and `gate.py open`, from a
                     subagent: the orchestrating session writes the build log; a subagent writes `report`.
  subagent-push      git push, `gh pr create`, `gh pr ready` from a subagent:
                     pushing and the pull request are the orchestrating session's.

Every refusal is appended to <git common dir>/factory/guard.log (one JSON line),
so a build can count which rules fired: `gate.py stats`.

This is a guard against slips, not a sandbox. It reads the command as text, so a
determined spelling gets past it. If it ever fails itself, it lets the command
run: a broken guard must not stop a build.

Python 3.9+, standard library only.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import time

SEPARATOR_CHARS = set(";|&()\n")
REDIRECT_CHARS = set("<>")
WRAPPERS = {"sudo", "command", "exec", "nohup", "time", "env", "nice", "builtin", "noglob"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
SHELL_KEYWORDS = {"do", "then", "else", "elif", "if", "while", "until", "!", "{", "}", "time"}
NAME_SEARCHES = {"pgrep", "pidof"}
NAME_FILTERS = {"pgrep", "pidof", "grep", "egrep", "fgrep", "rg"}
XARGS_VALUE_FLAGS = {"-I", "-n", "-P", "-L", "-d", "-E", "-s", "-a"}
COMMIT_VALUE_FLAGS = {
    "-m", "-F", "-C", "-c", "-t", "--message", "--file", "--author", "--date",
    "--template", "--reuse-message", "--reedit-message", "--fixup", "--squash",
    "--cleanup", "--pathspec-from-file", "--trailer",
}
PUSH_VALUE_FLAGS = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}
GH_VALUE_FLAGS = {"-R", "--repo"}
DEFAULT_PROTECTED = ["main", "master"]

DOC = "docs/agents/every-agent.md"

# Every log verb a subagent may not write: all of the grammar but `report` (`gate.py` log grammar, orchestrator.md).
# `merge-start` and `merge-end` are written by `gate.py merge`, and `open` by `gate.py open`; none is written by hand.
ORCHESTRATOR_LOG_VERBS = ("dispatch", "resume", "foundation-read", "review-wave", "spec-against-brief",
                          "merge-start", "merge-end", "merge-abort", "decided", "open", "observation", "note")


class Refusal(Exception):
    def __init__(self, rule: str, message: str):
        super().__init__(message)
        self.rule = rule
        self.message = message


# --------------------------------------------------------------------------
# Reading the command

_HEREDOC = re.compile(r"(?<!<)<<(?!<)-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


def strip_heredocs_and_comments(command: str) -> str:
    """Drops here-document bodies and whole-line comments: neither is a command."""
    lines = command.split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if line.lstrip().startswith("#"):
            continue
        out.append(line)
        for match in _HEREDOC.finditer(line):
            end = match.group(2)
            while i < len(lines) and lines[i].strip() != end:
                i += 1
            i += 1  # the terminator line
    return "\n".join(out)


def tokenize(command: str) -> list:
    lex = shlex.shlex(command, posix=True, punctuation_chars=";|&()<>\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""
    return list(lex)


def rough_tokenize(command: str) -> list:
    """Used when the command does not parse (an unbalanced quote): split on
    whitespace and treat the usual separators as separators."""
    spaced = re.sub(r"(\$\(|[;|&()\n`])", r" ; ", command)
    return [t.strip("'\"") for t in spaced.split()]


class Command:
    """One simple command: its words, the separators that came before it, and
    whether it sits inside $( ) or backticks."""

    def __init__(self, words: list, seps: list, substituted: bool):
        self.words = words
        self.seps = seps
        self.substituted = substituted


def simple_commands(tokens: list) -> list:
    """Splits a token list into simple commands, dropping redirections."""
    commands = []
    words = []
    seps = []
    pending = []
    substituted = False

    def close():
        nonlocal words, seps, substituted
        if words:
            commands.append(Command(words, seps, substituted))
        words = []
        seps = pending[:]
        del pending[:]
        substituted = False

    skip_next = False
    for token in tokens:
        if skip_next:
            skip_next = False
            continue
        chars = set(token)
        if token and chars & REDIRECT_CHARS and chars <= (REDIRECT_CHARS | {"&"}):
            skip_next = True  # the redirection's target
            continue
        if token and chars <= SEPARATOR_CHARS:
            dollar = bool(words) and words[-1].endswith("$") and token.startswith("(")
            if dollar:
                words[-1] = words[-1][:-1] + "$()"  # keep a marker that a substitution follows
            pending.append(token)
            close()
            substituted = dollar
            continue
        if token.startswith("`"):
            if words:
                words.append("$()")
            pending.append("`")
            close()
            substituted = True
            token = token.lstrip("`")
            if not token:
                continue
        words.append(token.rstrip("`") if token.endswith("`") and len(token) > 1 else token)
    close()
    return commands


def command_word(words: list):
    """Returns (name, arguments, came through xargs) of a simple command,
    looking through shell keywords, VAR=value prefixes and wrappers such as
    sudo, env, xargs and timeout."""
    through_xargs = False
    i = 0
    while i < len(words):
        word = words[i]
        if word in SHELL_KEYWORDS or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", word):
            i += 1
            continue
        name = os.path.basename(word.lstrip("$({"))
        if name in WRAPPERS:
            i += 1
            while i < len(words) and words[i].startswith("-"):
                i += 1
            continue
        if name in ("timeout", "gtimeout"):
            i += 1
            while i < len(words) and words[i].startswith("-"):
                i += 1
            i += 1  # the duration
            continue
        if name == "xargs":
            through_xargs = True
            i += 1
            while i < len(words) and words[i].startswith("-"):
                i += 2 if words[i] in XARGS_VALUE_FLAGS else 1
            continue
        return name, words[i + 1:], through_xargs
    return None, [], through_xargs


# --------------------------------------------------------------------------
# Git helpers

def git(cwd: str, *args: str):
    try:
        result = subprocess.run(
            ["git", "-C", cwd] + list(args),
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def current_branch(cwd: str, ctx=None):
    """The branch a command would run on: one checked out earlier in the same
    command line if there was one, else the worktree's."""
    if ctx is not None and ctx.get("branch"):
        return ctx["branch"]
    return git(cwd, "symbolic-ref", "--short", "-q", "HEAD")


COMMIT_ATTACHED_VALUE = set("mFCctuSU")  # short flags whose value may be written against them: -m"msg", -uno


def commit_cluster_has_n(flag: str) -> bool:
    """True for -n, -an, -nm; false for -m"renaming" and -uno, where the n is
    part of a value."""
    if flag.startswith("--") or not flag.startswith("-"):
        return False
    for char in flag[1:]:
        if char == "n":
            return True
        if char in COMMIT_ATTACHED_VALUE:
            return False
    return False


def parse_git(args: list):
    """Returns (subcommand, its arguments, -C directory or None, -c settings)."""
    directory = None
    settings = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "-C" and i + 1 < len(args):
            directory = args[i + 1]
            i += 2
            continue
        if arg == "-c" and i + 1 < len(args):
            settings.append(args[i + 1])
            i += 2
            continue
        if arg.split("=")[0] in ("--git-dir", "--work-tree", "--namespace", "--exec-path"):
            i += 1 if "=" in arg else 2
            continue
        if arg.startswith("-"):
            i += 1
            continue
        return arg, args[i + 1:], directory, settings
    return None, [], directory, settings


def flags_without_values(args: list, value_flags: set) -> list:
    """The flag tokens of a git subcommand, skipping the value that follows a
    flag such as -m, so a commit message is never read as a flag."""
    flags = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--":
            break
        if arg in value_flags:
            flags.append(arg)
            i += 2
            continue
        if arg.startswith("-"):
            flags.append(arg)
            # a short cluster ending in a value flag (-am "msg") takes the next word
            if not arg.startswith("--") and len(arg) > 2 and ("-" + arg[-1]) in value_flags:
                i += 2
                continue
        i += 1
    return flags


def positionals(args: list, value_flags: set) -> list:
    found = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in value_flags:
            i += 2
            continue
        if arg.startswith("-") and arg != "-":
            i += 1
            continue
        found.append(arg)
        i += 1
    return found


# --------------------------------------------------------------------------
# The rules

def check_git(args: list, ctx: dict) -> None:
    sub, rest, directory, settings = parse_git(args)
    cwd = ctx["cwd"]
    if directory:
        cwd = os.path.normpath(os.path.join(cwd, os.path.expanduser(directory)))

    if any(s.lower().startswith("core.hookspath") for s in settings):
        raise Refusal("hook-bypass", "`-c core.hooksPath=...` turns the repo's hooks off. Fix what the hook reports instead.")
    if sub is None:
        return

    if sub == "config":
        lowered = [a.lower() for a in rest]
        if "core.hookspath" in lowered:
            key_at = lowered.index("core.hookspath")
            has_value = key_at + 1 < len(rest) and not rest[key_at + 1].startswith("-")
            if has_value or "--unset" in lowered or "unset" in lowered[:key_at]:
                raise Refusal("hook-bypass", "Changing core.hooksPath turns the repo's hooks off. Fix what the hook reports instead.")
        return

    if sub in ("commit", "merge", "push", "rebase", "cherry-pick", "revert", "am", "pull"):
        flags = flags_without_values(rest, COMMIT_VALUE_FLAGS if sub == "commit" else PUSH_VALUE_FLAGS)
        bypass = "--no-verify" in flags
        if sub == "commit":
            bypass = bypass or any(commit_cluster_has_n(f) for f in flags)
        if bypass:
            raise Refusal("hook-bypass", "Never bypass a hook (`--no-verify`, `commit -n`). A hook that fails is a red check: read its output and fix the cause.")

    if sub in ("checkout", "switch"):
        created = [rest[i + 1] for i, a in enumerate(rest[:-1]) if a in ("-b", "-B", "-c", "-C", "--orphan")]
        words = positionals(rest, set())
        if created:
            ctx["branch"] = created[0]
        elif words and "--" not in rest:
            ctx["branch"] = words[0]
        return

    if sub == "stash":
        words = positionals(rest, set())
        if not words or words[0] not in ("list", "show"):
            raise Refusal("stash", "Work in progress is a commit on your branch, squashed or amended later; never a stash. A stash is invisible to the agent that resumes your worktree.")
        return

    if sub == "push":
        if ctx["subagent"]:
            raise Refusal("subagent-push", "Pushing is the orchestrating session's: every push is a billed CI run and goes in a batch (docs/agents/ci-spend.md). Commit locally and report your branch tip.")
        flags = flags_without_values(rest, PUSH_VALUE_FLAGS)
        for flag in flags:
            short_force = not flag.startswith("--") and "f" in flag[1:]
            if flag in ("--force", "--mirror") or short_force or flag.startswith("--force-with-lease") or flag.startswith("--force-if-includes"):
                raise Refusal("force-push", "No forced push: the integration branch is shared and reviewed. If history must change, stop and tell the user.")
            if flag == "--all":
                raise Refusal("protected-branch", "`git push --all` pushes every branch, the protected ones included. Name the branch you mean.")
        words = positionals(rest, PUSH_VALUE_FLAGS)
        refspecs = words[1:]
        targets = []
        for spec in refspecs:
            if spec.startswith("+"):
                raise Refusal("force-push", "A `+refspec` is a forced push. If history must change, stop and tell the user.")
            target = spec.split(":", 1)[1] if ":" in spec else spec
            targets.append(target)
        if not refspecs:
            targets.append("HEAD")
        for target in targets:
            name = target
            if name == "HEAD":
                name = current_branch(cwd, ctx) or ""
            if name.startswith("refs/heads/"):
                name = name[len("refs/heads/"):]
            if name in ctx["protected"]:
                raise Refusal("protected-branch", "`%s` changes only through a reviewed pull request, and merging it is the user's act. Push the feature branch instead." % name)
        return

    if sub == "merge":
        if any(a in ("--abort", "--continue", "--quit") for a in rest):
            return
        branch = current_branch(cwd, ctx)
        if branch and branch in ctx["protected"]:
            raise Refusal("protected-branch", "Merging into `%s` is the user's act. Leave the branch ready and say so." % branch)


def check_sed(args: list, ctx: dict) -> None:
    mac = ctx["platform"] == "darwin"
    for i, arg in enumerate(args):
        if arg == "--in-place" or arg.startswith("--in-place="):
            if mac:
                raise Refusal("sed-in-place", "This machine's sed (macOS) has no `--in-place`. Write `sed -i '' 's/a/b/' file`, or edit with the Edit tool.")
            continue
        if re.match(r"^-(?!-)[A-Za-z]*i$", arg):
            following = args[i + 1] if i + 1 < len(args) else None
            if mac and following != "":
                raise Refusal("sed-in-place", "On macOS `sed -i` takes a backup suffix, so `sed -i 's/a/b/' f` reads the script as the suffix and `f` as the script. Write `sed -i '' 's/a/b/' f` (with the space), or edit with the Edit tool.")
            if not mac and following == "":
                raise Refusal("sed-in-place", "On Linux `sed -i ''` reads the empty string as the script. Write `sed -i 's/a/b/' f`, or edit with the Edit tool.")


def ready_stamp_problem(cwd: str):
    head = git(cwd, "rev-parse", "HEAD")
    stamp_path = git(cwd, "rev-parse", "--git-path", "factory-ready")
    if head is None or stamp_path is None:
        return "this is not a git repository"
    if not os.path.isabs(stamp_path):
        stamp_path = os.path.join(cwd, stamp_path)
    try:
        with open(stamp_path, encoding="utf-8") as handle:
            stamped = handle.readline().strip()
    except OSError:
        return "the ready gate has not passed on this branch"
    if stamped != head:
        return "the ready gate last passed on %s and the tip is now %s" % (stamped[:7], head[:7])
    return None


def check_gh(args: list, ctx: dict) -> None:
    words = positionals(args, GH_VALUE_FLAGS)
    if len(words) < 2 or words[0] != "pr":
        return
    action = words[1]
    if action == "merge":
        raise Refusal("protected-branch", "Merging the pull request is the user's act. Leave it ready and say so.")
    if action in ("create", "ready") and ctx["subagent"]:
        raise Refusal("subagent-push", "Opening a pull request and marking it ready are the orchestrating session's. Report your branch tip instead.")
    if action == "create" and not any(a in ("--draft", "-d") for a in args):
        raise Refusal("draft-first", "Open the pull request as a draft (`gh pr create --draft`): expensive CI jobs skip drafts, and it is marked ready once, through the ready gate.")
    if action == "ready" and "--undo" not in args:
        problem = ready_stamp_problem(ctx["cwd"])
        if problem:
            raise Refusal("ready-gate", "Not marked ready: %s. Run `python3 .claude/factory/gate.py ready <feature>` here; it checks every ticket, every acceptance box and every suite on this tip, and stamps the tip when they pass. Then run this again." % problem)


KILL_BY_NAME = "it matches the other agents' processes and the user's own. Stop only what you started, by the process id you kept when you started it (`$!`, or the child handle), then `kill <pid>`."


def check_kill(index: int, commands: list, parsed: list) -> None:
    """Refuses a kill whose targets come from a search by name."""
    name, args, through_xargs = parsed[index]
    if any(search in arg for arg in args for search in NAME_SEARCHES):
        raise Refusal("kill-by-name", "Killing whatever `pgrep` finds is killing by name: " + KILL_BY_NAME)
    if "$()" in "".join(args) and index + 1 < len(commands) and commands[index + 1].substituted and parsed[index + 1][0] in NAME_SEARCHES:
        raise Refusal("kill-by-name", "Killing whatever `pgrep` finds is killing by name: " + KILL_BY_NAME)
    if through_xargs:
        j = index
        while j > 0 and any("|" in sep for sep in commands[j].seps) and not any(sep in (";", "&&", "||", "\n") for sep in commands[j].seps):
            j -= 1
            if parsed[j][0] in NAME_FILTERS:
                raise Refusal("kill-by-name", "Killing whatever a search by name finds is killing by name: " + KILL_BY_NAME)


def check_gate_log(name: str, args: list, ctx: dict) -> None:
    """A subagent writes the build log's `report` line and nothing else: not another verb, and not `gate.py open`."""
    if not ctx["subagent"]:
        return
    words = [name] + list(args)
    at = None
    if os.path.basename(name) == "gate.py":
        at = 0
    elif re.match(r"^python[\d.]*$", os.path.basename(name)):
        at = next((i for i, w in enumerate(words[1:], 1) if not w.startswith("-")), None)
        at = at if at is not None and os.path.basename(words[at]) == "gate.py" else None
    if at is None:
        return
    rest = words[at + 1:]
    if rest[:1] == ["open"] or (rest[:1] == ["log"] and len(rest) >= 3 and rest[2] in ORCHESTRATOR_LOG_VERBS):
        raise Refusal("subagent-log", "The build log is the orchestrating session's: a subagent writes `gate.py log <feature> report <NN> <role>` and nothing else. "
                      "Not %s, and not `gate.py open`. Put what you would log in your report." % ", ".join("`%s`" % v for v in ORCHESTRATOR_LOG_VERBS))


def check_words(name: str, args: list, ctx: dict, depth: int) -> None:
    check_gate_log(name, args, ctx)
    if name in ("pkill", "killall"):
        raise Refusal("kill-by-name", "`%s` stops every process with that name: %s" % (name, KILL_BY_NAME))
    if name == "git":
        check_git(args, ctx)
    elif name == "sed":
        check_sed(args, ctx)
    elif name == "gh":
        check_gh(args, ctx)
    elif name == "find":
        for i, arg in enumerate(args):
            if arg in ("-exec", "-execdir", "-ok", "-okdir") and i + 1 < len(args):
                inner, inner_args, _ = command_word(args[i + 1:])
                if inner:
                    check_words(inner, inner_args, ctx, depth)
    elif name in SHELLS and depth < 3:
        for i, arg in enumerate(args):
            if re.match(r"^-(?!-)[A-Za-z]*c$", arg) and i + 1 < len(args):
                check_command(args[i + 1], ctx, depth + 1)
                break
    elif name == "eval" and depth < 3:
        check_command(" ".join(args), ctx, depth + 1)
    # a substitution written inside a quoted word, such as "$(pkill x)"
    if depth < 3:
        for arg in args:
            for inner in re.findall(r"\$\(([^()]*)\)", arg) + re.findall(r"`([^`]*)`", arg):
                check_command(inner, ctx, depth + 1)


def check_tokens(tokens: list, ctx: dict, depth: int = 0) -> None:
    commands = simple_commands(tokens)
    parsed = [command_word(command.words) for command in commands]
    cwd_stack = []
    for index, command in enumerate(commands):
        for sep in command.seps:
            for char in sep:
                if char == "(":
                    cwd_stack.append((ctx["cwd"], ctx.get("branch")))
                elif char == ")" and cwd_stack:
                    ctx["cwd"], ctx["branch"] = cwd_stack.pop()
        name, args, _ = parsed[index]
        if name is None:
            continue
        if name == "cd" and len(args) == 1:
            ctx["cwd"] = os.path.normpath(os.path.join(ctx["cwd"], os.path.expanduser(args[0])))
            ctx["branch"] = None
            continue
        if name == "kill":
            check_kill(index, commands, parsed)
        check_words(name, args, ctx, depth)


def check_command(command: str, ctx: dict, depth: int = 0) -> None:
    text = strip_heredocs_and_comments(command.replace("\\\n", " "))
    try:
        tokens = tokenize(text)
    except ValueError:
        tokens = rough_tokenize(text)
    check_tokens(tokens, ctx, depth)


# --------------------------------------------------------------------------
# Entry

def load_protected(project_dir: str) -> list:
    try:
        with open(os.path.join(project_dir, "docs", "agents", "local", "factory.json"), encoding="utf-8") as handle:
            configured = json.load(handle).get("protected_branches")
        if isinstance(configured, list) and configured:
            return [str(b) for b in configured]
    except Exception:
        pass
    return DEFAULT_PROTECTED


def log_refusal(cwd: str, record: dict) -> None:
    try:
        common = git(cwd, "rev-parse", "--git-common-dir")
        if common is None:
            return
        if not os.path.isabs(common):
            common = os.path.join(cwd, common)
        folder = os.path.join(common, "factory")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "guard.log"), "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
    except Exception:
        pass


def decide(data: dict):
    """Returns a Refusal, or None to let the call through."""
    if data.get("tool_name") != "Bash":
        return None
    tool_input = data.get("tool_input") or {}
    command = tool_input.get("command") or ""
    cwd = data.get("cwd") or os.getcwd()
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or cwd
    ctx = {
        "cwd": cwd,
        "subagent": bool(data.get("agent_id")),
        "platform": os.environ.get("FACTORY_GUARD_PLATFORM") or sys.platform,
        "protected": load_protected(project_dir),
    }
    try:
        if ctx["subagent"] and tool_input.get("run_in_background"):
            raise Refusal("subagent-background", "A subagent never uses run_in_background: each exit wakes the orchestrating session. Run the job in the foreground with the Bash tool's `timeout` parameter (up to 600000 ms) and its output written to a file.")
        check_command(command, ctx)
    except Refusal as refusal:
        return refusal
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
        refusal = decide(data)
    except Exception:
        return 0  # a broken guard must not stop a build
    if refusal is None:
        return 0
    log_refusal(data.get("cwd") or os.getcwd(), {
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "rule": refusal.rule,
        "agent": data.get("agent_type") or "main",
        "command": (data.get("tool_input") or {}).get("command", "")[:300],
    })
    sys.stderr.write("Refused by the factory guard (%s). %s\nIf this rule is wrong for the case in hand, do not look for another spelling: report it. Rules: %s\n" % (refusal.rule, refusal.message, DOC))
    return 2


if __name__ == "__main__":
    sys.exit(main())
