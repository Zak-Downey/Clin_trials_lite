# Spec: Deploy the Trial Change Monitor to GitHub Pages

Status: ready-for-agent

## Problem Statement

The Trial Change Monitor only exists on the machine it was built on. Running it means cloning the repo, installing Python dependencies and typing `streamlit run` — which rules out everyone the tool was built for. An analyst covering a therapy area should be able to open a link and start watching trials.

The obvious answer, a hosted app, brings everything that makes a prototype stop being lightweight: a server to pay for and patch, accounts to administer, and a database holding other people's working notes. None of that is wanted. Nobody should have to sign in to watch a competitor's trial.

## Solution

Publish the app as a static site on GitHub Pages, where it runs entirely inside the visitor's own browser as WebAssembly, and keep each visitor's watchlists in their own browser storage. No server, no accounts, no shared database.

Three facts were established before committing to this, and they are what make it possible:

- **ClinicalTrials.gov can be called from a browser.** The v2 API returns `access-control-allow-origin: *`, so the page talks to the registry directly with no proxy standing in for a backend. This was the make-or-break question: had it failed, a static deployment would have been impossible.
- **The browser can keep a SQLite file.** stlite mounts IndexedDB-backed directories, so the database survives a refresh with no account attached to it.
- **The app must live within Streamlit 1.50.** stlite bundles that version; the repo develops against 1.63.

## What this costs

Browser-local storage is the price of no login, and it is a real price worth stating plainly: watchlists do not sync between devices, are not backed up, and are lost if the visitor clears their site data. A tool that forgets is worse than no tool if nobody is told it forgets, so this is documented in the README and recorded as an ADR rather than left for a user to discover.

## What is deliberately not changing

The `synthetic` flag stays in the schema and in the code. It reads as developer scaffolding but is not: it is a provenance marker threaded through storage, diffing, monitoring, the briefing and the display layer. Removing it is a wide refactor across six modules with real regression risk and nothing to show for it, because in the deployed app nothing ever sets the flag and no marker is ever rendered. The simulator that writes synthetic data is taken out of the deployed app and kept for local development.
