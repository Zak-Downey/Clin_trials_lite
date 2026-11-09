"""The factory gate: reads the local Markdown tracker and decides, mechanically,
what an agent used to decide by memory.

  gate.py features                 the features in the tracker
  gate.py frontier <feature>       what is ready, in flight, held, blocked, done
  gate.py boxes <feature> [NN]     audit acceptance boxes (all tickets, or one)
  gate.py ticket <feature> <NN>    may this ticket be marked done? Reads the ticket's boxes and,
                                   when it exists, <feature>/reviews/<NN>.md: a blocking finding
                                   must end `| fixed — test: <title> — red: <file>` (or walk:/doc:)
                                   or `| unreachable — run: <file>`, never open or left
  gate.py red <feature> <NN> <check>  run the named check now and keep its output as
                                   <feature>/red/<NN>-<check>-<tip>.txt, `# tip <hash>` first: the
                                   file a box cites as `red: <file>` for a new check
  gate.py mutate <feature> <NN>    mutation-test the ticket's changed files (run in its worktree, tree committed):
                                   the repo's mutate_command over changed files under mutate_paths, report to <feature>/reviews/<NN>-mutants.json,
                                   survivors split into changed lines and elsewhere, `not mutated:` lines for the reviewer's
                                   hand sample; `ticket` refuses a survivor in a changed line or a stale/missing report
  gate.py merge <feature> <NN> <branch> [--follow-up]  the merger's mechanical steps, run in the integration worktree:
                                   clean tree check, merge --no-ff --no-commit, checks, ticket gate, mark
                                   done and commit `Merge ticket NN: <title>`; logs merge-start/merge-end.
                                   Exit 1 on a conflict (merge left open) or aborts (red check, refusal).
                                   --follow-up: the fix after merge of a done ticket, committed `Merge ticket NN follow-up:
                                   <title>` with the Status left as it was; a done ticket is not merged without it
  gate.py release <feature>        move the spec and its needs-triage tickets to ready-for-agent; refuses a
                                   branch not cut from the protected tip, a user-facing spec without
                                   acceptance-walk and exploration tickets, no foundational ticket, an unread brief
  gate.py config [--keys]          validate factory.json against schema.json and print the effective configuration;
                                   --keys lists every key with its type, default and meaning. checks, ready,
                                   merge and release run the validation first and refuse on a problem
  gate.py lint                     the repo's forbidden patterns (factory.json "forbid")
  gate.py checks [--only <name>]   lint, then every check in factory.json (or just the one
                                   named), output to files
  gate.py ready <feature> [more]   the ready gate: tree, tickets, boxes, lint, checks;
                                   stamps the tip when everything passes. Name the
                                   review-fix feature too when there is one
  gate.py handover <feature> [more]  the reduced checklist that goes to the user
  gate.py log <feature> <verb> ...  (a feature has a spec.md) append `<ISO time> <verb> <args>` to the build log:
                                   dispatch <NN> <role> --agent <id> [--follow-up] | report <NN> <role> | resume <NN> <role> |
                                   foundation-read <NN> --agent <id> | review-wave <n> | spec-against-brief <path> |
                                   merge-start <NN> <tip> | merge-end <NN> <result> | observation "<text>" | note "<text>"
                                   (an unknown verb is a usage error); no verb prints the tail, --agents the agent ids
  gate.py open <feature> "<item>"  append a numbered item to the spec's `## Open list` and log it
  gate.py close <feature> [more] [--collect]  after `ready` stamped the built tip: audit, records, the Facts block,
                                   the worktree remove commands
  gate.py ready <feature> [more] --records <Y>  re-stamp the close commit Y when it touches records alone
  gate.py audit <feature> [more] [--report <file>]  after the fact: the build log (in its grammar) and the git history
                                   against the loop's rules, one line per rule: ok, a violation, or `expected and did
                                   not find: <line>`; with --report, the report's hashes, built tip and counts too.
                                   `close` runs it first; `ready --records` runs it on the committed report
  gate.py dashboard [<out.html>] [--sample]  write the dashboard page (default <git dir>/factory/dashboard.html);
                                   --sample draws it from invented figures, labelled as such
  gate.py github [--year YYYY --month MM]  record this repository's GitHub Actions usage for a month
                                   (default the current one) and its artifact and cache storage
  gate.py stats --write <feature> [more]  write the tokens record for features already closed
  gate.py stats                    each build log's first and last time; which guard rules have fired, and for whom;
                                   escapes per build by gate, the misclass count, tokens per role (read from the
                                   subagent transcripts) per finding and per missed escape. Judges nothing
  gate.py ledger check             every prose row of the ledger's Escapes table has a line in escapes.jsonl and back
  gate.py ledger add --feature <f> --class <c> --found-by <g> --should-have-been <g> --defect "<text>" [...]
                                   write the escapes.jsonl line and print the prose row to paste

The rules that judge merged work are listed one per line in .claude/factory/RULES (see gate/__init__.py).

Exit 0: passed. Exit 1: something is wrong, listed one per line. Exit 2: usage.

Run it in the integration worktree (or, for `ticket`, in the ticket's own): it
reads the tree it is run in, and the ready stamp belongs to that worktree.

A ticket is one file, <tracker>/<feature>/issues/NN-<slug>.md, with these lines
above its `## Comments` heading (bold or plain):

  Status: ready-for-agent | needs-info | needs-triage | ready-for-human | wontfix | done
  Blocked by: None | 03 | 01, 04 | 01 to 10, 12
  Kind: foundational | walk-tooling | acceptance-walk | exploration | ready-for-human | design (optional;
        never read for ordering)
  Touches: shared files or folders it will change, comma-separated; `*` to run alone;
           `none` when it changes no shared file

and acceptance boxes, each ending with its evidence once it has some:

  - [x] Text of the box — test: title of the test; walk: title of the walk check
  - [ ] Text of the box — needs-human: what to judge, and on which screenshot

Evidence kinds: test, walk, doc, check, shot, red, needs-human. A ticked box needs at
least one of test, walk, doc, check, shot (`red:` only backs a `test:` or `walk:`). An unticked box needs needs-human, or it is open.
`test:` and `walk:` titles must be found in the folders factory.json names;
`doc:` paths must exist; `check:` must name a configured check.

Rules for all of this: docs/agents/tickets.md and docs/agents/evidence.md.
Python 3.9+, standard library only.
"""
from __future__ import annotations

import os

from gate.audit import cmd_audit
from gate.checks import cmd_checks, cmd_lint, cmd_red
from gate.dashboard import cmd_dashboard
from gate.config import cmd_config, load_config, refusals
from gate.evidence import Resolver, cmd_boxes, cmd_ticket
from gate.frontier import cmd_frontier
from gate.git import find_root
from gate.github import cmd_github
from gate.ledger import cmd_ledger, cmd_stats
from gate.log import cmd_log, cmd_open
from gate.merge import cmd_merge
from gate.mutate import cmd_mutate
from gate.ready import cmd_close, cmd_handover, cmd_ready, cmd_ready_records
from gate.release import cmd_release
from gate.refuse import refuse
from gate.tokens import cmd_stats_write
from gate.tracker import Feature, list_features, tracker_dir


def main(argv: list) -> int:
    if len(argv) < 2 or argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return 2
    command = argv[1]
    root = find_root()
    try:
        config = load_config(root)
    except ValueError as error:
        return refuse("config-json", "factory.json is not valid JSON (%s)" % error, "valid JSON in docs/agents/local/factory.json")
    if command == "config":
        return cmd_config(root, argv[2:])
    if command in ("checks", "ready", "merge", "release", "red", "ticket", "mutate", "lint", "frontier", "boxes", "handover", "audit", "close", "features", "log", "open", "dashboard") and not (command == "dashboard" and "--sample" in argv):
        problems = refusals(root)
        if problems:
            for problem in problems:
                print("factory.json: %s" % problem)
            return refuse("config-valid", "%s found docs/agents/local/factory.json invalid" % command, "the problems printed above fixed (gate.py config lists them)")
    if command == "features":
        for name in list_features(root, config):
            print(name)
        return 0
    if command == "lint":
        problems = cmd_lint(root, config)
        for problem in problems:
            print(problem)
        print("lint: %s" % ("clean" if not problems else "%d problem(s)" % len(problems)))
        return 1 if problems else 0
    if command == "checks":
        if len(argv) > 2 and (argv[2] != "--only" or len(argv) != 4):
            print("gate: usage: checks [--only <name>]")
            return 2
        return cmd_checks(root, config, argv[3] if len(argv) == 4 else None)
    if command == "stats":
        if len(argv) == 2:
            return cmd_stats(root, config)
        if argv[2] != "--write":
            print("gate: usage: stats [--write <feature> [more]]")
            return 2
        names = argv[3:]
        if not names:
            print("gate: usage: stats --write <feature> [more]")
            return 2
        for name in names:
            if os.path.normpath(name) != name or os.sep in name or not os.path.isfile(os.path.join(root, tracker_dir(config), name, "spec.md")):
                return refuse("known-feature", "%s is not a feature (no %s/spec.md)" % (name, os.path.join(tracker_dir(config), name)), "one of the features here: %s" % (", ".join(list_features(root, config)) or "none"), 2)
        return cmd_stats_write(root, config, names)
    if command == "dashboard":
        rest = argv[2:]
        sample = "--sample" in rest
        paths = [a for a in rest if a != "--sample"]
        if len(paths) > 1 or any(a.startswith("-") for a in paths):
            print("gate: usage: dashboard [<out.html>] [--sample]")
            return 2
        return cmd_dashboard(root, config, paths[0] if paths else None, sample)
    if command == "github":
        rest = argv[2:]
        year = month = None
        if rest:
            if len(rest) != 4 or rest[0] != "--year" or rest[2] != "--month" or not rest[1].isdigit() or not rest[3].isdigit() or not 1 <= int(rest[3]) <= 12:
                print("gate: usage: github [--year YYYY --month MM]")
                return 2
            year, month = int(rest[1]), int(rest[3])
        return cmd_github(root, config, year, month)
    if command == "ledger":
        return cmd_ledger(root, argv[2:])
    if command in ("log", "open"):
        if len(argv) < 3:
            return refuse("feature-given", "%s was given no feature" % command, "%s <feature>%s" % (command, " <verb> <arguments> (or --agents)" if command == "log" else " \"<item>\""), 2)
        if os.path.normpath(argv[2]) != argv[2] or os.sep in argv[2] or not os.path.isfile(os.path.join(root, tracker_dir(config), argv[2], "spec.md")):
            return refuse("known-feature", "%s is not a feature (no %s/spec.md)" % (argv[2], os.path.join(tracker_dir(config), argv[2])), "one of the features here: %s" % (", ".join(list_features(root, config)) or "none"), 2)
        if command == "open":
            if len(argv) != 4:
                print("gate: usage: open <feature> \"<item>\"")
                return 2
            return cmd_open(root, config, argv[2], argv[3])
        return cmd_log(root, argv[2], argv[3:])
    if command == "red":
        if len(argv) != 5:
            print("gate: usage: red <feature> <NN> <check>")
            return 2
        return cmd_red(root, config, argv[2], argv[3], argv[4])
    if command == "mutate":
        if len(argv) != 4 or not os.path.isfile(os.path.join(root, tracker_dir(config), argv[2], "spec.md")):
            print("gate: usage: mutate <feature> <NN>")
            return 2
        return cmd_mutate(root, config, argv[2], argv[3])
    if command == "merge":
        follow_up = "--follow-up" in argv[2:]
        rest = [a for a in argv[2:] if a != "--follow-up"]
        if len(rest) != 3:
            print("gate: usage: merge <feature> <NN> <branch> [--follow-up]")
            return 2
        return cmd_merge(root, config, rest[0], rest[1], rest[2], follow_up)
    if command == "audit":
        rest, report = argv[2:], None
        if "--report" in rest:
            at = rest.index("--report")
            if at != len(rest) - 2 or not os.path.isfile(rest[at + 1]):
                print("gate: usage: audit <feature> [more] [--report <file>] (the report must exist)")
                return 2
            report = os.path.abspath(rest[at + 1])
            rest = rest[:at]
        if not rest or any(not os.path.isfile(os.path.join(root, tracker_dir(config), n, "spec.md")) for n in rest):
            print("gate: usage: audit <feature> [more] [--report <file>]")
            return 2
        return cmd_audit(root, config, rest, report)
    if command == "close":
        rest = [a for a in argv[2:] if a != "--collect"]
        if not rest or any(not os.path.isfile(os.path.join(root, tracker_dir(config), n, "spec.md")) for n in rest):
            print("gate: usage: close <feature> [<review-fix feature>] [--collect]")
            return 2
        return cmd_close(root, config, [Feature(root, config, n) for n in rest], "--collect" in argv)
    if command not in ("frontier", "boxes", "ticket", "ready", "handover", "release"):
        return refuse("known-command", "%s is not a command" % command, "one of the commands in `gate.py help`", 2)
    if len(argv) < 3:
        return refuse("feature-given", "%s was given no feature" % command, "%s <feature>, one of: %s" % (command, ", ".join(list_features(root, config)) or "none"), 2)
    feature = Feature(root, config, argv[2])
    resolver = Resolver(root, config)
    if command == "frontier":
        return cmd_frontier(feature)
    if command == "release":
        return cmd_release(root, config, feature)
    if command == "boxes":
        return cmd_boxes(feature, resolver, argv[3] if len(argv) > 3 else None)
    if command == "ticket":
        if len(argv) < 4:
            return refuse("ticket-given", "ticket was given no ticket number", "ticket <feature> <NN>", 2)
        return cmd_ticket(feature, resolver, argv[3])
    if command == "ready" and "--records" in argv:
        at = argv.index("--records")
        if at != len(argv) - 2:
            print("gate: usage: ready <feature> [more] --records <commit>")
            return 2
        return cmd_ready_records([feature] + [Feature(root, config, name) for name in argv[3:at]], argv[at + 1])
    if command == "ready":
        return cmd_ready([feature] + [Feature(root, config, name) for name in argv[3:]], resolver)
    return cmd_handover([feature] + [Feature(root, config, name) for name in argv[3:]])
