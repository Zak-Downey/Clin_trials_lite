# 04: Restore the pause between registry requests

**What to build:** Checking a watchlist should pace itself in the browser the way it already does locally. Working through a list fetches each trial in turn with a deliberate half-second pause between them, for a stated reason: ClinicalTrials.gov is a free public service and a burst of back-to-back requests is rude. In the browser that pause does nothing at all — the call the app uses to wait is silently a no-op there — so the courtesy the code believes it is extending is not extended. A list of fifty trials would fire fifty requests as fast as the network allows, from every visitor, against a public registry, with nothing in the code to suggest anything is wrong.

This is worth fixing rather than accepting, because it is the kind of defect that is invisible until it is someone else's incident, and because the tool is about to go from one machine to a public URL where the number of people doing this is no longer one.

The pause needs to become a real one in the browser while staying exactly as it is locally, and the reason it exists should survive in the code so the next person to read it does not quietly optimise it away again.

**Blocked by:** 02

**Status:** done

- [x] Checking a multi-trial watchlist in the browser genuinely spaces its requests rather than issuing them back to back
- [x] The pause is unchanged when running locally
- [x] The reason the pause exists remains legible in the code
- [x] The full test suite passes, without the tests being slowed by real waiting

## Comments

Done, but the premise it was written on turned out not to hold, and that is the more
useful half of this ticket.

The pause was measured on the runtime the app actually ships on -- stlite 0.90.12, loading
the real `browser.py` and timing it from inside a running Streamlit script. `time.sleep(0.5)`
took 0.51s there. It is not a no-op. stlite runs Python in a web worker, and the C library
underneath busy-waits on a worker thread; the "sleep does nothing" behaviour is the
main-thread one, which is not where this app's Python runs. So the fifty back-to-back
requests were not happening.

What is true is that nothing in the app was making that pause happen. It held because of
how somebody else's build of the C library implements one call, with no test touching it
and nothing that would say so if an stlite upgrade changed it -- and the failure would be
silent, with the call still there and still made. On a public URL that is worth not
depending on, so the work was done anyway, on that reason rather than the stated one.

`browser.wait` is the pause now: `time.sleep` locally, and in the browser an explicit spin
on `time.monotonic()` until the deadline passes. `monitor.check_all` calls it instead of
sleeping directly. `Atomics.wait` on shared memory is the proper way to block a worker and
was not available -- it needs the page served with cross-origin-isolation headers, which
GitHub Pages does not send.

`browser.py` grows past being only a transport, and its docstring says so now: it is the
module that knows the app is running in a browser. The README's list of what differs in the
browser said "two things and nothing else is", so it now says three.

The same stlite harness that disproved the premise measured the replacement: with
`IN_BROWSER` on, `browser.wait(0.5)` took 0.5s inside stlite's worker, so the spin is known
to hold there and `time.monotonic()` is known to advance. That is criterion 1's mechanism
observed rather than inferred.

The cost is stated in `_spin` rather than left for someone to discover: spinning burns a
core where sleeping yielded it, so a fifty-trial list spends around twenty-five seconds of
somebody's CPU, and on a phone that is battery and heat. Worth it for the gap the registry
is owed; a reason to spend it only on pacing.

One thing found and deliberately not fixed here: `check_all` paces the trial loop only. A
list with a remembered search fires that search and then the first trial fetch with no gap
between them, and a single `check()` can make more than one call. It is two requests, not
fifty, so it is not this ticket's defect -- but "the watchlist paces itself" is true of the
trial-to-trial gap and not yet of the whole run.

Tests patch `IN_BROWSER` and a fake monotonic clock, so the browser pause is asserted to
actually wait without the suite waiting for it, and the check-run test now watches
`browser.wait` rather than `time.sleep` -- a return to a bare sleep fails it. Full suite:
417 passing.
