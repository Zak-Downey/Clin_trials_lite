"""Competitor-monitoring view of a study, for a medical affairs team.

Pulls the protocol-level facts that matter for tracking a competitor's trial:
who is running it, what drugs, what disease, key dates, and where it sits.

Results are deliberately NOT extracted -- the results schema is deeply nested
and arm-specific, so we link out to the ClinicalTrials.gov results tab instead.
"""

import ctgov

# The subset of the API's PascalCase fields this view needs. Passing these to
# ctgov.search() keeps bulk pulls small.
FIELDS = [
    "NCTId", "BriefTitle", "OfficialTitle", "Acronym", "OrgStudyId", "SecondaryId",
    "LeadSponsorName", "LeadSponsorClass", "CollaboratorName", "ResponsiblePartyType",
    "OverallStatus", "WhyStopped",
    "Condition", "ConditionMeshTerm", "Keyword",
    "InterventionType", "InterventionName", "InterventionOtherName",
    "ArmGroupLabel", "ArmGroupType", "InterventionMeshTerm",
    "StudyType", "Phase", "EnrollmentCount", "EnrollmentType",
    "DesignAllocation", "DesignInterventionModel", "DesignPrimaryPurpose", "DesignMasking",
    "StartDate", "StartDateType",
    "PrimaryCompletionDate", "PrimaryCompletionDateType",
    "CompletionDate", "CompletionDateType",
    "StudyFirstPostDate", "ResultsFirstPostDate", "LastUpdatePostDate",
    "PrimaryOutcomeMeasure", "PrimaryOutcomeTimeFrame", "SecondaryOutcomeMeasure",
    "EligibilityCriteria", "Sex", "MinimumAge", "StdAge",
    "HasResults",
]

BASE_URL = "https://clinicaltrials.gov/study"


def _dig(d, *path, default=None):
    """Walk a nested dict by key path, returning `default` if any hop is missing."""
    for key in path:
        if not isinstance(d, dict):
            return default
        d = d.get(key)
        if d is None:
            return default
    return d


def profile(study: dict) -> dict:
    """Flatten one full study record into a competitor-monitoring profile."""
    p = study.get("protocolSection", {})
    ident = p.get("identificationModule", {})
    status = p.get("statusModule", {})
    spon = p.get("sponsorCollaboratorsModule", {})
    design = p.get("designModule", {})
    arms = p.get("armsInterventionsModule", {})
    outcomes = p.get("outcomesModule", {})
    elig = p.get("eligibilityModule", {})
    derived = study.get("derivedSection", {})

    nct = ident.get("nctId")

    def date(field):
        s = status.get(field) or {}
        return s.get("date"), s.get("type")

    start, start_type = date("startDateStruct")
    primary_comp, primary_comp_type = date("primaryCompletionDateStruct")
    comp, comp_type = date("completionDateStruct")

    return {
        # --- identity
        "nctId": nct,
        "briefTitle": ident.get("briefTitle"),
        "officialTitle": ident.get("officialTitle"),
        "acronym": ident.get("acronym"),
        "orgStudyId": _dig(ident, "orgStudyIdInfo", "id"),
        "secondaryIds": [s.get("id") for s in ident.get("secondaryIdInfos", [])],
        # --- who
        "leadSponsor": _dig(spon, "leadSponsor", "name"),
        "sponsorClass": _dig(spon, "leadSponsor", "class"),
        "collaborators": [c.get("name") for c in spon.get("collaborators", [])],
        "responsibleParty": _dig(spon, "responsibleParty", "type"),
        # --- what drugs
        "interventions": [i.get("name") for i in arms.get("interventions", [])],
        "interventionTypes": sorted({i.get("type") for i in arms.get("interventions", [])}),
        "armGroups": [a.get("label") for a in arms.get("armGroups", [])],
        "drugMeshTerms": [m["term"] for m in _dig(derived, "interventionBrowseModule", "meshes", default=[])],
        # --- what disease
        "conditions": _dig(p, "conditionsModule", "conditions", default=[]),
        "conditionMeshTerms": [m["term"] for m in _dig(derived, "conditionBrowseModule", "meshes", default=[])],
        "sex": elig.get("sex"),
        "minimumAge": elig.get("minimumAge"),
        # --- design and scale
        "studyType": design.get("studyType"),
        "phases": design.get("phases", []),
        "enrollment": _dig(design, "enrollmentInfo", "count"),
        "enrollmentType": _dig(design, "enrollmentInfo", "type"),
        "allocation": _dig(design, "designInfo", "allocation"),
        "primaryPurpose": _dig(design, "designInfo", "primaryPurpose"),
        "masking": _dig(design, "designInfo", "maskingInfo", "masking"),
        # --- endpoints (titles only; values live on the results page)
        "primaryOutcomes": [o.get("measure") for o in outcomes.get("primaryOutcomes", [])],
        "primaryOutcomeTimeFrames": [o.get("timeFrame") for o in outcomes.get("primaryOutcomes", [])],
        "secondaryOutcomeCount": len(outcomes.get("secondaryOutcomes", [])),
        # --- dates
        "overallStatus": status.get("overallStatus"),
        "whyStopped": status.get("whyStopped"),
        "startDate": start, "startDateType": start_type,
        "primaryCompletionDate": primary_comp, "primaryCompletionDateType": primary_comp_type,
        "completionDate": comp, "completionDateType": comp_type,
        "studyFirstPostDate": _dig(status, "studyFirstPostDateStruct", "date"),
        "resultsFirstPostDate": _dig(status, "resultsFirstPostDateStruct", "date"),
        "lastUpdatePostDate": _dig(status, "lastUpdatePostDateStruct", "date"),
        # --- results (linked, not extracted)
        "hasResults": study.get("hasResults"),
        "resultsUrl": f"{BASE_URL}/{nct}?tab=results" if study.get("hasResults") else None,
    }


def fetch(nct_id: str) -> dict:
    """Fetch one study and return its competitor-monitoring profile."""
    return profile(ctgov.get(nct_id))


if __name__ == "__main__":
    import sys

    for k, v in fetch(sys.argv[1] if len(sys.argv) > 1 else "NCT03412565").items():
        print(f"{k:28} {v}")
