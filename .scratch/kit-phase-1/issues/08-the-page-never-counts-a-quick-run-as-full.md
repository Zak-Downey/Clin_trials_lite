# 08: The page never counts a quick run as a full run

**What to build:** The hand-over page treats a quick run as a run of some checks, never as the full run it reports. A quick run after a full one does not replace it as "the last full run". A build whose only runs were quick has no full run, and the page says so in the words it already uses for that case. The run still appears in the page's history of runs. Every sentence the page prints about the last full run stays true. Spec: `.scratch/kit-phase-1/spec.md`, user story 20.

**Blocked by:** 07

**Status:** ready-for-agent

- [ ] Red first: a page test with a full run followed by a quick run still reports the full run as the last full one
- [ ] A red quick run after a green full run shows as a later failure, as a run of some checks does today
- [ ] A branch with only quick runs has no full run, and the page says so
- [ ] A run line written before this build, with no quick field, is read as a full run

## Comments
