# 09: Move the published app onto a current stlite

**What to build:** A published app running a Streamlit close to the one the repository is
written against, instead of one twelve versions behind it.

Which Streamlit the site runs is decided by a single pinned version in `web/index.html`.
It pins stlite `0.90.12`, which carries Streamlit 1.50. The current stlite is `1.9.1` and
carries 1.62 — near enough the 1.63 the repository was developed against that the gap
between what a developer sees and what a visitor gets mostly closes. Ticket 08 exists
because of that gap: a defect that cannot be reproduced on 1.63 is live on the site.

The pin is deliberate and should stay a pin. What is being asked for here is to move it
once, on purpose, with the app checked afterwards — not to let it float, which would hand
a visitor's refresh the power to change the runtime underneath them.

Two things make the move worth doing beyond closing the version gap:

- **A crash this app is shaped to hit.** stlite 1.9.1 fixed a fault where a page that
  rendered a dataframe before a 5.5 MB WebAssembly module had finished loading died
  outright. The watchlist *is* a dataframe and it is the first thing drawn, so the app
  may be winning that race by luck rather than by design.
- **The migration looks cheap.** The only breaking change across the 1.0.0 boundary was
  renaming the `mountDocumentStyles` option to `disableDocumentStyles`, and this page does
  not use it. Every option the page does pass — `entrypoint`, `requirements`, `files`,
  `idbfsMountpoints`, `env`, `streamlitConfig` — is unchanged.

Cheap to write is not the same as cheap to trust, and the checking is most of this
ticket. The jump crosses roughly seventy stlite releases and moves the bundled Python
runtime, so what has to be established is not that the version number changed but that
the app still works — and in particular that **watchlists written before the upgrade
still open after it**. They live in the browser's own storage as a SQLite file, and a
visitor who loses months of monitoring to a version bump is owed better than an
apology. That check needs a watchlist created on the old version and read on the new one,
which means doing it in that order and not reinstalling the browser in between.

The spec for this feature records "the app must live within Streamlit 1.50" as an
established fact. That stops being true here, and the spec should say so rather than
leaving a future reader to wonder which of the two is current.

One thing this ticket does not settle: the repository's own development environment
cannot run 1.62 on Python 3.9, which is what a mac clone gets by default. Whether to
raise the local Python so tests run against what visitors run is a real question and a
separate one — this ticket only moves the site.

**Blocked by:** None, but do 08 first — its fix should be version-independent, and
landing it after this one removes the only environment where its test can fail.

**Status:** ready-for-human

- [x] `web/index.html` pins one current stlite version, in both the stylesheet and the
      module import, and still pins rather than floats
- [ ] A watchlist created on the published site before the upgrade opens, intact, after it
- [ ] The published app loads, searches the registry, and keeps a watchlist across a
      refresh — checked in a browser at the live URL, not in a build directory
- [ ] The watchlist table draws on first load, with nothing broken in the browser console
- [ ] Renaming a list keeps the list on screen
- [x] The comment in `web/index.html` says which Streamlit the new pin carries, and why
      the pin is a pin
- [x] The README and the feature spec no longer say the app must live within Streamlit 1.50

## Comments

The code change is landed; the four browser criteria are not, and cannot be from
here. Status is `ready-for-human` for that reason, not because the work is half
finished.

### Do not push until a watchlist exists on the live site

`deploy.yml` publishes on push to `main`, so **pushing this commit is the upgrade**.
The criterion above asking that a pre-upgrade watchlist still open afterwards can only
be met in one order: create a watchlist on the live site while it is still serving
0.90.12, and only then push. Once pushed, that "before" no longer exists to test
against, and getting it back means reverting the pin and republishing.

### What was checked here, so the browser check does not have to

Everything below was verified against the npm registry, jsDelivr and PyPI rather than
assumed, because the point of this ticket is that a version number changing is not
evidence the app still works.

- **1.9.1 is current**, and both CDN files it needs resolve.
- **It carries Streamlit 1.62 on Python 3.13**: the package ships
  `streamlit-1.62.0-cp313-none-any.whl`. 0.90.12 ships `streamlit-1.50.0-cp313`, so the
  Python does not move -- twelve Streamlits do, and that is the whole of it.
- **`requirements: ["sqlite3"]` still resolves.** Pyodide 0.29.x lists `sqlite3` 1.0.0
  as a loadable package for cp313. Had it stopped being one, the watchlist would not
  open at all -- the single largest risk in this upgrade, and it is cleared.
- **The boot overlay still hands over.** The page waits for
  `[data-testid="stAppViewContainer"]` before removing its loading screen, and falls
  back to a 120-second timer. That test id is still present in the 1.9.1 bundle, so a
  visitor will not sit in front of the spinner for two minutes.

### Two corrections to this ticket

- **It missed a breaking change that is actually in our path.** The ticket says the only
  one across the 1.0.0 boundary was `mountDocumentStyles` -> `disableDocumentStyles`.
  True, but 0.93.0 also removed the `workerType` option from `mount()`, and 0.93.0 is
  *above* the 0.90.12 we are leaving, so it is in the jump. The page does not pass
  `workerType`, so nothing changes -- but the ticket's reassurance was narrower than it
  read.
- **"Roughly seventy stlite releases" is high.** `@stlite/browser` published 31 releases
  between 0.90.12 and 1.9.1.

### The one thing still worth watching in the browser

Streamlit removed Base Web from its frontend across 1.58-1.62, and stlite moved its
overlay styling onto Streamlit's own portal host to follow. Overlays -- the date
pickers and multiselect dropdowns in the search form -- are the most likely place for
that to show, so they are worth opening rather than glancing at.

### The new test, and what it does not do

`tests/test_site.py` gains one test, which holds three of the four clauses of the first
criterion: one stlite, in both places, pinned rather than floating. Each clause was
proved to bite by breaking it on its own -- deleting the stylesheet link, leaving one
URL on the old version, and floating the pin to `^1.9`.

It cannot check the fourth clause, *current*, and should not try: that would mean a
test that fails when somebody else publishes a release. Keeping the pin current stays a
human decision, which is the same reason it is a pin.

Red-before-green was not reachable for this change. A version pin in a static page has
no failing-test state to start from -- the page was already internally consistent, so
the guard was green the moment it was written. Proving it by breaking the page three
ways is the honest substitute, and is recorded above rather than glossed.

### Review

Both axes ran. The findings taken:

- **The spec bullet claimed finished history.** It had been rewritten to say issue 09
  "moved" the pin, in an *established facts* section, while nothing was committed and
  the live site still served the old version. It now states the standing fact -- the
  pin decides the runtime -- and says the issue *moves* it.
- **The same bullet said the upgrade "closes the gap".** Ambiguous to the point of being
  wrong: the gap to the 1.63 this repository was developed against closes, and the gap
  to a Python 3.9 checkout, which is held at 1.50, opens. Both were in the same diff,
  contradicting each other. The framing is gone.
- **The test did not check what its own comment claimed.** `len(set(versions)) == 1`
  passes when there is only *one* URL, so deleting the stylesheet link left it green.
  Now checked separately, and that case is one of the three proved above. This was the
  most valuable finding of the review.
- **`PINNED` was a dishonest name** for a pattern that matches `latest` and `^1.9` too.
  It is `STLITE` now; `EXACT` is what judges pinning.
- **Duplicated read-and-raise.** `_said_all` sits beside `_said` and shares its habit of
  raising when the page has stopped saying something, so an empty answer cannot read as
  a passing one.
- **The page comment prescribed a procedure.** It had grown a sentence about how to
  verify an upgrade, which is this ticket's business and not the page's. Cut; the
  comment says what the pin is and why it is a pin, which is what was asked for.
- **The README bullet prejudged a deferred question.** It called a 3.9 checkout "the one
  environment where local and published differ by enough to matter" -- a judgement this
  ticket explicitly leaves open. It now states the fact (1.62 needs Python 3.10, so 3.9
  gets 1.50) and stops there.

One finding not taken: the review called the test scope creep, on the grounds that no
criterion asks for a test and it cannot catch staleness. The first criterion asks for
three checkable properties, and this is them; the staleness limit is real and is stated
above rather than papered over.

### Untouched, as the ticket asks

Whether to raise the local Python so the suite runs against what visitors run is still
open. Three briefing tests remain unrunnable on Streamlit 1.50 for an unrelated reason
(`AppTest` has no `download_button` accessor), and this ticket does not change that.
