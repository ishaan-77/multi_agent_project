"""Generate the two synthetic deal PDFs used to validate the pipeline.

Run from the project root:  python -m scripts.make_samples

  samples/normal_loan.pdf     - clean deal, should pass nearly every rule
  rules/lending_policy.pdf    - the same 13 rules written as a prose policy, to test the
                                Policy Parser (rules from a document instead of YAML)
  samples/edge_case_loan.pdf  - deliberately flawed deal: LTV breach, undefined margin,
                                conflicting dates, missing guarantee/prepayment/cross-default,
                                weak covenants. Should trigger human escalation.

All names, companies and figures are fictional.
"""
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

OUT = Path(__file__).resolve().parent.parent / "samples"
BANNER = "SYNTHETIC DOCUMENT - FICTIONAL PARTIES - FOR TESTING ONLY"

# Each section: (number, heading, [(clause_no, text), ...]); "PAGE" forces a page break.
NORMAL = {
    "title": "TERM LOAN FACILITY AGREEMENT",
    "ref": "Agreement No. HCB-TL-2026-0147",
    "sections": [
        ("1", "Parties", [
            ("1.1", "Lender: Harborview Commercial Bank N.A., a national banking association (the \"Lender\")."),
            ("1.2", "Borrower: Northwind Fabrication Ltd., a Delaware corporation (the \"Borrower\")."),
            ("1.3", "Guarantor: Northwind Holdings Inc., the parent company of the Borrower (the \"Guarantor\")."),
        ]),
        ("2", "Definitions", [
            ("2.1", "\"Effective Date\" means 1 March 2026."),
            ("2.2", "\"Term SOFR\" means the 3-month forward-looking term rate based on SOFR published by CME Group Benchmark Administration Ltd."),
            ("2.3", "\"Business Day\" means a day on which banks are open for general business in New York."),
        ]),
        ("3", "The Facility", [
            ("3.1", "The Lender makes available to the Borrower a senior secured term loan facility in an aggregate amount of USD 12,000,000 (twelve million US dollars)."),
            ("3.2", "Purpose: the Borrower shall apply all amounts borrowed towards the acquisition of CNC machinery and the expansion of its Plant 2 manufacturing facility."),
            ("3.3", "Availability Period: the facility may be drawn in up to three tranches within 90 days of the Effective Date."),
        ]),
        ("4", "Interest", [
            ("4.1", "The rate of interest on the loan is Term SOFR plus a margin of 2.75% per annum."),
            ("4.2", "If Term SOFR is less than 0.50%, Term SOFR shall be deemed to be 0.50%."),
            ("4.3", "Interest is payable quarterly in arrears on the last day of each March, June, September and December."),
            ("4.4", "Default interest of an additional 2.00% per annum applies to any overdue amount."),
        ]),
        "PAGE",
        ("5", "Repayment and Maturity", [
            ("5.1", "The Borrower shall repay the loan in 20 equal quarterly instalments, the first falling due on 30 June 2026."),
            ("5.2", "The Final Maturity Date is 31 March 2031, on which all outstanding amounts are due."),
        ]),
        ("6", "Prepayment", [
            ("6.1", "Voluntary prepayment is permitted on 30 days' prior written notice in minimum amounts of USD 500,000. A prepayment fee of 1.00% applies in year one, 0.50% in year two and nil thereafter."),
            ("6.2", "Mandatory prepayment: net proceeds of any asset disposal exceeding USD 1,000,000 shall be applied in prepayment of the loan."),
        ]),
        ("7", "Security and Collateral", [
            ("7.1", "The loan is secured by a first-priority security interest over all machinery and equipment located at Plant 2, 4100 Industrial Way, Dayton, Ohio."),
            ("7.2", "An independent appraisal by Calder & Wynn Valuation Partners dated 15 January 2026 valued the collateral at USD 18,500,000."),
            ("7.3", "The Borrower shall keep the collateral insured at full replacement value with the Lender named as loss payee."),
        ]),
        ("8", "Guarantee", [
            ("8.1", "The Guarantor unconditionally and irrevocably guarantees the punctual performance of all of the Borrower's obligations under this Agreement."),
        ]),
        ("9", "Financial Covenants", [
            ("9.1", "Debt Service Coverage Ratio: the Borrower shall maintain a DSCR of not less than 1.35x, tested quarterly on a rolling twelve-month basis."),
            ("9.2", "Leverage: the ratio of Total Debt to EBITDA shall not exceed 3.0x."),
            ("9.3", "Minimum Tangible Net Worth: the Borrower shall maintain tangible net worth of at least USD 25,000,000."),
        ]),
        "PAGE",
        ("10", "Information Undertakings", [
            ("10.1", "The Borrower shall deliver audited annual financial statements within 120 days after the end of each financial year."),
            ("10.2", "The Borrower shall deliver unaudited quarterly financial statements and a compliance certificate within 45 days after each quarter end."),
        ]),
        ("11", "Events of Default", [
            ("11.1", "Non-payment: the Borrower fails to pay any amount when due and the failure is not remedied within 5 Business Days."),
            ("11.2", "Financial covenants: any requirement of Clause 9 is not satisfied."),
            ("11.3", "Cross-default: any Financial Indebtedness of the Borrower exceeding USD 2,000,000 is declared due before its specified maturity."),
            ("11.4", "Insolvency: the Borrower is unable to pay its debts as they fall due or any insolvency proceeding is commenced."),
            ("11.5", "Change of control: the Guarantor ceases to own at least 51% of the Borrower."),
        ]),
        ("12", "Conditions Precedent", [
            ("12.1", "First drawdown is conditional on receipt of board resolutions, a legal opinion, the appraisal referred to in Clause 7.2, insurance certificates and completed KYC documentation."),
        ]),
        ("13", "Restrictions and Exclusions", [
            ("13.1", "Loan proceeds shall not be used to pay dividends, repurchase shares or fund speculative trading."),
            ("13.2", "The Lender shall not be liable for any indirect or consequential loss."),
        ]),
        ("14", "Governing Law and Jurisdiction", [
            ("14.1", "This Agreement is governed by the laws of the State of New York. The courts of New York County have exclusive jurisdiction."),
        ]),
    ],
}

EDGE = {
    "title": "BRIDGE LOAN FACILITY AGREEMENT",
    "ref": "Agreement No. HCB-BL-2026-0322",
    "sections": [
        ("1", "Parties", [
            ("1.1", "Lender: Harborview Commercial Bank N.A. (the \"Lender\")."),
            ("1.2", "Borrower: Coastal Ridge Developers LLC, a Florida limited liability company (the \"Borrower\")."),
        ]),
        ("2", "Definitions", [
            ("2.1", "\"Effective Date\" means 1 April 2026."),
            ("2.2", "\"Applicable Margin\" means the margin determined by the parties in a separate fee letter."),
        ]),
        ("3", "The Facility", [
            ("3.1", "The Lender makes available to the Borrower a bridge loan facility in an aggregate amount of USD 40,000,000."),
            ("3.2", "Purpose: general corporate purposes, including the development of the Bayfront Parcel."),
        ]),
        ("4", "Interest", [
            ("4.1", "The rate of interest on the loan is Term SOFR plus the Applicable Margin."),
            ("4.2", "Interest is payable at such intervals as the Lender may notify from time to time."),
        ]),
        "PAGE",
        ("5", "Repayment and Maturity", [
            ("5.1", "The loan shall be repaid in instalments as set out in Schedule 1, the first falling due on 30 June 2026."),
            ("5.2", "The Final Maturity Date is 31 March 2036."),
        ]),
        ("6", "Security", [
            ("6.1", "The loan is secured by a mortgage over the Bayfront Parcel, Lots 14-19, Pinellas County, Florida."),
            ("6.2", "The value of the collateral shall be as stated in a valuation report to be delivered after the Effective Date. The Borrower's preliminary internal estimate of the Bayfront Parcel is USD 45,000,000."),
        ]),
        ("7", "Financial Covenants", [
            ("7.1", "The Borrower shall maintain a Debt Service Coverage Ratio of not less than 1.10x."),
            ("7.2", "Leverage covenant levels are to be agreed between the parties."),
            ("7.3", "The Lender may, in its sole discretion, waive any financial covenant without notice."),
        ]),
        ("8", "Information Undertakings", [
            ("8.1", "The Borrower shall deliver audited annual financial statements within 180 days after the end of each financial year."),
        ]),
        "PAGE",
        ("9", "Events of Default", [
            ("9.1", "Non-payment: the Borrower fails to pay any amount when due."),
            ("9.2", "Insolvency: any insolvency proceeding is commenced against the Borrower."),
        ]),
        ("10", "[Intentionally left blank]", [
            ("10.1", "[Reserved.]"),
        ]),
        ("11", "Governing Law", [
            ("11.1", "This Agreement is governed by the laws of the State of Florida. The courts of Pinellas County have non-exclusive jurisdiction."),
        ]),
        ("SCHEDULE 1", "Key Dates and Repayment Schedule", [
            ("S1.1", "Effective Date: 1 May 2026."),
            ("S1.2", "First repayment: 30 June 2026; thereafter quarterly instalments of USD 1,000,000."),
            ("S1.3", "Final Maturity Date: 31 March 2036."),
        ]),
    ],
}

POLICY = {
    "title": "HARBORVIEW COMMERCIAL LENDING POLICY",
    "ref": "Credit Policy CP-2026 (written version of rules/lending_policy.yaml)",
    "sections": [
        ("1", "Credit Limits", [
            ("1.1", "Exposure limit. The principal of any single facility must not exceed USD 50,000,000. Severity: high."),
            ("1.2", "Loan-to-value. The loan-to-value ratio must not exceed 75%, measured against an independent collateral valuation. Severity: critical."),
            ("1.3", "Independent valuation. Collateral must be described and supported by a dated valuation from an independent appraiser; a borrower estimate or a valuation still to be delivered is not acceptable. Severity: high."),
            ("1.4", "Tenor. The final maturity date must be no more than 7 years after the effective date. Severity: medium."),
            ("1.5", "Guarantee. Facilities above USD 10,000,000 require a parent or third-party guarantee. Severity: high."),
        ]),
        ("2", "Pricing and Covenants", [
            ("2.1", "Pricing. The interest rate must be fully defined, either as a numeric fixed rate or as a named benchmark plus a numeric margin. A margin left to a separate letter that is not provided does not comply. Severity: high."),
            ("2.2", "Debt service coverage. The agreement must include a debt service coverage ratio covenant of at least 1.25x. Severity: high."),
        ]),
        ("3", "Reporting and Legal Terms", [
            ("3.1", "Audited accounts. Audited annual financial statements must be delivered within 120 days of the financial year end. Severity: medium."),
            ("3.2", "Events of default. The events of default must include payment default, cross-default and insolvency. Severity: high."),
            ("3.3", "Governing law. The agreement must state a governing law and a forum for disputes. Severity: low."),
            ("3.4", "Prepayment. Voluntary and mandatory prepayment terms must be specified. Severity: medium."),
            ("3.5", "Key dates. The effective date, first repayment date and maturity date must be stated consistently wherever they appear. Severity: medium."),
            ("3.6", "Use of proceeds. The agreement must state the purpose of the loan and restrict prohibited uses of the proceeds. Severity: low."),
        ]),
    ],
}


def build(spec: dict, path: Path) -> None:
    styles = getSampleStyleSheet()
    banner = ParagraphStyle("banner", parent=styles["Normal"], fontSize=8, textColor="#B00020", alignment=1)
    clause = ParagraphStyle("clause", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=6)

    story = [
        Paragraph(BANNER, banner),
        Spacer(1, 0.2 * inch),
        Paragraph(spec["title"], styles["Title"]),
        Paragraph(spec["ref"], styles["Normal"]),
        Spacer(1, 0.25 * inch),
    ]
    for section in spec["sections"]:
        if section == "PAGE":
            story.append(PageBreak())
            continue
        num, heading, clauses = section
        label = num if num.startswith("SCHEDULE") else f"{num}."
        story.append(Paragraph(f"{label} {heading}", styles["Heading2"]))
        for cno, text in clauses:
            story.append(Paragraph(f"<b>{cno}</b>&nbsp;&nbsp;{text}", clause))

    def footer(canvas, doc):
        canvas.setFont("Helvetica", 8)
        canvas.drawString(inch, 0.6 * inch, f"{spec['ref']}  |  {BANNER}")
        canvas.drawRightString(LETTER[0] - inch, 0.6 * inch, f"Page {doc.page}")

    SimpleDocTemplate(str(path), pagesize=LETTER, title=spec["title"]).build(
        story, onFirstPage=footer, onLaterPages=footer
    )
    print(f"wrote {path}")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    build(NORMAL, OUT / "normal_loan.pdf")
    build(EDGE, OUT / "edge_case_loan.pdf")
    build(POLICY, OUT.parent / "rules" / "lending_policy.pdf")
