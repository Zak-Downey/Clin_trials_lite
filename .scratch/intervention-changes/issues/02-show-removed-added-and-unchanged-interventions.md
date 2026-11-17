# 02: Show Removed, Added and Unchanged on an interventions change

**What to build:** On the trial page's Changes tab, an interventions change names what moved instead of repeating both lists:

```
Interventions
  Removed    Carfilzomib
  Added      None
  Unchanged  6 interventions   [Show]
```

Removed and Added are always both shown, an empty side reading "None". The unchanged interventions are counted, and their names open and close behind a keyboard-reachable "Show" / "Hide" button; when nothing is unchanged the line reads "None" with no button. Names match by exact text and keep the registry's wording; added and unchanged follow the new record's order, removed the previous record's. "Removed" and "Added" are words; red and green only support them. Changes detected before this ships, and simulated changes, are drawn the same way. Every other field's change, the History tab, the change summary and its export are unchanged. Spec: `.scratch/intervention-changes/spec.md`, user stories 1–16 and 19–26, and its Implementation and Testing Decisions.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] After a simulated removal of Carfilzomib from NCT03412565, the interventions change reads "Removed Carfilzomib", "Added None", "Unchanged 6 interventions"
- [ ] The six unchanged names are hidden until "Show" is pressed (by keyboard in the walk), and "Hide" folds them again
- [ ] An addition lists the name under Added with Removed "None"; a swap lists each name on its own side
- [ ] Empty to filled lists every name under Added; filled to empty lists every name under Removed; a full replacement shows Unchanged "None" with no button
- [ ] A renamed intervention shows as one removed and one added
- [ ] The trial API carries added, removed and unchanged on an interventions change only, and keeps the previous and current text on every change
- [ ] The "Simulated changes" label and marking as reviewed work as before
- [ ] An enrolment or date change on the same page still shows Previously / Now; History, change summary and export are unchanged
- [ ] The card fits both supported window sizes without sideways scrolling
- [ ] Unit tests for the split, an API test through the `api` fixture, and a trial page walk, each red before the fix
