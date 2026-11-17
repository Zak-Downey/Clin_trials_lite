# Spec: Show which interventions were added and removed

Status: ready-for-agent

## Problem Statement

When a check for updates detects that a monitored trial's interventions changed, the trial page's Changes tab shows the whole previous list beside the whole new list as comma-joined text: "Previously Daratumumab, Bortezomib, Lenalidomide, Dexamethasone, Melphalan, Prednisone, Carfilzomib" and "Now Daratumumab, Bortezomib, Lenalidomide, Dexamethasone, Melphalan, Prednisone". To find what moved, the analyst compares the two lists name by name. With seven drugs a side that is slow, and a dropped combination partner (competitor intelligence with a short shelf life) is easy to miss.

## Solution

On the Changes tab, an interventions change names what moved instead of repeating both lists:

```
Interventions
  Removed    Carfilzomib
  Added      None
  Unchanged  6 interventions   [Show]
```

The interventions removed and added are each named. A side with nothing on it reads "None". The interventions present before and after are counted, and their names unfold behind "Show". The words "Removed" and "Added" carry the meaning; red and green support them.

A list the sponsor only reordered is not a change, as today. An intervention the registry record names more than once counts once, so a change in how often a name repeats is not a change either.

Every other field's change keeps its Previously / Now layout. The History tab, the change summary and its export keep "old list → new list".

## User Stories

1. As a medical affairs analyst, I want an interventions change to name each intervention that was removed, so that I see a dropped drug without comparing two lists.
2. As an analyst, I want an interventions change to name each intervention that was added, so that I see a new combination partner at a glance.
3. As an analyst, I want the Removed line to read "None" when nothing was removed, so that "nothing was removed" is stated rather than left for me to infer.
4. As an analyst, I want the Added line to read "None" when nothing was added, so that I can tell a pure removal from a swap.
5. As an analyst, I want both lines always present, in the same order (Removed, then Added), so that every interventions change reads the same way and I know where to look.
6. As an analyst, I want a change that both adds and removes interventions to list each name on its own side, so that a swapped drug reads as one out and one in.
7. As an analyst, I want several interventions removed in one check to be listed together under Removed, so that one check reads as one event.
8. As an analyst, I want the unchanged interventions counted ("Unchanged 6 interventions"), so that I can judge how much of the regimen stayed the same.
9. As an analyst, I want the unchanged count to read in the singular for one ("1 intervention"), so that the line reads as a sentence.
10. As an analyst, I want the unchanged names hidden until I ask for them, so that the news is not crowded by what did not move.
11. As an analyst, I want "Show" to reveal the unchanged names and then offer to hide them again, so that I can check the context and fold it away.
12. As a keyboard user, I want "Show" to be a button I can reach and press from the keyboard, so that the unchanged names are not mouse-only.
13. As an analyst, I want the Unchanged line to read "None", with no "Show" button, when every intervention was replaced, so that a fully swapped regimen is unmistakable.
14. As an analyst, I want an intervention list that went from empty to filled to show every name under Added and Removed "None", so that a newly registered regimen reads as additions.
15. As an analyst, I want a list that went from filled to empty to show every name under Removed, so that a withdrawn regimen reads as removals.
16. As an analyst, I want each name to keep the registry's wording and order (added and unchanged in the new record's order, removed in the previous record's order), so that the names match what I would see on ClinicalTrials.gov.
17. As an analyst, I want a list the sponsor only reordered to raise no change at all, so that I am not sent to read a non-event.
18. As an analyst, I want an intervention named more than once in the record (once per arm) to count once, so that a change in repeats alone raises no change with nothing added or removed.
19. As an analyst, I want a renamed intervention (for example "Carfilzomib" becoming "carfilzomib (Kyprolis)") shown as one removed and one added, so that the app never guesses two names are the same drug.
20. As an analyst, I want "Removed" and "Added" written as words, with colour only as support, so that the change reads correctly for a colour-blind reader and in a screenshot pasted into a briefing.
21. As an analyst, I want an interventions change detected before this feature shipped to be shown the same new way, so that older unreviewed changes read like new ones.
22. As an analyst, I want a simulated interventions change to keep its "Simulated changes" label, so that a demonstration is never mistaken for registry news.
23. As an analyst, I want marking the trial as reviewed to work on an interventions change exactly as before, so that the new layout changes nothing about review.
24. As an analyst, I want every other field's change (dates, enrolment, status and the other list fields) to keep its Previously / Now layout, so that only the interventions card changes.
25. As an analyst, I want the History tab, the change summary and its export to read as before, so that briefings I already produce are unchanged.
26. As an analyst, I want the interventions card to fit the page at both supported window sizes without sideways scrolling, so that a long drug name does not break the layout.

## Implementation Decisions

- **One pure function owns the split.** The diffing module gains a function that takes a previous and a current list and returns three lists: added, removed and unchanged. It compares distinct names by exact text. Added and unchanged keep the current list's order; removed keeps the previous list's order. It has no storage, network or display knowledge, like everything else in that module.
- **Which fields are split is one named set.** The diffing module holds the set of fields shown as added/removed, containing only interventions. Another list field (conditions, arm groups, primary outcomes) opts in by joining the set; nothing else changes.
- **Detection agrees with display.** The comparison that decides whether a field moved compares lists by distinct names rather than by sorted contents with repeats. A list whose only difference is how often a name repeats is no longer a change. This is a change to what is detected, and the commit says so. Reordering stays a non-change, as today.
- **The trial page's API carries the split.** The trial endpoint adds an optional `added`, `removed` and `unchanged` (each a list of names) to a change whose field is in the split set. The existing `previous` and `current` text stays in every change, so nothing that reads it breaks. The page draws the three groups and computes nothing.
- **No migration.** Changes are stored with their previous and current lists, so the split is computed when the page is served. Changes already detected are drawn the new way.
- **The page.** On the Changes tab, a change carrying the split draws three labelled lines (Removed, Added, Unchanged) in place of Previously / Now. An empty side reads "None". The unchanged names sit behind a "Show" / "Hide" button (`aria-expanded` kept in step), the pattern the History tab's "Show details" already uses. Red and green reuse the stylesheet's existing colour tokens and work in both themes.
- **Glossary.** No new domain term; an interventions change is a **change** in the glossary's sense.

## Testing Decisions

- **What makes a good test here:** it states what the analyst sees or what the API returns for a given pair of records, never how the split is computed. A test survives a rewrite of the function's insides.
- **Seams (the repo's settled two):** the `api` fixture for the API and the diffing module; a walk for the trial page. No new seam.
- **Diffing module:** unit tests for the split and for detection: added only, removed only, both, reordered (no change), a repeat-count change alone (no change), empty to filled, filled to empty, renamed (one removed, one added), order of each group. Prior art: the interventions tests already in the diff unit suite (an added intervention, a removed one, a reversed list).
- **API:** through the `api` fixture, a simulated removal of Carfilzomib from NCT03412565 serves removed `["Carfilzomib"]`, added `[]` and the six others unchanged, while a non-intervention change on the same trial carries no split. Prior art: the trial-page test in the review API suite that checks how unreviewed changes are grouped by check.
- **Page:** a walk on the trial page: after a simulated change, the interventions card shows "Removed Carfilzomib", "Added None" and "Unchanged 6 interventions"; the six names are hidden until "Show" is pressed by keyboard; an enrolment or date change on the same page still shows Previously / Now. Written red first. Prior art: the trial page walk, and the stand-in registry's "one intervention fewer" record.

## Out of Scope

- The split for any field other than interventions.
- The History tab, the change summary, its export and the briefing text.
- Recognising renames, spelling or case variants as the same intervention.
- Intervention types, arm groups and drug MeSH terms, which keep their own Previously / Now changes.

## Further Notes

- The six layout and wording choices (interventions only; Changes tab only; grouped lists with unchanged folded; both lines always shown; words before colour; exact names) were agreed with the owner on 2026-11-17.
- The owner's example ("Removed: Carfilzomib, Added: None, Unchanged: 6 interventions") is exactly what the developer simulator and the stand-in registry produce on NCT03412565, so the acceptance walk can show it without new fixtures.
- The reference image the owner shared (a side-by-side text diff with added/removed/modified tiles) informed the colours only; a list of drug names has no "modified" line, so there is no modified group.
