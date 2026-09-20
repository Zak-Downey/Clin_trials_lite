# 08: Keep the list you are reading when you rename it

**What to build:** Renaming the list you are standing in leaves you standing in it.

Today it does not. Rename "Lung" to "Lung — AZ" on the published site and the name
changes, but the page drops back to showing the first list, "My watchlist". Nothing is
lost — the trials are all still there, under the new name, one click away — so this is an
irritation rather than a disaster. It is worth fixing anyway, because it happens at the
moment a reader is least able to tell an irritation from a disaster: they have just
renamed something and the thing they renamed has apparently vanished.

The cause is the list picker, shared by both pages from `views/pickers.py`. The picker is
a dropdown whose selection Streamlit remembers between runs, and Streamlit decides
whether the dropdown on the new run is the same dropdown partly from the option labels it
renders. Renaming a list changes one of those labels, so the control is treated as a new
one, the remembered choice is dropped, and the picker falls back to its first option.
Streamlit 1.63 identifies the control by its key instead and the fault does not appear
there — which is why this was invisible until the app was published, because the site
runs 1.50 and a mac development environment runs 1.50 as well.

The fix should not be a bet on which Streamlit is underneath. Ticket 09 moves the site
onto a version where the underlying behaviour is gone, and this ticket should stand
whether 09 has landed or not, and whether the next upgrade after it reverts the behaviour
or not. What the picker needs is for the chosen list to survive a change to the words in
the dropdown — the id is what the app cares about, and ids do not change when names do.

One thing in the picker must survive the fix: a list can be deleted while its id is still
sitting in the session, and `choose` already drops the stale id so the control falls back
to the first list rather than raising. That guard and this fix are easy to write in each
other's way — restoring a remembered id has to stop short of restoring one that no longer
exists.

This ticket sits in the deployment feature rather than with the monitor's own tickets
because the defect is a fact about the published app and was found by the version
divergence that publishing introduced.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Renaming the list being read leaves that list on screen, under its new name
- [x] The same holds for the picker on the Search page, which is the same control
- [x] A test covers it, and that test fails against the app as it stands today
- [x] Deleting the list being read still falls back to the first list rather than raising
- [x] Creating a list, and switching between lists, behave as they did *(switching does; creating no longer displaces the reader, which is a change and a deliberate one -- see below)*
- [x] The full test suite passes *(423 pass; 3 fail for a reason that predates this work and is unrelated to it -- see below)*

## Comments

The picker now keeps its own record of what was chosen, under a key of its own rather
than the widget's, and hands it back to the control as its starting position. Streamlit
reads a starting position only when it has no selection of its own, so this does nothing
at all on a version that keeps the selection -- which is what makes it a fix rather than
a bet. On 1.50 the rename makes the control look new and the record restores the list; on
1.62 and 1.63 the control is not new, Streamlit's own selection carries, and the record
is ignored. Ticket 09 can land, or be reverted, without touching this.

Three tests, each confirmed red against the app as it stood and green after: the rename
on the Watchlist page (which the suite already described and which was already failing
here), the same rename seen from the Search page's picker, and creating a list. A fourth
covers deleting the list being read, which was the trap the ticket named -- it passes
either way, so it was checked the only way a guard can be: by weakening the guard and
watching it fail with `ValueError: 2 is not in list`.

**Creating a list behaves differently now, and the criterion saying it would not is the
one place this departs from the ticket.** Creating puts a new name in the picker, which
moves the same ground a rename does, so it lost the reader's place the same way -- stand
in "Lung", make "Breast", and the page dropped you into "My watchlist". The criterion was
written to mean "do not break these", not "preserve this", and preserving it would have
meant special-casing the fix to keep a defect. It is now pinned by a test rather than
left to be discovered.

The sentinel the Search page offers instead of a list is remembered like any other
choice. The review reasonably asked whether it should be, since the ticket's reasoning
is about ids surviving a rename and the sentinel has no id. Left as it is on purpose: a
reader halfway through naming a new list has the same claim to be left where they are,
and singling the sentinel out would be a special case that buys nothing.

What the review changed: the helper is `_kept_at` rather than public, since this module
exports `names` and `choose` and nothing else, and every other module-internal helper in
the repository is underscored. The delete test asserts `storage.DEFAULT_LIST` rather than
the string "My watchlist", which is how the rest of the suite names it. Most usefully,
the "is this still offered?" test was written twice in two shapes, once per key, and the
second key was never actually cleared when it went stale -- harmless only because the
starting position was being checked separately. Both keys now go through the same loop,
which removed the duplication and the gap together.

Unrelated, and worth saying here because it is the reason "the full test suite passes"
needs a footnote: three briefing tests fail on this machine because Streamlit 1.50's
app-test harness has no `download_button` accessor at all. They fail at `HEAD` too. A
separate commit fixes nineteen other tests that were failing for a neighbouring reason --
the harness injected a table selection as a plain dictionary, where the real widget hands
back one that answers to attribute access. That commit is kept apart from this one
because it belongs to the version question ticket 09 raises, not to this fix.
