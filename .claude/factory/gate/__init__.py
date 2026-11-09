"""The factory gate as a package: one module per group of subcommands.

`gate.py` beside this folder is the entry shim; `cli` dispatches, and no other module imports it.

  config    factory.json and its defaults          tracker   tickets, boxes, features, the grammar
  git       git, worktrees, stamps, the rule era   evidence  resolving evidence; ticket, boxes
  frontier  what is ready                          checks    lint, checks, red
  merge     the merger's steps                     release   release
  ready     ready, handover, close                 log       the build log, open, the checklists
  audit     the after-the-fact audit               ledger    ledger add/check, stats
  mutate    mutation testing of changed files

RULES lists the gate rules that judge merged work. A ticket merged before a rule existed is not judged
by it, and the era is read from the `RULES` file the gate shipped with at the merge commit
(`.claude/factory/RULES` in an installed repo; one rule per line).
"""

# A rule that judges merged work more strictly is a new line (for example `red-audit-2`), never a change to what an
# old name means: the era check asks only whether the name was listed at the merge commit, so a stricter rule under an
# old name would judge every earlier ticket by the stricter form.
# The rules that judge merged work, one line each in the RULES file the kit ships. `follow-up` joins from ticket 06.
RULES = ("red-audit", "doc-anchor", "review-grammar", "mutants")

RULES_FILE = ".claude/factory/RULES"

# Fallback for a commit with no RULES file: a gate that was still one file, `.claude/factory/gate.py`
# (a repo's hardened monolith gate, or any build in flight in a repo when it installs this kit), held a rule
# when its source held the text below. Used for that fallback only.
MONOLITH_FILE = ".claude/factory/gate.py"
MONOLITH_MARKERS = {"red-audit": "class RedAudit", "mutants": "def mutant_problems"}
