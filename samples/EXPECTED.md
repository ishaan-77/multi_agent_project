# Expected results (answer key)

Hand-written ground truth for the two synthetic deals, checked against
`rules/lending_policy.yaml`. Tests and the README compare pipeline output against this.

## normal_loan.pdf: clean deal

| Rule | Expected | Evidence |
|---|---|---|
| CR-01 Exposure ≤ $50M | PASS | 3.1: USD 12,000,000 |
| CR-02 Pricing defined | PASS | 4.1: Term SOFR + 2.75% |
| CR-03 LTV ≤ 75% | PASS | 12.0M / 18.5M = 64.9% (3.1, 7.2) |
| CR-04 Independent valuation | PASS | 7.2: Calder & Wynn, 15 Jan 2026 |
| CR-05 Tenor ≤ 7y | PASS | 1 Mar 2026 → 31 Mar 2031 ≈ 5.1y (2.1, 5.2) |
| CR-06 DSCR ≥ 1.25x | PASS | 9.1: 1.35x |
| CR-07 Guarantee if > $10M | PASS | 8.1: Northwind Holdings Inc. |
| CR-08 Audited FS ≤ 120d | PASS | 10.1: 120 days |
| CR-09 Core events of default | PASS | 11.1, 11.3, 11.4 |
| CR-10 Governing law | PASS | 14.1: New York |
| CR-11 Prepayment terms | PASS | 6.1, 6.2 |
| CR-12 Consistent dates | PASS | 2.1, 5.1, 5.2 |
| CR-13 Use of proceeds | PASS | 3.2, 13.1 |

**Expected escalation:** none. There should be only low or medium residual risks.

## edge_case_loan.pdf: flawed deal

| Rule | Expected | Planted issue |
|---|---|---|
| CR-01 Exposure ≤ $50M | PASS | 3.1: USD 40,000,000 |
| CR-02 Pricing defined | FAIL | 2.2 / 4.1: margin set in a fee letter that isn't provided |
| CR-03 LTV ≤ 75% | FAIL or NEEDS_REVIEW | 40M / 45M = 88.9%, and only from the borrower's own estimate (6.2) |
| CR-04 Independent valuation | FAIL | 6.2: valuation "to be delivered" |
| CR-05 Tenor ≤ 7y | FAIL | maturity 31 Mar 2036 ≈ 10y (5.2) |
| CR-06 DSCR ≥ 1.25x | FAIL | 7.1: 1.10x |
| CR-07 Guarantee if > $10M | FAIL | no guarantee clause anywhere |
| CR-08 Audited FS ≤ 120d | FAIL | 8.1: 180 days |
| CR-09 Core events of default | FAIL | cross-default missing (only 9.1, 9.2) |
| CR-10 Governing law | PASS | 11.1: Florida |
| CR-11 Prepayment terms | FAIL or NEEDS_REVIEW | no prepayment clause |
| CR-12 Consistent dates | FAIL | Effective Date 1 Apr 2026 (2.1) vs 1 May 2026 (S1.1) |
| CR-13 Use of proceeds | FAIL or NEEDS_REVIEW | 3.2: "general corporate purposes" with no restrictions |

**Other ambiguities the Risk agent should flag:** interest payment dates are at the lender's discretion (4.2), leverage covenant is "to be agreed" (7.2), the lender can waive covenants unilaterally (7.3), Clause 10 is blank, and there are no conditions precedent.

**Expected escalation:** yes. There are critical and high-severity FAILs plus NEEDS_REVIEW items.
