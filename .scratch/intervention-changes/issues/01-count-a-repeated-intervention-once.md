# 01: Count a repeated intervention once when detecting changes

**What to build:** A check for updates no longer reports an interventions change when the only difference between the previous and current record is how many times a name repeats (the registry can name an intervention once per arm). Lists still compare by membership, so a reordered list stays a non-change. The analyst sees nothing new on screen; a false change simply stops appearing. This changes what is detected, and the commit message says so. Spec: `.scratch/intervention-changes/spec.md`, user stories 17 and 18.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] A record whose interventions differ from the previous one only in how often a name repeats records no change
- [ ] A record whose interventions are only reordered still records no change
- [ ] Adding or removing a distinct intervention still records an interventions change
- [ ] Every other field's detection is unchanged (the existing comparison tests pass untouched)
- [ ] A unit test for the repeat-only case, red before the fix
- [ ] The commit message states that detection changed and why
