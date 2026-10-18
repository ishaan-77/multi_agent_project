"""Command-line entry point.

    python run.py --deal samples/normal_loan.pdf
    python run.py --deal samples/edge_case_loan.pdf --rules rules/lending_policy.yaml
"""
import argparse
import sys

from src.pipeline import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-agent deal review pipeline")
    parser.add_argument("--deal", required=True, help="Deal document (.pdf, .txt, .md)")
    parser.add_argument("--rules", default="rules/lending_policy.yaml", help="Compliance rule set (YAML)")
    parser.add_argument("--out", default="outputs", help="Output folder")
    args = parser.parse_args()

    print(f"Reviewing {args.deal} against {args.rules} ...")
    report, state = run_pipeline(args.deal, args.rules, args.out)

    for entry in state.get("audit_log", []):
        print(f"  [{entry.agent:>12}] {entry.event}: {entry.detail}")

    matrix = report["compliance_matrix"]
    print(f"\nStatus:      {report['status']}")
    print(f"Compliance:  {sum(c['status'] == 'PASS' for c in matrix)} pass, "
          f"{sum(c['status'] == 'FAIL' for c in matrix)} fail, "
          f"{sum(c['status'] == 'NEEDS_REVIEW' for c in matrix)} needs review")
    print(f"Risks:       {len(report['risk_register'])}")
    print(f"Decision:    {report['decision']} ({len(report['escalations'])} escalations)")
    print(f"Report:      {report.get('output_dir')}/report.md")
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
