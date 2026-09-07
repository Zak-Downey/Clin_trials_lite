# 07: Read an opened trial without scrolling

**What to build:** Selecting a watchlist row opens the trial's profile as a single column of 41 fields, one under the next, each rendered as its own markdown block. On a wide screen that wastes two thirds of the width, Streamlit's per-block margins stretch the profile over several screens of mostly white, and the fields arrive in one undifferentiated run — the completion date sits between an enrollment type and a study-first-post date with nothing to say they belong to different questions. Finding what you came for means scrolling and reading labels.

Lay the same fields out as a **dossier**: eight titled cards, dealt across three columns, each card holding the fields that answer one question about the study. The whole profile should fit on roughly one screen, and a reader looking for the dates should be able to go straight to the card called that.

Two things make it compact rather than merely re-arranged:

- **A card is one rendered block, not one per field.** The vertical white in the current profile is Streamlit's block margin repeated 41 times, so the fix is to render each card's fields as a single unit with a label and value on the same line. This is the whole of the density win; a card grid built one field per block would look no better than what it replaces.
- **The groups are named, and nothing falls out of them.** A field the grouping doesn't recognise goes into a final "Other" card, so a profile field added later shows up rather than silently disappearing from the page.

Highlighting is unchanged and non-negotiable: a moved field keeps the loud colour when it is high-signal and the quieter one otherwise, carries what it moved from, and is marked 🧪 when the simulator caused it. Because a card can be scanned past, each card's title also carries a count of the unreviewed changes inside it, so nothing that moved can hide in a card the reader's eye skipped.

The header above the cards — the synthetic badge, the NCT ID and title, the last-checked and last-reviewed line, and the "Mark as reviewed" button — stays exactly as it is.

**Prototype:** branch `prototype/profile-layout`, file `prototype_profile.py`. Three layouts were built on the real page against the real database and compared on screen: **variant A (dossier) won**, over B (a split pane leading with the changes, with the study demoted to a dense reference table) and C (a metric strip of vitals over topic tabs). C's vitals strip was considered as an addition to A and deliberately turned down. The branch is the primary source for why the other two lost. Do not promote its code: it was written under prototype rules — no tests, raw HTML in B, and A and C sharing a copied line renderer.

The grouping is a decision about what the fields mean, not about how Streamlit draws them, so it belongs behind the existing view seam with the other pure formatting helpers, where it can be tested without running Streamlit. `app.py` stays a thin view.

The field-to-card mapping, settled by the prototype:

```python
GROUPS = [
    ("Identity", ["nctId", "briefTitle", "officialTitle", "acronym", "orgStudyId", "secondaryIds"]),
    ("Sponsor", ["leadSponsor", "sponsorClass", "collaborators", "responsibleParty"]),
    ("Status and dates", [
        "overallStatus", "whyStopped", "startDate", "startDateType",
        "primaryCompletionDate", "primaryCompletionDateType",
        "completionDate", "completionDateType",
        "studyFirstPostDate", "resultsFirstPostDate", "lastUpdatePostDate",
    ]),
    ("Drugs and arms", ["interventions", "interventionTypes", "armGroups", "drugMeshTerms"]),
    ("Disease and eligibility", ["conditions", "conditionMeshTerms", "sex", "minimumAge"]),
    ("Design and scale", [
        "studyType", "phases", "enrollment", "enrollmentType",
        "allocation", "primaryPurpose", "masking",
    ]),
    ("Endpoints", ["primaryOutcomes", "primaryOutcomeTimeFrames", "secondaryOutcomeCount"]),
    ("Results", ["hasResults", "resultsUrl"]),
]
```

**Blocked by:** 06

**Status:** done

- [x] An opened trial's profile renders as titled cards laid out across three columns, replacing the single vertical stack
- [x] Every field the profile carries appears exactly once; a field outside the named groups appears in an "Other" card rather than vanishing
- [x] A card's fields are rendered as one block, with each field's label and value on the same line
- [x] A changed field is still highlighted, with the louder treatment reserved for high-signal fields
- [x] A changed field still shows the value it moved from, and a simulated change is still marked synthetic
- [x] A card whose fields include unreviewed changes says how many, in its title
- [x] The results link still renders as a link, not as a bare URL
- [x] A field with no value still reads as empty rather than looking like a rendering fault
- [x] The header, the last-checked and last-reviewed line, and the "Mark as reviewed" button are unchanged, and reviewing still clears the highlighting in the same interaction
- [x] The walkable loop still runs end to end: add a trial, check, simulate a change, check, read what moved from the watchlist table, open the row, read the cards, review it
- [x] Tests cover the grouping without running Streamlit: every field lands in exactly one card, the card order is fixed, an unknown field falls into "Other", and a group with no fields present is not rendered
