"""Poke at the ClinicalTrials.gov API from the command line.

    python explore.py "lung cancer"
    python explore.py "lung cancer" --limit 100 --status RECRUITING
    python explore.py "lung cancer" --csv trials.csv
    python explore.py --nct NCT02305173          # dump one full study record
"""

import argparse
import json

import ctgov


def main():
    p = argparse.ArgumentParser(description="Search ClinicalTrials.gov")
    p.add_argument("condition", nargs="?", help='condition, e.g. "lung cancer"')
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--status", help="e.g. RECRUITING, COMPLETED, TERMINATED")
    p.add_argument("--nct", help="fetch one full study record by NCT id")
    p.add_argument("--csv", help="write results to this CSV path (needs pandas)")
    args = p.parse_args()

    if args.nct:
        print(json.dumps(ctgov.get(args.nct), indent=2))
        return

    if not args.condition:
        p.error("give a condition, or use --nct")

    extra = {"filter_overallStatus": args.status} if args.status else {}

    total = ctgov.count(cond=args.condition, **extra)
    studies = ctgov.search(cond=args.condition, limit=args.limit, **extra)
    print(f"{total} studies match; showing {len(studies)}\n")

    for s in studies:
        f = ctgov.flatten(s)
        print(f"{f.get('protocolSection.identificationModule.nctId')}  "
              f"[{f.get('protocolSection.statusModule.overallStatus')}] "
              f"{f.get('protocolSection.designModule.phases') or '-'}  "
              f"n={f.get('protocolSection.designModule.enrollmentInfo.count')}")
        print(f"   {f.get('protocolSection.identificationModule.briefTitle')}")

    if args.csv:
        ctgov.to_frame(studies).to_csv(args.csv, index=False)
        print(f"\nwrote {args.csv}")


if __name__ == "__main__":
    main()
