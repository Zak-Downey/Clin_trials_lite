"""The merger's mechanical steps (`gate.py merge`)."""
from __future__ import annotations

import os
import re

from gate.checks import cmd_lint, run_checks
from gate.config import load_config, read, red_marker_regex, refusals
from gate.evidence import Resolver, cmd_ticket
from gate.git import run_git, run_text
from gate.log import cmd_log
from gate.refuse import refuse
from gate.tracker import Feature, set_status


def first_failing_line(path: str, marker: str) -> str:
    """The first line of a check's output that carries its red marker: the failing test's name."""
    regex = red_marker_regex({"red_marker": marker})
    for line in read(path).split("\n"):
        if regex.search(line):
            return line.strip()
    return ""


def io_capture(function):
    """(result, printed text) of calling function."""
    import contextlib
    import io
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        result = function()
    return result, buffer.getvalue()


def cmd_merge(root: str, config: dict, feature_name: str, label: str, branch: str, follow_up: bool = False) -> int:
    """The merger's mechanical steps, in the integration worktree. Stops where judgement starts:
    exit 1 with the merge left open on a conflict; aborted on a red check or a refused ticket.
    With `follow_up` the ticket is already done: the fix after merge is committed `Merge ticket NN follow-up: <title>`
    and the ticket's Status stays as it was; without it a done ticket is not merged a second time."""
    feature = Feature(root, config, feature_name)
    ticket = feature.get(label)
    integration = "feature/%s" % feature_name
    _, status = run_text(root, "status", "-sb")
    on_branch = re.match(r"^## (\S+?)(\.\.\.|\s|$)", status.split("\n")[0])
    tip = run_git(root, "rev-parse", "--verify", "-q", "refs/heads/%s^{commit}" % branch)
    open_merge = run_git(root, "rev-parse", "-q", "--verify", "MERGE_HEAD^{commit}")
    resuming = bool(tip) and open_merge == tip
    _, unresolved = run_text(root, "diff", "--name-only", "--diff-filter=U")
    clean = len(status.strip().split("\n")) == 1
    if not on_branch or on_branch.group(1) != integration or not (clean and not open_merge or resuming and not unresolved.strip()):
        print(status.strip())
        return refuse("merge-place", "the checkout is not branch %s with a clean tree (git status -sb above)" % integration, "branch %s checked out and clean, or this branch's own merge with its conflicts resolved" % integration)
    if not tip:
        return refuse("merge-branch", "there is no branch %s" % branch, "an existing ticket branch")
    done = ticket.status.strip().lower() == "done"
    if done and not follow_up:
        return refuse("merge-done", "ticket %s is already done" % ticket.label, "a follow-up: `log %s dispatch %s implementer --agent <id> --follow-up`, then `gate.py merge %s %s %s --follow-up`" % (feature_name, ticket.label, feature_name, ticket.label, branch))
    if follow_up and not done:
        return refuse("merge-follow-up", "--follow-up is for a done ticket and ticket %s is %s" % (ticket.label, ticket.status or "without a status"), "the merge without --follow-up")

    def end(*words):
        cmd_log(root, feature_name, ["merge-end", ticket.label] + list(words))

    cmd_log(root, feature_name, ["merge-start", ticket.label, tip])
    if not resuming:
        code, merged = run_text(root, "merge", "--no-ff", "--no-commit", branch)
        if code != 0:
            _, names = run_text(root, "diff", "--name-only", "--diff-filter=U")
            files = [n for n in names.split("\n") if n.strip()]
            if files:
                print("the merge is left open; these files conflict:")
                for name in files:
                    print("  %s" % name)
                end("conflict")
                return refuse("merge-conflict", "branch %s conflicts with the integration branch in %d file(s), listed above, and the merge is left open" % (branch, len(files)), "the conflicts resolved and staged (the merger agent), then the same gate.py merge command again")
            print(merged.strip())
            run_text(root, "merge", "--abort")
            end("failed")
            return refuse("merge-git", "git could not merge %s (its message is above) and the merge was aborted" % branch, "the branch mergeable by git")

    # The configuration of the merged tree judges the merge: a branch that adds a check, or an evidence folder,
    # is held to it, and the checks it names run.
    problems = refusals(root)
    if problems:
        run_text(root, "merge", "--abort")
        for problem in problems:
            print("factory.json: %s" % problem)
        end("refused")
        return refuse("merge-config", "docs/agents/local/factory.json is invalid in the merged tree and the merge was aborted", "the branch's factory.json valid (gate.py config lists the problems)")
    config = load_config(root)
    feature = Feature(root, config, feature_name)
    ticket = feature.get(label)

    os.environ["WALK_FEATURE"] = feature_name
    reds = []
    problems = lint_problems = cmd_lint(root, config)
    for problem in problems:
        print("lint: %s" % problem)
    problems = problems + run_checks(root, config, None, None, reds)
    if problems:
        run_text(root, "merge", "--abort")
        for name, path, marker in reds:
            print("check %s is red; output: %s" % (name, path))
            failing = first_failing_line(path, marker)
            if failing:
                print("  failing test: %s" % failing)
        end("red", reds[0][0] if reds else ("lint" if lint_problems else "no-checks"))
        return refuse("merge-checks", "a check or the lint is red on the merged tree (above) and the merge was aborted", "every check green and no lint problem on the branch")

    # What the checks wrote under the feature's walks folder belongs to this merge; anything else they changed is named.
    walks = os.path.relpath(os.path.join(feature.dir, "walks"), root)
    if os.path.isdir(os.path.join(root, walks)):
        run_text(root, "add", "-A", "--", walks)
    _, changed = run_text(root, "diff", "--name-only")
    _, untracked = run_text(root, "ls-files", "--others", "--exclude-standard")
    left = [n for n in (changed + "\n" + untracked).split("\n") if n.strip()]
    if left:
        print("merge: the checks left these paths changed, not committed:")
        for name in left:
            print("  %s" % name)

    refused, gate_out = io_capture(lambda: cmd_ticket(Feature(root, config, feature_name), Resolver(root, config), ticket.label))
    if refused != 0:
        run_text(root, "merge", "--abort")
        print(gate_out.rstrip("\n"))
        end("refused")
        return refuse("merge-ticket-gate", "the merge was aborted because the ticket gate refused it (above)", "`gate.py ticket %s %s` passing on the branch" % (feature_name, ticket.label))

    names = []
    if not follow_up:
        names.append(os.path.relpath(ticket.path, root))
        set_status(ticket.path, "done")
        if all(t.status in ("done", "wontfix") for n, t in feature.tickets.items() if n != ticket.number):
            spec = os.path.join(feature.dir, "spec.md")
            set_status(spec, "done")
            names.append(os.path.relpath(spec, root))
        run_text(root, "add", "--", *names)
    subject = "Merge ticket %s%s: %s" % (ticket.label, " follow-up" if follow_up else "", re.sub(r"^\d+\s*[:.-]\s*", "", ticket.title))
    code, committed = run_text(root, "commit", "-q", "-m", subject)
    if code != 0:
        print(committed.strip())
        run_text(root, "merge", "--abort")
        end("failed")
        return refuse("merge-commit", "git could not commit the merge (its message is above) and the merge was aborted", "a commit that git accepts (hooks passing)")
    commit = run_git(root, "rev-parse", "HEAD")
    end(commit)
    print("merge: ticket %s merged. Tip %s" % (ticket.label, commit))
    print("checks: all green" + (" (spec %s closed)" % feature_name if len(names) > 1 else ""))
    return 0
