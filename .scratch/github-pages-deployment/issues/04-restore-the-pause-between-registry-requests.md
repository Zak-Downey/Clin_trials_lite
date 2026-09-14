# 04: Restore the pause between registry requests

**What to build:** Checking a watchlist should pace itself in the browser the way it already does locally. Working through a list fetches each trial in turn with a deliberate half-second pause between them, for a stated reason: ClinicalTrials.gov is a free public service and a burst of back-to-back requests is rude. In the browser that pause does nothing at all — the call the app uses to wait is silently a no-op there — so the courtesy the code believes it is extending is not extended. A list of fifty trials would fire fifty requests as fast as the network allows, from every visitor, against a public registry, with nothing in the code to suggest anything is wrong.

This is worth fixing rather than accepting, because it is the kind of defect that is invisible until it is someone else's incident, and because the tool is about to go from one machine to a public URL where the number of people doing this is no longer one.

The pause needs to become a real one in the browser while staying exactly as it is locally, and the reason it exists should survive in the code so the next person to read it does not quietly optimise it away again.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Checking a multi-trial watchlist in the browser genuinely spaces its requests rather than issuing them back to back
- [ ] The pause is unchanged when running locally
- [ ] The reason the pause exists remains legible in the code
- [ ] The full test suite passes, without the tests being slowed by real waiting
