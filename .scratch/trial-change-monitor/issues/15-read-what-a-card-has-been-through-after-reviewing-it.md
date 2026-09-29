# 15: Read what a card has been through after reviewing it

**What to build:** Marking a trial reviewed (05) clears its highlighting, which is right for "what is new since I last looked" and wrong for "what has this study been through". The moment an analyst presses the button, the slipped completion date they have just read disappears from the dossier, and the only way back to it is the briefing's date-range summary. 05 kept the change records for exactly this; nothing yet reads them back on the card they belong to.

Each card of the opened profile carries its own history, folded away underneath it: every move its fields have made since monitoring began, newest day first, each marked read or unread. The fold says how many moves there are and when the last one was, so a card that moved last week is told apart from one that moved in spring without opening either. A card nothing has moved on says so. The history is grey, never in the highlight colours, which keep meaning "unread".

A value and its estimated/actual type moving in one check are one move, as they are in the briefing.

**Blocked by:** 05

**Status:** done

- [x] Every card with recorded moves offers its history, folded, with the count and the last date on the fold
- [x] The history survives marking the trial reviewed
- [x] Each move says what it went from and to, and whether it has been reviewed
- [x] A field that moved twice shows both moves
- [x] A date and its type moving together read as one move
- [x] A simulated move is marked in the history
- [x] A card with no moves says so rather than folding away nothing
- [x] Tests cover: history kept through review, ordering and read state, repeated moves, folded qualifiers, grouping into cards, and the page after a review

## Comments

**2026-09-28 — decided by prototype.** Question: once a trial is reviewed and its cards go clean, how should the reader still see what moved: the last change on each field, recent changes over a window, or a record per card? Four variants were built on the real Watchlist page: A (a grey trace of each field's last move), B (a folded history per card), C (a lens re-highlighting over 7/30/90 days), D (clean cards with a timeline rail). **B was chosen.** The prototype, including a static HTML copy of all four variants, is on the throwaway branch `prototype/card-change-history` (pushed to origin); run it with `python prototype_card_history.py` on that branch.
