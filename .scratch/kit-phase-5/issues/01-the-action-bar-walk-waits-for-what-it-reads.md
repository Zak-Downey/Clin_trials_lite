# 01: The action-bar walk waits for what it reads

**What to build:** `test_walk_the_action_bar_states_its_scope_stays_visible_and_leaves_the_last_change_clear` in `walks/test_trial_page_walk.py` failed beside the other walks and passed alone in two builds (`.scratch/kit-phase-2/walks/flaky.jsonl` at 1024 x 768, `.scratch/kit-phase-4/walks/flaky.jsonl` at 1440 x 900). It reads the review bar's words and its place on the screen straight after the trial opens, and reads places again straight after each scroll. Find what it reads before the page has finished drawing or settling, and make it wait for that thing, as E-039 and E-040 were fixed. Show the race red first by slowing what the walk races (the trial's answer, the drawing, or the scroll), in a new walk or by the stand-in's switches; many green runs in a row are not proof. Its assertions keep their meaning: nothing is loosened, removed or wrapped in a retry. If the fault is in the page and not in the walk (the bar really is misplaced for a moment a person could act in), that is a defect of the app: fix the page, and say so. Add its line to the defect log by the log's own rules. Spec: `.scratch/kit-phase-5/spec.md`, "The wobbling test".

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Red first: a walk that slows what the test raced fails as the wobble did, and passes after the fix
- [ ] The comments say what was read too early, whether the fault was the walk's or the page's, and what the test now waits for
- [ ] No assertion of the walk was loosened, and no retry or fixed pause was added
- [ ] The whole browser suite, run three times in a row at both window sizes, reports no wobbling test; `python3 checks.py` ends green on this ticket's commit

## Comments
