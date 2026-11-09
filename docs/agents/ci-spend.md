# CI spend: GitHub Actions minutes

On a private repo every workflow run bills minutes against a monthly allowance, and an agent session can spend a month's allowance in two days. Jev Bench did: about 3,570 minutes in 38 hours (2026-11-03). Most of it came from pushing to a draft pull request after every ticket merge, about 65 pushes at 36 minutes each. A push is a **billed run**. Everything below reduces the number of billed runs, or what each one costs.

What this repo's workflows are, and any gap against the checklist, is in `local/repo.md`.

## Pushing

- **Push a batch, in every phase.** Commit locally as work lands. Push when a batch of merges is in, before a review reads the branch, and when the pull request is marked ready. Jev Bench's PR 22 ran its browser suite twenty times for seventeen tickets, and eleven of those runs were red on the same regression.
- **Only the orchestrating session pushes.** The guard refuses a push from a subagent.
- **The local gate is green before the push.** `gate.py merge` runs every suite on every merge (`orchestrator.md`), so the integration tip is always a tree that passed locally. CI confirms a green tree on a clean machine. A regression is found locally, where it costs no minutes.
- **A commit that changes only comments or docs carries `[skip ci]` in its message** when it goes to a pull request that also changes code. `paths-ignore` filters on every file the pull request changes, so it lets that push run in full. GitHub honours `[skip ci]` in a pushed commit or in a pull request's head commit.
- **A commit CI has already passed is not run again.** Before a rerun or a manual dispatch, check `gh run list --commit <sha> --status success`.
- **A pull request stays a draft while tickets land and is marked ready once**, through the ready gate (`orchestrator.md`). A workflow that skips drafts (below) depends on this. The guard refuses `gh pr create` without `--draft`.

## Waiting and failures

- **The orchestrating session waits for CI with `gh pr checks <N> --watch`, run in the background,** and acts on the notification. The watch outlasts the Bash tool's ten-minute ceiling. Subagents do not wait on CI at all.
- **A red job is read from its log**: `gh run view <id> --log-failed`. The failure is reproduced and fixed locally, and the fix goes in the next batch, so one push carries a fix that is already known to be green.
- **A job that fails within seconds, before its first step, is a billing or quota block.** Stop and tell the user. Lifting it is theirs, and no code change fixes it.

## Writing a workflow

A new or edited workflow has every item below from its first commit. Each one cost Jev Bench minutes before it was added.

- **Cancel superseded runs.** Without this, 136 of Jev Bench's 200 runs were followed by another on the same branch within half an hour.
  ```yaml
  concurrency:
    group: ${{ github.workflow }}-${{ github.ref }}
    cancel-in-progress: true
  ```
- **Trigger on `pull_request` only.** `main` changes only through a pull request that has already passed. A `push: branches: [main]` trigger reruns the same tree, and cost Jev Bench about 350 minutes.
- **Ignore docs-only changes**: `paths-ignore: ["**.md", ".scratch/**"]`. Because of the whole-pull-request filter above, this saves runs only on pull requests that change nothing but docs.
- **Expensive jobs skip drafts. Browser walks and end-to-end suites are expensive; type checks and unit tests are cheap and still run on drafts.**
  ```yaml
  on:
    pull_request:
      types: [opened, synchronize, reopened, ready_for_review]
    workflow_dispatch:
  jobs:
    walks:
      if: ${{ !github.event.pull_request.draft }}
  ```
  On a draft, the orchestrating session runs the walks on purpose with `gh workflow run <workflow> --ref <branch>`: after a merge that changed shared plumbing, after each batch, and before review.
- **When the local gate runs every suite in seconds, skip the whole workflow on drafts.** CI's job is then the clean machine, once, when the pull request is marked ready: the same run is the clean-clone smoke (`evidence.md`).
- **A dispatch needs the workflow on the default branch.** `gh workflow run` cannot start a workflow that exists only on the feature branch, so the workflow file lands on `main` in a pull request of its own before the build that relies on dispatching it.
- **Few jobs, not many small ones.** Each job's time is rounded up to a whole minute, so six twenty-second jobs bill six minutes. Put the cheap checks in one job.
- **Every job has `timeout-minutes`**, set near twice its measured time, so a hung job stops early instead of billing up to the six-hour default.
- **Dependencies and browsers are cached** (the repo's dependency and browser caches, from `local/repo.md`). Artifacts upload `if: failure()`.
- **A pull-request-only workflow never fills a cache on `main`**, and a pull request can read only its own caches and the base branch's. Each new pull request therefore starts cold. With one pull request per feature that is one cold run, and is the cheaper side of the trade; add a cache-warming run on `main` only if pull requests are many and setup is long.
- **A failure is rerun inside the job, alone and once**, rather than as a whole-job rerun. A flaky browser timeout then costs seconds, not a full run.
- **Parallelism buys little.** A private repo's `ubuntu-latest` runner has two cores: Jev Bench's suite went from eleven minutes to nine across them. Matrix shards cut waiting time but not billed minutes, because each shard pays its own setup. Cut runs first.
- **If branch protection requires a check, skip inside the job, not the workflow.** A workflow skipped by `paths-ignore` or `[skip ci]` leaves a required check pending and the pull request blocked; a job skipped by its own `if:` reports success.
- **The workflow's header comment says why it is shaped this way**, with the measured minutes and the date, so a later edit does not undo a saving without knowing what it saved.

## The other bill

Model spend is larger than CI spend and nothing above measures it. The orchestrating session records, in the build's row of `local/ledger.md`, how many subagents of each role and model a build used, so a gate's cost can be set against what it found.
