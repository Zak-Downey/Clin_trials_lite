# 01: Take the developer tools out of the app

**What to build:** The app opens with no developer tooling on screen. Today the sidebar carries a panel, expanded by default, offering to rewind a trial's stored history so the next check finds a fabricated difference. That exists because the first test case was a completed trial that would never change again, and the alerting path had to be demonstrable. It is the right tool for a prototype and the wrong thing to hand a stranger: it invites someone evaluating the tool to manufacture intelligence and then read it back as though a sponsor had moved.

The panel goes, along with the app's dependence on the simulator that backs it. The simulator itself stays in the repository and keeps its tests — it is still how a developer demonstrates the alerting path locally — it simply stops being something the app reaches for, so that later work can publish the app without publishing it.

The provenance flag that marks simulated data is deliberately left alone. It reads like developer scaffolding and is not: it is threaded through storage, diffing, monitoring, the briefing and the display layer, and tearing it out is a wide refactor across six modules with real regression risk. Nothing in the deployed app will ever set it, so no marker is ever rendered and the flag simply lies dormant.

The app's own description of itself needs to keep up: it currently advertises the simulator in the sidebar and explains that the sidebar is left to it, and both statements stop being true here.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] The app runs locally and shows no developer tools panel anywhere in it
- [x] The app no longer depends on the simulator, so it can be run without that module present
- [x] The simulator and its tests remain in the repository and still pass
- [x] The provenance flag, its column and every reader of it are untouched
- [x] The app's own documentation no longer describes a simulator or a sidebar given over to one
- [x] The full test suite passes
