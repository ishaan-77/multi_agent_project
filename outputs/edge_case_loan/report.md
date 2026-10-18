# Deal Review Report: BRIDGE LOAN FACILITY AGREEMENT

**Document:** `samples/edge_case_loan.pdf` (3 pages)  
**Policy:** Harborview Commercial Lending Policy (Synthetic) v1.0  
**Run status:** `completed_with_errors`  
**Decision:** 🔴 **ESCALATE TO HUMAN REVIEW**

> Evidence references use `p<page>:<clause>`. For example, `p2:7.2` is page 2, clause 7.2.

## Executive Summary

[Automated fallback - the Risk & Summary LLM was unavailable.] 4 policy breaches and 16 open items were identified by the compliance review. A human reviewer should assess overall credit risk.

## Escalations for Human Review

| Severity | Source | Reason |
|---|---|---|
| critical | `compliance:CR-03` | Maximum loan-to-value failed: ltv_ratio = 88.9% (normalized 0.8889); policy requires <= 0.75. Limit breached. |
| critical | `risk:R-01` | Policy breach: Maximum loan-to-value: ltv_ratio = 88.9% (normalized 0.8889); policy requires <= 0.75. Limit breached. |
| high | `compliance:CR-02` | Pricing fully defined needs human judgment: Compliance LLM unavailable; rule must be checked manually. |
| high | `compliance:CR-04` | Independent collateral valuation needs human judgment: Compliance LLM unavailable; rule must be checked manually. |
| high | `compliance:CR-06` | Minimum DSCR covenant failed: dscr_covenant = not less than 1.10x (normalized 1.1); policy requires >= 1.25. Limit breached. |
| high | `compliance:CR-07` | Guarantee for large facilities needs human judgment: Compliance LLM unavailable; rule must be checked manually. |
| high | `compliance:CR-09` | Core events of default needs human judgment: Compliance LLM unavailable; rule must be checked manually. |
| high | `system` | Agent error: compliance: compliance: failed after 3 attempts: Error calling model 'gemini-3.8-flash' (RESOURCE_EXHAUSTED): 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quot |
| high | `system` | Agent error: risk: risk: failed after 3 attempts: Error calling model 'gemini-3.8-flash' (RESOURCE_EXHAUSTED): 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please ch |
| medium | `compliance:CR-11` | Prepayment terms needs human judgment: Compliance LLM unavailable; rule must be checked manually. |
| medium | `compliance:CR-12` | Internally consistent key dates needs human judgment: Compliance LLM unavailable; rule must be checked manually. |
| medium | `extraction:effective_date` | Low-confidence term 'effective_date' (0.40): Conflict between Clause 2 (1 April 2026) and Schedule 1 (1 May 2026). |
| medium | `extraction:margin_pct` | Low-confidence term 'margin_pct' (0.30): Applicable margin is undefined in this agreement and deferred to a separate fee letter. |
| medium | `extraction:leverage_covenant` | Low-confidence term 'leverage_covenant' (0.40): Levels are undefined in the agreement and remain to be agreed between the parties. |
| low | `compliance:CR-10` | Governing law and jurisdiction needs human judgment: Compliance LLM unavailable; rule must be checked manually. |
| low | `compliance:CR-13` | Use-of-proceeds restrictions needs human judgment: Compliance LLM unavailable; rule must be checked manually. |

## Compliance Matrix

1 pass · 4 fail · 8 needs review

| Rule | Name | Severity | Result | Evidence | Rationale | Method |
|---|---|---|---|---|---|---|
| CR-01 | Single-borrower exposure limit | high | ✅ PASS | `p1:3.1` | principal_amount = USD 40,000,000 (normalized 40,000,000); policy requires <= 50,000,000 USD. Within limit. | deterministic |
| CR-02 | Pricing fully defined | high | ⚠️ REVIEW | — | Compliance LLM unavailable; rule must be checked manually. | llm |
| CR-03 | Maximum loan-to-value | critical | ❌ FAIL | `p1:3.1`, `p2:6.2` | ltv_ratio = 88.9% (normalized 0.8889); policy requires <= 0.75. Limit breached. | deterministic |
| CR-04 | Independent collateral valuation | high | ⚠️ REVIEW | — | Compliance LLM unavailable; rule must be checked manually. | llm |
| CR-05 | Maximum tenor | medium | ❌ FAIL | `p1:2.1`, `p3:S1.1`, `p2:5.2`, `p3:S1.3` | tenor_years = 10.0 years (normalized 10); policy requires <= 7. Breaches the limit even on a low-confidence value (0.40): derived: maturity_date - effective_date \| effective_date: Conflict between Clause 2 (1 April 2026) and Schedule 1 (1 May 2026). | deterministic |
| CR-06 | Minimum DSCR covenant | high | ❌ FAIL | `p2:7.1` | dscr_covenant = not less than 1.10x (normalized 1.1); policy requires >= 1.25. Limit breached. | deterministic |
| CR-07 | Guarantee for large facilities | high | ⚠️ REVIEW | — | Compliance LLM unavailable; rule must be checked manually. | llm |
| CR-08 | Audited financial reporting | medium | ❌ FAIL | `p2:8.1` | audited_financials_days = within 180 days after the end of each financial year (normalized 180); policy requires <= 120. Limit breached. | deterministic |
| CR-09 | Core events of default | high | ⚠️ REVIEW | — | Compliance LLM unavailable; rule must be checked manually. | llm |
| CR-10 | Governing law and jurisdiction | low | ⚠️ REVIEW | — | Compliance LLM unavailable; rule must be checked manually. | llm |
| CR-11 | Prepayment terms | medium | ⚠️ REVIEW | — | Compliance LLM unavailable; rule must be checked manually. | llm |
| CR-12 | Internally consistent key dates | medium | ⚠️ REVIEW | — | Compliance LLM unavailable; rule must be checked manually. | llm |
| CR-13 | Use-of-proceeds restrictions | low | ⚠️ REVIEW | — | Compliance LLM unavailable; rule must be checked manually. | llm |

## Risk Register (prioritized)

| ID | Severity | Likelihood | Category | Risk | Evidence | Recommendation |
|---|---|---|---|---|---|---|
| R-01 | critical | high | financial | **Policy breach: Maximum loan-to-value**: ltv_ratio = 88.9% (normalized 0.8889); policy requires <= 0.75. Limit breached. | `p1:3.1`, `p2:6.2` | Resolve CR-03 before approval or obtain a documented policy exception. |
| R-02 | high | high | financial | **Policy breach: Minimum DSCR covenant**: dscr_covenant = not less than 1.10x (normalized 1.1); policy requires >= 1.25. Limit breached. | `p2:7.1` | Resolve CR-06 before approval or obtain a documented policy exception. |
| R-03 | medium | high | financial | **Policy breach: Maximum tenor**: tenor_years = 10.0 years (normalized 10); policy requires <= 7. Breaches the limit even on a low-confidence value (0.40): derived: maturity_date - effective_date \| effective_date: Conflict between Clause 2 (1 April 2026) and Schedule 1 (1 May 2026). | `p1:2.1`, `p3:S1.1`, `p2:5.2`, `p3:S1.3` | Resolve CR-05 before approval or obtain a documented policy exception. |
| R-04 | medium | high | operational | **Policy breach: Audited financial reporting**: audited_financials_days = within 180 days after the end of each financial year (normalized 180); policy requires <= 120. Limit breached. | `p2:8.1` | Resolve CR-08 before approval or obtain a documented policy exception. |

## Missing or Ambiguous Information

- Not found in document: guarantor
- Not found in document: default_interest
- Not found in document: prepayment_terms
- Not found in document: guarantee
- Not found in document: other_covenants
- Not found in document: conditions_precedent
- Not found in document: use_of_proceeds_restrictions
- Not found in document: exclusions
- CR-02 Pricing fully defined: Compliance LLM unavailable; rule must be checked manually.
- CR-04 Independent collateral valuation: Compliance LLM unavailable; rule must be checked manually.
- CR-07 Guarantee for large facilities: Compliance LLM unavailable; rule must be checked manually.
- CR-09 Core events of default: Compliance LLM unavailable; rule must be checked manually.
- CR-10 Governing law and jurisdiction: Compliance LLM unavailable; rule must be checked manually.
- CR-11 Prepayment terms: Compliance LLM unavailable; rule must be checked manually.
- CR-12 Internally consistent key dates: Compliance LLM unavailable; rule must be checked manually.
- CR-13 Use-of-proceeds restrictions: Compliance LLM unavailable; rule must be checked manually.

## Follow-up Actions

1. Re-run the risk analysis when the LLM is available.
2. Address: Policy breach: Maximum loan-to-value
3. Address: Policy breach: Maximum tenor
4. Address: Policy breach: Minimum DSCR covenant
5. Address: Policy breach: Audited financial reporting

## Extracted Terms

| Term | Value | Evidence | Confidence | Verified | Notes |
|---|---|---|---|---|---|
| lender | Harborview Commercial Bank N.A. | `p1:1.1` | 1.00 | ✅ |  |
| borrower | Coastal Ridge Developers LLC | `p1:1.2` | 1.00 | ✅ |  |
| facility_type | bridge loan facility | `p1:3.1` | 1.00 | ✅ |  |
| principal_amount | USD 40,000,000 | `p1:3.1` | 1.00 | ✅ |  |
| purpose | general corporate purposes, including the development of the Bayfront Parcel | `p1:3.2` | 1.00 | ✅ |  |
| effective_date | 2026-04-01 / 2026-05-01 | `p1:2.1`, `p3:S1.1` | 0.40 | ✅ | Conflict between Clause 2 (1 April 2026) and Schedule 1 (1 May 2026). |
| interest_rate | Term SOFR plus the Applicable Margin | `p1:4.1` | 0.90 | ✅ |  |
| margin_pct | margin determined by the parties in a separate fee letter | `p1:2.2` | 0.30 | ✅ | Applicable margin is undefined in this agreement and deferred to a separate fee letter. |
| interest_payment_frequency | at such intervals as the Lender may notify from time to time | `p1:4.2` | 0.70 | ✅ | Payment frequency is discretionary at Lender notification rather than fixed. |
| first_repayment_date | 2026-06-30 | `p2:5.1`, `p3:S1.2` | 1.00 | ✅ |  |
| maturity_date | 2036-03-31 | `p2:5.2`, `p3:S1.3` | 1.00 | ✅ |  |
| repayment_schedule | repaid in instalments as set out in Schedule 1: first falling due on 30 June 2026; thereafter quarterly instalments of USD 1,000,000 | `p2:5.1`, `p3:S1.2` | 1.00 | ✅ |  |
| collateral_description | mortgage over the Bayfront Parcel, Lots 14-19, Pinellas County, Florida | `p2:6.1` | 1.00 | ✅ |  |
| collateral_value | USD 45,000,000 | `p2:6.2` | 0.70 | ✅ | Stated figure is Borrower's preliminary internal estimate; valuation report to be delivered post-Effective Date. |
| collateral_valuation_source | Borrower's preliminary internal estimate (valuation report to be delivered after Effective Date) | `p2:6.2` | 0.80 | ✅ |  |
| dscr_covenant | not less than 1.10x | `p2:7.1` | 1.00 | ✅ |  |
| leverage_covenant | to be agreed between the parties | `p2:7.2` | 0.40 | ✅ | Levels are undefined in the agreement and remain to be agreed between the parties. |
| audited_financials_days | within 180 days after the end of each financial year | `p2:8.1` | 1.00 | ✅ |  |
| events_of_default | Non-payment (failure to pay any amount when due); Insolvency (any insolvency proceeding commenced against Borrower) | `p3:9.1`, `p3:9.2` | 1.00 | ✅ |  |
| governing_law | laws of the State of Florida; Pinellas County non-exclusive jurisdiction | `p3:11.1` | 1.00 | ✅ |  |
| ltv_ratio | 88.9% | `p1:3.1`, `p2:6.2` | 0.70 | ✅ | derived: principal_amount / collateral_value \| collateral_value: Stated figure is Borrower's preliminary internal estimate; valuation report to be delivered post-Effective Date. |
| tenor_years | 10.0 years | `p1:2.1`, `p3:S1.1`, `p2:5.2`, `p3:S1.3` | 0.40 | ✅ | derived: maturity_date - effective_date \| effective_date: Conflict between Clause 2 (1 April 2026) and Schedule 1 (1 May 2026). |

**Not found in document:** guarantor, default_interest, prepayment_terms, guarantee, other_covenants, conditions_precedent, use_of_proceeds_restrictions, exclusions

## Errors

- compliance: compliance: failed after 3 attempts: Error calling model 'gemini-3.8-flash' (RESOURCE_EXHAUSTED): 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-3.8-flash\nPlease retry in 15h20m14.534470286s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://ai.google.dev/gemini-api/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-3.8-flash'}, 'quotaValue': '20'}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '55214s'}]}}
- risk: risk: failed after 3 attempts: Error calling model 'gemini-3.8-flash' (RESOURCE_EXHAUSTED): 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-3.8-flash\nPlease retry in 15h17m57.947554725s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://ai.google.dev/gemini-api/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-3.8-flash'}, 'quotaValue': '20'}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '55077s'}]}}
