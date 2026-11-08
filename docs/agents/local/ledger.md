# Ledger: what escaped, what each gate found, what it cost

The workflow's own measurements for this repo. Without them, nobody can say which gate earns its cost or which rule can be cut. Agents add rows as `evidence.md` and their role files say; the user reads this at a retro.

## Escapes

A defect found after its ticket merged. One row each, added by whoever fixes it, on the day.

| ID | Date | Feature | Defect | Found by | Should have been found by | Change made |
|---|---|---|---|---|---|---|

### escapes.jsonl

Each Escapes row has a line in `docs/agents/local/escapes.jsonl`, written by `gate.py ledger add`, which prints the row to paste here with its `E-NNN` id as the first cell. `gate.py ledger check` joins the two and refuses a row without a line.

## Builds

One row per build, written by `gate.py close`.

| Feature | Dates | Tickets | Per-ticket review: blocking / notes / mutants survived | Exploration: defects | Whole-branch review: blocking / sweep / design / nit | Found by the user | Subagents by role and model | Merger subagents | Guard refusals |
|---|---|---|---|---|---|---|---|---|---|

## Recurring findings

A class of review finding seen more than once. The review merger adds rows and proposes a rule; adopting it is the user's.

| Class | Seen in | Rule proposed | Adopted |
|---|---|---|---|
