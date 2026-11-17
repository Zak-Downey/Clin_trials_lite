# 01: The app starts on port 8765 unless told otherwise

**What to build:** `python run.py` with no `--port` listens at `http://127.0.0.1:8765/`, prints that address and opens it, so saved links and each watchlist's remembered tab last across restarts. `--port` still chooses another port. When another program holds 8765 the app stops with today's busy-port message (naming the port and `--port`) and never moves to another port. A second start of this app still points at the copy already running. The servers that tests and walks start keep their free ports. The README says the app starts at 8765 and that links and remembered tabs survive a restart. Spec: `.scratch/trial-address-and-port/spec.md`, user stories 1–7, Implementation Decisions › Port, Testing Decisions › Port.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] A plain `python run.py` uses port 8765: a test shows it, red first, without fighting a copy of the app already running on 8765
- [ ] When 8765 is held by another program, `run.py` exits non-zero with a plain line naming 8765 and `--port`, and no traceback
- [ ] `--port N` still listens on N
- [ ] Starting a second time against the same database still prints "already running" with the first copy's address and exits 0
- [ ] The existing `run.py` subprocess tests that relied on the free default now pass a port explicitly and still pass side by side
- [ ] The API tests' and the walks' servers still start on free ports
- [ ] The README names `http://127.0.0.1:8765/` as the address and says links and remembered tabs last across restarts

## Comments
