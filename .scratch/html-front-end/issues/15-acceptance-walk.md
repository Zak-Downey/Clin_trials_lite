# 15: Acceptance walk: the whole journey, keyboard only

**Blocked by:** 14

**Status:** needs-triage

**Touches:** walks/

**Kind:** acceptance-walk

**Spec sections (read these, not this ticket's paraphrase):** End State 4; Testing Decisions › Seam 2, › The stand-in registry.

**What to build:** One end-to-end walk across the whole spec, keyboard only, at 1440 × 900 and 1024 × 768 in Chromium and at 1440 × 900 in WebKit, on an empty database against the stand-in registry. The only step not taken through the page is the stand-in's revise and register switch.

- [ ] Walk: keyboard only, from an empty database: create a watchlist; search; select across two pages; add trials; save the search; check for updates; stand-in revise and register; check for updates again; open the changed trial; review it; undo; review again; add the new match; dismiss one match and restore it; view the summary; copy it; export the CSV
- [ ] The walk passes at 1440 × 900 and 1024 × 768 in Chromium
- [ ] The walk passes at 1440 × 900 in WebKit
- [ ] No console error, failed request or horizontal scroll occurs at any step
- [ ] Walk: every control reached in the journey is a real control with a visible focus ring and a text label, and no state on the way (selected, reviewed, failed) is shown by colour alone (design 14/4)

## Comments
