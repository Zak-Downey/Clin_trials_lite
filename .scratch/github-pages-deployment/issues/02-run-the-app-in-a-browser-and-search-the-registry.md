# 02: Run the app in a browser and search the registry

**What to build:** The whole app, running inside a web browser with no Python installed and no server behind it, far enough to prove the idea works end to end: open a page, type a condition, and get real studies back from ClinicalTrials.gov.

A static page boots the app as WebAssembly and mounts its Python sources, which are fetched from the same origin rather than pasted into the page, so the deployed code stays the code in the repository. Only the modules the app actually needs are mounted — an explicit list, not a sweep of the directory, because everything mounted here is eventually published to a public URL and the repository also holds a working database, internal specs and tests.

The one thing that genuinely cannot survive the move is how the app reaches the registry. Every request in the app funnels through a single function, which is fortunate, because in the browser there are no sockets and no custom certificate handling — the page has to ask the browser to make the request. What must not change is what that function raises when things go wrong. The app turns a 404 into *"...was not found on ClinicalTrials.gov"* and an unreachable registry into *"Could not reach ClinicalTrials.gov"*, and it does that by catching the specific errors the current transport raises. A browser transport that reports failure differently would leave an analyst reading a stack trace instead of a sentence, so it has to fail in the same vocabulary, including distinguishing a missing study from a broken connection.

Two things to confirm while doing this rather than assume. The browser build carries Streamlit 1.50 where the repository develops against 1.63, and the app puts its page navigation along the top — a placement worth checking is supported there, with the ordinary sidebar navigation as the fallback if it is not. And the first load pulls down a Python runtime and its libraries, which takes long enough that a blank page reads as a broken one; it needs to say it is loading.

Verifiable without deploying anything: serve the page locally and search.

**Blocked by:** 01 (while the app depends on the simulator, the published bundle is forced to carry it)

**Status:** ready-for-agent

- [ ] The app loads and renders in a browser from a locally served static page, with no Python installed
- [ ] A search on a condition returns real results from ClinicalTrials.gov, proving the browser can reach the registry directly
- [ ] An NCT ID that does not exist produces the same readable "was not found" message as it does locally
- [ ] A registry that cannot be reached produces the same readable message as it does locally, distinct from the above
- [ ] Only an explicit list of modules is mounted; the working database, tests, internal notes and the simulator are not among them
- [ ] Page navigation works, in its current placement or the documented fallback
- [ ] The page tells the visitor it is loading rather than showing blank space
- [ ] The app still runs locally under Streamlit exactly as before, from the same entry point
- [ ] The full test suite passes
