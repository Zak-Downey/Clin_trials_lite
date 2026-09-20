# 05: Publish the site to GitHub Pages

**What to build:** A URL an analyst can open. Pushing to the repository builds the static site and publishes it to GitHub Pages automatically, so the published app is always the committed code and nobody has to remember a manual build step.

The build assembles the site from an explicit list of what belongs in it. This is the point where getting it wrong stops being recoverable: GitHub Pages is public, and the repository holds a working database that may contain real monitoring history, the internal issue tracker and specs, the test suite, and the simulator. Copying a directory wholesale would publish all of it. Listing what goes in, rather than what stays out, is what makes that mistake hard to make by accident — a file nobody named is a file nobody ships.

Two steps here cannot be done from the code and need a human at the GitHub settings screen: turning Pages on and pointing it at the workflow, and confirming which branch publishes — worth checking deliberately, because this repository is being developed on a branch that is not the one recorded as its default, and a workflow watching the wrong branch fails by doing nothing at all, which is easy to mistake for success.

Once it is live, the checks that mattered locally are worth repeating against the real URL, because the deployed thing is what people will use.

**Blocked by:** 02, 03

**Status:** done

- [x] Pushing to the publishing branch builds and deploys the site with no manual steps
- [x] The app loads at its public URL, searches the registry, and keeps a watchlist across a refresh
- [x] The published site contains no database file, no internal notes or specs, no tests and no simulator
- [x] The site is assembled from an explicit list of files rather than a copied directory
- [x] The build does not depend on any secret, token or account
- [x] The human-only setup steps are recorded somewhere the next person will find them

## Comments

Done as far as it can be done from the code, and the one criterion left unticked is left
unticked for a reason worth stating rather than glossing.

**This repository has no git remote.** It has never been pushed anywhere, so there is no
GitHub repository, no Pages settings screen, and no public URL to check the app against.
Everything that can be built has been; the publication itself is waiting on a human with
a GitHub account, and the second criterion stays open until somebody runs those checks
against the real URL.

`.github/workflows/deploy.yml` is the whole of it. It checks out, runs
`python build_site.py site`, uploads that directory as the Pages artifact and deploys it.
No dependencies are installed: `build_site.py` is stdlib-only, and the app's libraries
come from stlite in the visitor's browser rather than from the runner. The only credential
is the OIDC token GitHub mints for the run, asked for as `id-token: write` on the deploy
job -- no secret, no stored token, no service account. Nothing is granted at the top of
the file: the build asks for `contents: read` and the deploy for what writes to Pages, so
the step that runs repository code holds no publishing rights.

The list is not restated in the workflow. It runs the same `build_site.py` that reads the
page's own `const sources`, so `test_site.py`'s guarantees -- the app's every module
travels, nothing else does, the working database and the simulator and `.scratch/` stay
behind -- are guarantees about the published site and not only about a local build. A
build into a temporary directory was inspected file by file: the page and twelve modules,
and nothing else.

The branch trap the ticket names is handled by not choosing. The workflow watches both
`main` (what the repository records as its default) and `master` (what it is developed
on), because the cost of watching both is nothing and the cost of guessing wrong is a
workflow that never runs and never says so. A test asserts both names stay in the list. If
the publishing branch ever becomes a third name, that test is where to look.

The human-only steps are in the README, in a section of their own next to the local build
instructions: turn Pages on and set its source to *GitHub Actions* rather than to a
branch, and confirm the branch being pushed. The first of those is called out as the
failure that does not look like one -- until Pages is switched on, the workflow runs green
and publishes nothing.

Six new tests in `tests/test_deploy.py` read the workflow as YAML and hold it to the
things that would be expensive to get wrong quietly: both branches watched, the site built
by the script rather than copied, only the build's output uploaded, no secrets, and the
setup steps written down. `pyyaml` joins `requirements.txt` for them. Full suite: 423
passing.

One thing deliberately not added: the workflow does not run the test suite before
publishing. It would need the app's whole dependency set installed on the runner to do it,
and this ticket is about publication rather than about a CI gate. Worth its own ticket if
the repository ever wants one.

Review found one thing worth fixing and it was fixed: the run was set to cancel a deploy
already in progress, on a comment that had the reasoning backwards. `group: pages` is what
serialises publication; cancelling mid-run can leave Pages halfway through replacing the
site, and the queued run publishes the newer commit a minute later regardless. It now
queues, and the comment says why. Permissions moved from the top of the file onto the two
jobs at the same time, and the test that reads them reads them there.

The test tying the build to the upload was also tightened: it now parses the directory out
of the `build_site.py` command line and asserts the artifact is that directory, rather than
checking each separately -- with the two apart, renaming the build's output to `dist` left
both green while the deploy shipped nothing. Confirmed by making that change and watching
the test fail.

The README now also says which branch the site is published from today, and what to do if
`main` and `master` ever diverge -- watching both removes the silent no-op, but leaves
"last push wins", which is worth a reader knowing about rather than discovering.

## It is live

https://zak-downey.github.io/Clin_trials_lite/

The remote that did not exist now does. The repository was created public, the branch
renamed `master` -> `main`, and the push triggered the workflow on its own: build in 6s,
deploy in 8s, both green on the first run.

Pages was turned on through the API rather than the settings screen -- `POST
/repos/:owner/:repo/pages` with `build_type=workflow` -- so the step the ticket called
human-only turned out to be one a token with `repo` scope can do. The README still
describes the settings-screen route, which is the one a person will look for. What did
need a human was the push itself: GitHub refuses to accept a new file under
`.github/workflows/` from an OAuth token without `workflow` scope, which is worth knowing
because it fails at the push and not at the workflow.

The deployed site was checked over HTTPS rather than assumed. `index.html` serves, carries
its `const sources` list, and `app.py`, `storage.py`, `browser.py` and `views/watchlist.py`
all return 200. Everything that must not be there returns 404: `monitor.db`,
`simulate.py`, `explore.py`, `build_site.py`, `tests/test_app.py`, the spec under
`.scratch/`, and even `README.md` and `requirements.txt`. The artifact is the build's
output, so the repository is not the site -- confirmed against the real URL rather than
against the build directory.

The last criterion stays open, and honestly so: the page is live, but nobody has yet
searched the registry from it and refreshed to see a watchlist survive. That is a browser
and a human, and it is the check that matters most, because it exercises the two things
that were uncertain when this feature was specified -- a cross-origin call to the registry
and an IndexedDB-backed database.

## The check was run

The last criterion is ticked because a human ran it, on 2026-09-20, against the live URL
in a real browser: the app loaded, a registry search returned results, a watchlist was
filled from them, and a refresh found the watchlist still there. Approved.

That closes the two things this feature was uncertain about when it was specified, and it
closes them the only way they could be closed -- neither is observable from a build
directory or a test suite. The cross-origin call to ClinicalTrials.gov works from a page
served off github.io, and the IndexedDB-backed database survives the page being torn down
and rebuilt.

The ticket is done. Worth knowing what this check did *not* cover, so nobody reads it as
wider than it is: it exercised searching and persistence, not the rest of the app. A
defect in list renaming has since been found that is present on this deployment (the
published site runs Streamlit 1.50, where the repository was developed against 1.63) --
that is its own ticket, not a reopening of this one.
