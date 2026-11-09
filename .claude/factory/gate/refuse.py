"""The one place a refusal is worded: `gate: refused by <rule>: <what happened>. Needs: <the input that satisfies it>`."""
from __future__ import annotations


# The rule names a refusal may carry: one name per condition. Add a rule here, with its meaning, before a call names it.
RULES = {
    "close-audit": "close: the audit found violations",
    "close-clean": "close: the working tree is not clean",
    "close-once": "close: the records were already written",
    "close-stamped": "close: this tip is not the stamped built tip",
    "config-json": "factory.json is not valid JSON",
    "config-valid": "factory.json fails the configuration checks",
    "feature-given": "a command that takes a feature was given none",
    "git-repository": "the working directory is not a git repository",
    "known-check": "no check of that name in factory.json",
    "known-command": "not a gate command",
    "known-feature": "no such feature in the tracker",
    "known-ticket": "no such ticket in the feature",
    "ledger-flags": "ledger add: a flag is missing or its value is not allowed",
    "log-agent-id": "log: the agent id is already in the build log",
    "log-grammar": "log: the arguments after a verb do not fit its grammar",
    "log-merge-end": "log: merge-end's result is not a hash or an abort word",
    "log-verb": "log: not a log verb",
    "merge-branch": "merge: the ticket branch does not exist",
    "merge-checks": "merge: a check or the lint is red on the merged tree",
    "merge-commit": "merge: git could not commit the merge",
    "merge-config": "merge: the merged tree's factory.json is invalid",
    "merge-conflict": "merge: the branches conflict and the merge is left open (the merger's trigger)",
    "merge-done": "merge: the ticket is already done and no --follow-up was given",
    "merge-follow-up": "merge: --follow-up was given for a ticket that is not done",
    "merge-git": "merge: git could not merge for a reason other than a conflict",
    "merge-place": "merge: the checkout is not the integration branch with a clean tree",
    "merge-ticket-gate": "merge: the ticket gate refused the merged tree",
    "mutate-base": "mutate: no integration branch or commit to record",
    "mutate-clean": "mutate: uncommitted changes outside the tracker",
    "mutate-config": "mutate: mutate_paths is set without its command or report",
    "mutate-report": "mutate: the run left no report",
    "ready-checks": "ready: a check is red or a walk flaked",
    "ready-problems": "ready: problems listed above, the checks not run",
    "ready-stamp": "ready: the tip could not be stamped",
    "records-report": "ready --records: the report does not name the built tip or fails its audit",
    "records-tip": "ready --records: the built tip or the close ref is not usable",
    "red-tip": "red: there is no commit to record as the tip",
    "release-checks": "release: problems listed above",
    "release-rounds": "release: a second fix feature of one root feature (the review's two rounds are the root's)",
    "release-spec": "release: the feature has no spec.md",
    "release-status": "release: the spec is not needs-triage",
    "ticket-gate": "ticket: the ticket may NOT be marked done",
    "ticket-given": "ticket was given no ticket number",
    "tickets-exist": "the feature has no ticket files",
}


def refusal(rule: str, what: str, needs: str) -> str:
    """The refusal as one line (newlines in the parts are folded to spaces)."""
    parts = [" ".join(str(p).split()) for p in (rule, what, needs)]
    return "gate: refused by %s: %s. Needs: %s" % (parts[0], parts[1].rstrip("."), parts[2])


def refuse(rule: str, what: str, needs: str, code: int = 1) -> int:
    """Prints the refusal and returns the exit code the caller returns."""
    print(refusal(rule, what, needs))
    return code
