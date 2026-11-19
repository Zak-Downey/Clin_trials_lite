# 03: The page says what GitHub's machine found

**What to build:** The hand-over page gains one statement about the run of the `checks` workflow on GitHub for the build's last commit. `handover.py` asks GitHub through the `gh` command (the runs of that workflow for that commit) and the page says one of five things, in the owner's words, with no term left unexplained: it passed there, with the run's number and how many minutes it took; it failed there, with the run's address and, where GitHub gives it, the step that failed; it is still running; no run was made for this commit; or GitHub could not be asked, and why (`gh` is not installed, is not signed in, or gave an error, quoted). Only a pass is good news: each of the other four adds one to the page's own count of things to look at, with a sentence saying what the owner can do (wait and build the page again; start the run; sign in). A run of an earlier commit of the branch is never taken for this commit's: with only such a run, the page says no run was made for this commit and that an earlier one exists. When several runs exist for the commit, the newest decides. When the branch has a pull request, the page gives its address and says whether it is still a draft (not yet accepted) or ready. Building the page never fails, and never waits more than a few seconds, because of GitHub. It names nothing of this product. Spec: `.scratch/kit-phase-5/spec.md`, "Asking GitHub".

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Red first, with a stand-in for the `gh` command: one test for each of the five things the page can say, each checking the words the owner reads and whether the count of things to look at went up
- [ ] Red first: a run that belongs to an earlier commit is not reported as this commit's; with two runs for the commit the newer decides
- [ ] Red first: with a draft pull request for the branch, the page gives its address and says it is not yet accepted; with none, it says nothing of one
- [ ] Red first: with the command missing, or ending in an error, or taking too long, the page is still built and says GitHub could not be asked and why
- [ ] A page built from records with no such answer at all (an older build) reads as it did before, apart from the new statement; `python3 checks.py` ends green on this ticket's commit

## Comments
