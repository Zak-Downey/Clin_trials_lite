# 09: Search the registry and fill a list

**What to build:** The only way onto a watchlist is pasting an NCT ID one at a time, which assumes you already know the number. A medical affairs lead does not think in NCT IDs; they think "everything Janssen has in phase 3 for multiple myeloma", and they want that as a list they can fill in one sitting.

Give the Search page a **query built from four fields** — condition, intervention, sponsor, and phase — any of which can be left blank. Running it returns matching studies from the live registry as a **table that reads like the watchlist it feeds**: NCT ID, official title, sponsor, phase, status, conditions, interventions. Rows are selected from that table, and the selection is added to a named list chosen afterwards, either an existing one or a new one named on the spot.

Choosing the destination **after** selecting is the point, not an accident of layout: it is what lets one search be split across two lists, which is exactly what happens when a search for a drug turns up studies in two indications.

A result already in the chosen list should say so rather than being added twice, and adding a trial that is already monitored under another list must join it to this one rather than re-fetching it or starting its history over. Results are capped, and the page says how many it is showing and that it is a cap, so a search that matched thousands does not look like it matched forty.

**Prototype:** branch `prototype/watchlist-query`, file `prototype_search.py`. Three query surfaces were built on the real page against the live registry and compared on screen: **variant A (search and table) won**, over B (sidebar facets, result cards, the destination list as the tab you stand in) and C (criteria as chips with a live match count, a basket, named at save). The branch is the primary source for why the other two lost. Do not promote its code: it was written under prototype rules — no tests, no persistence, and the destination lists living in session state.

**Deliberately not taken from the prototype:** C's live match count, which narrows as criteria are added and made the search legible before a single result was read. It was noted as worth stealing and is not part of this ticket. Raise it separately if it is still wanted once A is in use.

The four axes map onto the registry API as `query.cond`, `query.intr`, `query.spons`, and the `AREA[Phase]` advanced filter; the prototype confirmed all four work together against the live service. Searching is the registry client's business and turning a study into a row is a formatting question, so the page should stay thin, as it did for the profile.

**Blocked by:** 08

**Status:** done

- [x] The Search page offers condition, intervention, sponsor, and phase, any of which may be left blank, and searching with all four blank is refused rather than returning the whole registry
- [x] Results arrive as a table carrying NCT ID, official title, sponsor, phase, status, conditions, and interventions
- [x] Several rows can be selected at once, and the destination list is chosen after selecting, from the existing lists or as a new name
- [x] Adding puts every selected trial in that list and starts monitoring anything not already monitored
- [x] A trial already monitored under another list joins this one without re-fetching it or losing its history
- [x] A result already in the chosen list is shown as already there rather than added twice
- [x] The result count is shown, and a capped result set says it is capped
- [x] A search that matches nothing says so plainly, and a registry that is unreachable reports the failure rather than showing an empty table
- [x] The walkable loop still runs end to end: search for a condition and sponsor, select several results, add them to a new named list, open that list on the watchlist page, check, and read what moved
- [x] Tests cover the search without touching the network: the four fields becoming registry query parameters, a study becoming a result row, and the blank-search refusal
