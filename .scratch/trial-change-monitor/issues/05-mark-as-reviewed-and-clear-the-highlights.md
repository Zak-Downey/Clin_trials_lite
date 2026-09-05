# 05: Mark as reviewed and clear the highlights

**What to build:** Without this, highlighting means "this changed at some point" — which decays into permanent visual noise and makes the tool unusable by a second person. With it, highlighting means "new since you last looked", which is the actual question a monitoring analyst has.

Once an analyst has read a trial's changes, they mark it reviewed. The highlighting clears and the feed distinguishes trials carrying unreviewed changes from those already actioned. The change records themselves are retained rather than deleted, so a per-field history view can be built later from data already collected.

Simulating a further change and re-checking must re-highlight the trial, closing the full loop: add, check, change, see, review, change again.

**Blocked by:** 04

**Status:** ready-for-human

- [x] Each trial carrying unreviewed changes offers a way to mark it reviewed
- [x] Marking a trial reviewed clears its highlighting
- [x] Marking a trial reviewed does not delete any change records
- [x] The feed distinguishes trials with unreviewed changes from reviewed ones
- [x] Reviewing one trial does not affect any other trial's highlighting
- [x] A change detected after a review re-highlights the trial
- [x] The full loop is walkable end to end: add a trial, check, simulate a change, check, see it highlighted, review it, simulate again, see it highlighted afresh
- [x] Tests cover: highlighting clears on review, history survives review, a later change re-highlights, and review state is per-trial
