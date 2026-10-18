# Deal Review Report: TERM LOAN FACILITY AGREEMENT

**Document:** `samples/normal_loan.pdf` (3 pages)  
**Policy:** Harborview Commercial Lending Policy (Synthetic) v1.0  
**Run status:** `completed`  
**Decision:** 🟢 **No escalation required**

> Evidence references use `p<page>:<clause>`. For example, `p2:7.2` is page 2, clause 7.2.

## Executive Summary

Harborview Commercial Bank N.A. proposes to extend a USD 12,000,000 senior secured term loan facility to Northwind Fabrication Ltd., supported by an unconditional parent guarantee from Northwind Holdings Inc. The facility features a 5.1-year tenor, quarterly principal amortization across 20 instalments, and interest set at Term SOFR plus 2.75% with a 0.50% floor. Loan proceeds will fund CNC machinery procurement and expansion of the Borrower's Plant 2 site in Dayton, Ohio. The credit profile is robust, with all 13 credit policy criteria fully satisfied. Collateral security provides healthy coverage with an initial loan-to-value ratio of 64.9% based on an independent appraisal of USD 18,500,000. Core covenants require a minimum 1.35x DSCR, maximum 3.0x leverage, and tangible net worth of at least USD 25,000,000. Primary issues involve missing definitions for critical covenant terms (EBITDA, Debt Service, and Financial Indebtedness) and long-term equipment depreciation. Recommendation is to approve with conditions, subject to finalizing legal definitions, verifying UCC perfection, and conditioning tranche drawdowns on documented machinery acquisition expenditures.

## Compliance Matrix

13 pass · 0 fail · 0 needs review

| Rule | Name | Severity | Result | Evidence | Rationale | Method |
|---|---|---|---|---|---|---|
| CR-01 | Single-borrower exposure limit | high | ✅ PASS | `p1:3.1` | principal_amount = USD 12,000,000 (normalized 12,000,000); policy requires <= 50,000,000 USD. Within limit. | deterministic |
| CR-02 | Pricing fully defined | high | ✅ PASS | `p1:4.1` | The interest rate is fully defined by specifying a recognized benchmark (Term SOFR) and a fixed numeric margin of 2.75% per annum. | llm |
| CR-03 | Maximum loan-to-value | critical | ✅ PASS | `p1:3.1`, `p2:7.2` | ltv_ratio = 64.9% (normalized 0.6486); policy requires <= 0.75. Within limit. | deterministic |
| CR-04 | Independent collateral valuation | high | ✅ PASS | `p2:7.1`, `p2:7.2` | The collateral is clearly described and supported by a dated valuation of USD 18,500,000 from an independent appraisal firm. | llm |
| CR-05 | Maximum tenor | medium | ✅ PASS | `p1:2.1`, `p2:5.2` | tenor_years = 5.1 years (normalized 5.08); policy requires <= 7. Within limit. | deterministic |
| CR-06 | Minimum DSCR covenant | high | ✅ PASS | `p2:9.1` | dscr_covenant = not less than 1.35x (normalized 1.35); policy requires >= 1.25. Within limit. | deterministic |
| CR-07 | Guarantee for large facilities | high | ✅ PASS | `p1:3.1`, `p2:8.1` | The facility amount is USD 12,000,000, exceeding the USD 10,000,000 threshold, and is fully covered by an unconditional guarantee from parent company Northwind Holdings Inc. | llm |
| CR-08 | Audited financial reporting | medium | ✅ PASS | `p3:10.1` | audited_financials_days = 120 days after the end of each financial year (normalized 120); policy requires <= 120. Within limit. | deterministic |
| CR-09 | Core events of default | high | ✅ PASS | `p3:11.1`, `p3:11.3`, `p3:11.4` | The agreement explicitly includes non-payment, cross-default, and insolvency among its specified events of default. | llm |
| CR-10 | Governing law and jurisdiction | low | ✅ PASS | `p3:14.1` | The contract clearly designates the laws of the State of New York as governing law and selects the courts of New York County as the forum for dispute resolution. | llm |
| CR-11 | Prepayment terms | medium | ✅ PASS | `p2:6.1`, `p2:6.2` | The agreement defines both voluntary prepayment terms, including notice periods and fee schedules, and mandatory prepayment requirements from asset disposal proceeds. | llm |
| CR-12 | Internally consistent key dates | medium | ✅ PASS | `p1:2.1`, `p2:5.1`, `p2:5.2` | The Effective Date, first repayment date, and final maturity date are explicitly stated without any internal contradictions or conflicting dates across the document. | llm |
| CR-13 | Use-of-proceeds restrictions | low | ✅ PASS | `p1:3.2`, `p3:13.1` | The agreement defines the permitted purpose of the loan and explicitly prohibits specific uses of proceeds, including dividends, share repurchases, and speculative trading. | llm |

## Risk Register (prioritized)

| ID | Severity | Likelihood | Category | Risk | Evidence | Recommendation |
|---|---|---|---|---|---|---|
| R-01 | medium | high | legal | **Undefined Financial Covenant Metrics**: Clause 9 establishes financial covenants including a DSCR of 1.35x and a Total Debt to EBITDA leverage cap of 3.0x, but Section 2 provides no definitions for EBITDA, Total Debt, or Debt Service components, creating potential contractual disputes over calculation methodology. | `p2:9.1`, `p2:9.2` | Incorporate standard market definitions for EBITDA, Total Debt, and Debt Service in Section 2, accompanied by an agreed compliance certificate template. |
| R-02 | medium | medium | financial | **Machinery Collateral Depreciation and Realization Risk**: The USD 12,000,000 facility is secured solely by Plant 2 machinery and equipment appraised at USD 18,500,000. Industrial manufacturing machinery is prone to wear, technological obsolescence, and secondary market discounts upon liquidation, which may deteriorate the 64.9% LTV buffer over the 5-year term. | `p2:7.1`, `p2:7.2` | Require periodic updated machinery valuations during the loan tenor and maintain mandatory ongoing inspection rights and active replacement-value insurance coverage. |
| R-03 | medium | low | operational | **Tranche Drawdown and Capital Project Execution Risk**: Proceeds are designated for purchasing CNC machinery and expanding Plant 2, with drawdowns permitted in up to three tranches over 90 days. Supply chain delays, equipment delivery bottlenecks, or facility commissioning issues could impair scheduled operational ramp-up. | `p1:3.2`, `p1:3.3` | Tie subsequent tranche disbursements to verified proof of equipment purchase orders, invoices, and delivery milestones. |
| R-04 | low | medium | legal | **Undefined Financial Indebtedness in Cross-Default Clause**: Clause 11.3 triggers an event of default if Financial Indebtedness exceeding USD 2,000,000 is accelerated, but 'Financial Indebtedness' is not defined, leaving ambiguity regarding whether capital leases, trade payables, or intercompany balances are included. | `p3:11.3` | Add a comprehensive definition of Financial Indebtedness in Section 2 to clearly delineate covered borrowing categories and carve out customary ordinary-course liabilities. |

## Missing or Ambiguous Information

- Definitions for key financial covenant terms including 'EBITDA', 'Total Debt', and 'Debt Service' are omitted from Section 2.
- The term 'Financial Indebtedness' referenced in Clause 11.3 (Cross-default) is not defined in Section 2.
- The form and specific line-item calculations for the quarterly compliance certificate referenced in Clause 10.2 are not attached or scheduled.
- Specific collateral perfection mechanisms (such as UCC-1 filing requirements and landlord or mortgagee waivers for Plant 2 at 4100 Industrial Way) are not detailed under Conditions Precedent in Clause 12.1.

## Follow-up Actions

1. Amend Section 2 of the loan agreement to insert clear contractual definitions for 'EBITDA', 'Total Debt', 'Debt Service', and 'Financial Indebtedness'.
2. Attach an agreed standard quarterly Compliance Certificate template specifying the exact calculation formulas for all financial covenants.
3. Perform UCC lien searches and confirm first-priority security perfection over the machinery and equipment located at 4100 Industrial Way, Dayton, Ohio.
4. Condition second and third tranche disbursements within the 90-day availability period on receipt of verified capital expenditure invoices and equipment installation milestones.
5. Obtain and verify certificates of insurance demonstrating replacement-value equipment coverage and designating Harborview Commercial Bank N.A. as loss payee prior to first drawdown.

## Extracted Terms

| Term | Value | Evidence | Confidence | Verified | Notes |
|---|---|---|---|---|---|
| lender | Harborview Commercial Bank N.A. | `p1:1.1` | 1.00 | ✅ |  |
| borrower | Northwind Fabrication Ltd. | `p1:1.2` | 1.00 | ✅ |  |
| guarantor | Northwind Holdings Inc. | `p1:1.3` | 1.00 | ✅ |  |
| facility_type | senior secured term loan facility | `p1:3.1` | 1.00 | ✅ |  |
| principal_amount | USD 12,000,000 | `p1:3.1` | 1.00 | ✅ |  |
| effective_date | 2026-03-01 | `p1:2.1` | 1.00 | ✅ |  |
| first_repayment_date | 2026-06-30 | `p2:5.1` | 1.00 | ✅ |  |
| maturity_date | 2031-03-31 | `p2:5.2` | 1.00 | ✅ |  |
| interest_rate | Term SOFR plus a margin of 2.75% per annum, subject to a 0.50% floor | `p1:4.1`, `p1:4.2` | 0.95 | ✅ |  |
| margin_pct | 2.75% | `p1:4.1` | 1.00 | ✅ |  |
| interest_payment_frequency | quarterly in arrears on the last day of each March, June, September and December | `p1:4.3` | 1.00 | ✅ |  |
| default_interest | additional 2.00% per annum | `p1:4.4` | 1.00 | ✅ |  |
| repayment_schedule | 20 equal quarterly instalments | `p2:5.1` | 1.00 | ✅ |  |
| prepayment_terms | Voluntary prepayment on 30 days' notice, minimum USD 500,000 (fee: 1.00% year 1, 0.50% year 2, nil thereafter); mandatory prepayment from net proceeds of asset disposal exceeding USD 1,000,000 | `p2:6.1`, `p2:6.2` | 0.95 | ✅ |  |
| collateral_description | first-priority security interest over all machinery and equipment located at Plant 2, 4100 Industrial Way, Dayton, Ohio | `p2:7.1` | 1.00 | ✅ |  |
| collateral_value | USD 18,500,000 | `p2:7.2` | 1.00 | ✅ |  |
| collateral_valuation_source | independent appraisal by Calder & Wynn Valuation Partners dated 15 January 2026 | `p2:7.2` | 1.00 | ✅ |  |
| guarantee | unconditionally and irrevocably guarantees the punctual performance of all of the Borrower's obligations under this Agreement | `p2:8.1` | 1.00 | ✅ |  |
| dscr_covenant | not less than 1.35x | `p2:9.1` | 1.00 | ✅ |  |
| leverage_covenant | Total Debt to EBITDA shall not exceed 3.0x | `p2:9.2` | 1.00 | ✅ |  |
| other_covenants | maintain tangible net worth of at least USD 25,000,000 | `p2:9.3` | 1.00 | ✅ |  |
| audited_financials_days | 120 days after the end of each financial year | `p3:10.1` | 1.00 | ✅ |  |
| events_of_default | Non-payment unremedied within 5 Business Days, breach of financial covenants, cross-default exceeding USD 2,000,000, insolvency, and change of control (Guarantor ceasing to own at least 51%) | `p3:11.1`, `p3:11.2`, `p3:11.3`, `p3:11.4`, `p3:11.5` | 1.00 | ✅ |  |
| conditions_precedent | board resolutions, legal opinion, appraisal referred to in Clause 7.2, insurance certificates, and completed KYC documentation | `p3:12.1` | 1.00 | ✅ |  |
| purpose | acquisition of CNC machinery and the expansion of its Plant 2 manufacturing facility | `p1:3.2` | 1.00 | ✅ |  |
| use_of_proceeds_restrictions | shall not be used to pay dividends, repurchase shares or fund speculative trading | `p3:13.1` | 1.00 | ✅ |  |
| exclusions | Lender shall not be liable for any indirect or consequential loss | `p3:13.2` | 1.00 | ✅ |  |
| governing_law | laws of the State of New York, exclusive jurisdiction of New York County courts | `p3:14.1` | 1.00 | ✅ |  |
| ltv_ratio | 64.9% | `p1:3.1`, `p2:7.2` | 1.00 | ✅ | derived: principal_amount / collateral_value |
| tenor_years | 5.1 years | `p1:2.1`, `p2:5.2` | 1.00 | ✅ | derived: maturity_date - effective_date |
