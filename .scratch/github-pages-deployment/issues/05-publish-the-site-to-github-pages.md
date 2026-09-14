# 05: Publish the site to GitHub Pages

**What to build:** A URL an analyst can open. Pushing to the repository builds the static site and publishes it to GitHub Pages automatically, so the published app is always the committed code and nobody has to remember a manual build step.

The build assembles the site from an explicit list of what belongs in it. This is the point where getting it wrong stops being recoverable: GitHub Pages is public, and the repository holds a working database that may contain real monitoring history, the internal issue tracker and specs, the test suite, and the simulator. Copying a directory wholesale would publish all of it. Listing what goes in, rather than what stays out, is what makes that mistake hard to make by accident — a file nobody named is a file nobody ships.

Two steps here cannot be done from the code and need a human at the GitHub settings screen: turning Pages on and pointing it at the workflow, and confirming which branch publishes — worth checking deliberately, because this repository is being developed on a branch that is not the one recorded as its default, and a workflow watching the wrong branch fails by doing nothing at all, which is easy to mistake for success.

Once it is live, the checks that mattered locally are worth repeating against the real URL, because the deployed thing is what people will use.

**Blocked by:** 02, 03

**Status:** ready-for-agent

- [ ] Pushing to the publishing branch builds and deploys the site with no manual steps
- [ ] The app loads at its public URL, searches the registry, and keeps a watchlist across a refresh
- [ ] The published site contains no database file, no internal notes or specs, no tests and no simulator
- [ ] The site is assembled from an explicit list of files rather than a copied directory
- [ ] The build does not depend on any secret, token or account
- [ ] The human-only setup steps are recorded somewhere the next person will find them
