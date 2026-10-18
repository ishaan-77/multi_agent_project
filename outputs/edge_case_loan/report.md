# Deal Review Report: BRIDGE LOAN FACILITY AGREEMENT

**Document:** `samples/edge_case_loan.pdf` (3 pages)  
**Policy:** HARBORVIEW COMMERCIAL LENDING POLICY Credit Policy CP-2026 vparsed  
**Run status:** `failed`  
**Decision:** 🔴 **ESCALATE TO HUMAN REVIEW**

> Evidence references use `p<page>:<clause>`. For example, `p2:7.2` is page 2, clause 7.2.

## Escalations for Human Review

| Severity | Source | Reason |
|---|---|---|
| critical | `orchestrator` | Pipeline could not complete; the deal must be reviewed manually. |
| high | `system` | Agent error: extraction: extraction: daily API quota exhausted, not retrying: Error calling model 'gemini-3.8-flash' (RESOURCE_EXHAUSTED): 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded y |

## Rules Parsed from the Policy Document

These rules were read from the policy by the Policy Parser. Check them before relying on the results.

| Rule | Name | Check | Limit | Severity | Source | Traced |
|---|---|---|---|---|---|---|
| 1.1 | Exposure limit | threshold | `principal_amount <= 5e+07` | high | `pol:p1:1.1` | ✅ |
| 1.2 | Loan-to-value | threshold | `ltv_ratio <= 0.75` | critical | `pol:p1:1.2` | ✅ |
| 1.3 | Independent valuation | judgment | `—` | high | `pol:p1:1.3` | ✅ |
| 1.4 | Tenor | threshold | `tenor_years <= 7` | medium | `pol:p1:1.4` | ✅ |
| 1.5 | Guarantee | judgment | `—` | high | `pol:p1:1.5` | ✅ |
| 2.1 | Pricing | judgment | `—` | high | `pol:p1:2.1` | ✅ |
| 2.2 | Debt service coverage | threshold | `dscr_covenant >= 1.25` | high | `pol:p1:2.2` | ✅ |
| 3.1 | Audited accounts | threshold | `audited_financials_days <= 120` | medium | `pol:p1:3.1` | ✅ |
| 3.2 | Events of default | judgment | `—` | high | `pol:p1:3.2` | ✅ |
| 3.3 | Governing law | presence | `—` | low | `pol:p1:3.3` | ✅ |
| 3.4 | Prepayment | presence | `—` | medium | `pol:p1:3.4` | ✅ |
| 3.5 | Key dates | judgment | `—` | medium | `pol:p1:3.5` | ✅ |
| 3.6 | Use of proceeds | presence | `—` | low | `pol:p1:3.6` | ✅ |

## Errors

- extraction: extraction: daily API quota exhausted, not retrying: Error calling model 'gemini-3.8-flash' (RESOURCE_EXHAUSTED): 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To mon
