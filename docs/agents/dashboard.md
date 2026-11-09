# The dashboard

One static page, `gate.py dashboard`, that says whether the gates are catching defects, where the ones that slip through should have been caught, and what a build costs. `gate.py close` writes it at the end of every close and prints `dashboard: <path>`; the hand-over names the same path. The default path is `factory/dashboard.html` inside the repository's git directory, so it is never committed; `gate.py dashboard <out.html>` writes elsewhere and `--sample` draws it from invented figures.

## What it shows

- **Builds**: one row per build (tickets, reviews, blocking findings, mutants, boxes, hours, guard refusals, flakes) from `builds.jsonl`.
- **Escapes**: defects found after the gate that should have caught them, by the gate that should have, from `escapes.jsonl`.
- **Tokens and cost**: tokens by role per build, and the cost when prices are set, from `tokens.jsonl`.
- **Flakes**: checks that failed under load and passed alone, from `flakes.jsonl`.
- **GitHub**: Actions usage and artifact and cache storage, from `github.jsonl` and `github-storage.json`.

A missing record is an empty section that names the command that fills it.

## Which tiles carry a change

A tile carries "vs last" when it is per build and its two sides are comparable: Escapes per ticket, Found by you, Tokens per ticket, Surviving mutants and Flakes always (Tokens per ticket and Surviving mutants only when both builds have the records), and Build cost when both builds are fully priced. The GitHub Actions and GitHub storage tiles carry none: they are per month, not per build, so there is no previous build to compare with, and a change against the previous month would need two months of lines. A Build cost with an unpriced model on either side carries none either: the two sums would count different things. Story 22 ("every KPI shows its change") is read as every per-build KPI whose two sides are comparable.

## What writes each record

| Record (under `docs/agents/local/`) | Written by |
|---|---|
| `builds.jsonl` | `gate.py close` |
| `tokens.jsonl` | `gate.py close`; `gate.py stats --write <feature>` for a build already closed |
| `escapes.jsonl` | `gate.py ledger add` |
| `flakes.jsonl` | `gate.py ready` |
| `github.jsonl`, `github-storage.json` | `gate.py github`; `close` runs it for the current month when `origin` is a GitHub remote |

## Prices

Set `prices` in `factory.json`, dollars per million tokens, one entry per model name as it appears in `tokens.jsonl`:

```json
"prices": {"<model>": {"input": 3, "output": 15, "cache_read": 0.3, "cache_write": 3.75}}
```

A model with no entry is shown as `unpriced`, never as free; so is a model whose entry leaves out a kind (say `cache_read`) that its records used, so set all four kinds. `close`'s Facts say how many models are unpriced. With no `prices` the page shows tokens only.

## What `github` needs

`gh` on the PATH and signed in (`gh auth login`), and a GitHub `origin`. 
Billing usage, as GitHub's docs say (read 2026-11-08, API version 2026-03-10: https://docs.github.com/en/rest/billing/usage), takes a personal access token (classic), not a fine-grained one, and access is by role: the account holder for a user, an organisation owner or billing manager for an organisation. The user form also needs the enhanced billing platform, so a 404 means the report is not available for the owner. A 403 names the token and role; a 404 says so; a failed owner lookup skips the call. Each time `github` records storage only and carries on, and writes the reason as a `usage` field in `github-storage.json`, which the page's cards repeat. Whether the token `gh auth login` gives reaches the endpoints is not yet checked (the first real GitHub remote does). `gh` not answering within its deadline is said as such; `close` never waits on it for long. With no remote, `close` does not call `gh`.
