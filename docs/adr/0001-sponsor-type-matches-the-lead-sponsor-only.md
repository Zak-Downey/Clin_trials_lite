# 1. Sponsor type matches the lead sponsor only

**Status:** accepted (2026-09-14)

## The question

The registry gives every study a lead sponsor with a class, and separately lists
collaborators who each carry a class of their own. A search narrowed to
`Industry` matches `AREA[LeadSponsorClass](INDUSTRY)` and nothing else, so a
trial a company funds at an academic centre -- the company named as a
collaborator, the university as lead -- does not match.

For chronic lymphocytic leukemia, measured against the live registry:

| Query                                          | Studies |
| ---------------------------------------------- | ------: |
| the condition alone                            |   2,614 |
| industry **lead** sponsor (what the tool does) |     725 |
| industry lead **or** industry collaborator     |   1,064 |
| industry collaborator, academic lead           |     326 |

So the narrower reading hides 326 CLL studies with commercial money behind them:
31% of the studies a company is involved in at all.

## The decision

Keep lead-sponsor-only. Do not match `AREA[CollaboratorClass]`.

## Why

Sponsor class is offered as *the registry's own classification*, and the registry
classifies a study by its lead sponsor. Matching collaborators too would make
`Industry` mean "a company is involved somewhere", which is a different question
and would change what every other class means with it: `Other` would stop being
"the lead sponsor is not any of the named kinds" and start being a residue, and
an academic trial with one company collaborator would answer to both `Industry`
and `Other` at once. A filter that answers to two names is a filter the analyst
cannot reason about.

The 326 studies are a real gap, and the honest response is to say so rather than
to paper over it by widening the match: `OTHER` is labelled "Other (incl.
academic)" and the form's help text states the lead-sponsor rule, so an analyst
scanning competitors knows that ticking `Industry` alone is a commercially-led
view and not every study with commercial money in it.

## What would reopen this

A second, separate axis -- "a company is involved, as lead or collaborator" --
alongside the classes rather than inside them. That would answer the wider
question without overloading `Industry`, and it is the shape to reach for if the
326 turn out to matter in practice.

## See also

- `display.SPONSOR_TYPE_NAMES` and the comment above it, on why `OTHER` cannot
  be labelled "not companies"
- `ctgov.SPONSOR_CLASSES`, the classes as the registry spells them
- `.scratch/trial-change-monitor/issues/14-search-on-sponsor-type-status-and-start-date.md`
