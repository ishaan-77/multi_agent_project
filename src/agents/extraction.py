"""Term Extraction Agent (LLM).

Reads the chunked document and returns material terms. Each term carries a verbatim
quote and the chunk_id it came from. On a retry, it receives the Evidence Verifier's
feedback about which citations failed.
"""
from __future__ import annotations

from src.agents.common import format_chunks
from src.llm import LLMError, call_structured
from src.state import AuditEntry, ExtractionResult, PipelineState

# The catalog tells the model which terms matter. The names line up with the `term:`
# fields in the rule set, so the Compliance agent can find them deterministically.
TERM_CATALOG = {
    "lender": "Lending institution name",
    "borrower": "Borrowing entity name",
    "guarantor": "Guarantor name, if any",
    "facility_type": "Type of facility (term loan, bridge loan, ...)",
    "principal_amount": "Total facility amount. normalized = number in USD",
    "effective_date": "Effective date. value = ISO YYYY-MM-DD",
    "first_repayment_date": "First repayment date. value = ISO YYYY-MM-DD",
    "maturity_date": "Final maturity date. value = ISO YYYY-MM-DD",
    "interest_rate": "Full pricing description as stated (benchmark + margin, or fixed)",
    "margin_pct": "Numeric margin over benchmark in percent, e.g. 2.75. Omit if undefined",
    "interest_payment_frequency": "When interest is paid",
    "default_interest": "Additional default interest",
    "repayment_schedule": "How principal is repaid",
    "prepayment_terms": "Voluntary and mandatory prepayment terms and fees",
    "collateral_description": "What secures the loan",
    "collateral_value": "Collateral value. normalized = number in USD",
    "collateral_valuation_source": "Who valued the collateral and when (independent appraiser or borrower estimate?)",
    "guarantee": "Guarantee terms",
    "dscr_covenant": "Minimum debt service coverage ratio. normalized = the ratio, e.g. 1.35",
    "leverage_covenant": "Maximum leverage ratio covenant",
    "other_covenants": "Other financial covenants",
    "audited_financials_days": "Days after year end to deliver audited financials. normalized = days",
    "events_of_default": "List of events of default",
    "conditions_precedent": "Conditions before drawdown",
    "purpose": "Stated purpose / use of proceeds",
    "use_of_proceeds_restrictions": "Prohibited uses of proceeds",
    "exclusions": "Exclusions / limitations of liability",
    "governing_law": "Governing law and jurisdiction",
}

SYSTEM = """You are the Term Extraction Agent in a credit review pipeline.
You extract material deal terms from a loan agreement. You must be precise and grounded.

Rules:
1. Every term MUST include evidence: the chunk_id in square brackets exactly as shown, and a
   short VERBATIM quote (copied character-for-character, max ~25 words) from that chunk.
2. Never invent or infer values that are not written in the document. If a term in the
   catalog is not present, add its name to missing_terms instead of guessing.
3. If a value is undefined ("to be agreed", "as set out in a separate letter") extract it
   as stated, set confidence <= 0.5 and explain in notes.
4. If the same term appears more than once with DIFFERENT values, include evidence for each
   occurrence, set confidence <= 0.5 and describe the conflict in notes.
5. confidence: 0.9-1.0 explicit and unambiguous; 0.6-0.8 needs interpretation; <= 0.5 ambiguous.
6. Leave the `verified` field empty; another agent sets it."""


DERIVED_TERMS = {"ltv_ratio", "tenor_years"}  # computed in code by the Compliance agent


def policy_terms(state: PipelineState) -> dict[str, str]:
    """Terms that the rule set's threshold rules check but the catalog doesn't name.

    A custom policy may check e.g. 'requested_principal_usd'; the extractor must then
    extract a term with exactly that name, or the code check would have nothing to compare.
    """
    ruleset = state.get("ruleset")
    extra = {}
    for r in (ruleset.rules if ruleset else []):
        if r.check_type == "threshold" and r.term and r.term not in TERM_CATALOG and r.term not in DERIVED_TERMS:
            unit = f" in {r.unit}" if r.unit else ""
            extra[r.term] = f"Required by policy rule {r.id} ({r.description.strip()}). normalized = the number{unit}"
    return extra


def build_prompt(state: PipelineState) -> str:
    catalog = "\n".join(f"- {name}: {desc}" for name, desc in {**TERM_CATALOG, **policy_terms(state)}.items())
    prompt = (
        f"TERM CATALOG (use these exact names; you may add other material terms in snake_case):\n"
        f"{catalog}\n\nDOCUMENT (one clause per line, chunk_id in brackets):\n"
        f"{format_chunks(state['chunks'])}"
    )
    feedback = state.get("verification_feedback") or []
    if feedback:
        prompt += (
            "\n\nIMPORTANT - your previous extraction had citation problems. Fix these terms "
            "by quoting text exactly as it appears in the cited chunk:\n- " + "\n- ".join(feedback)
        )
    return prompt


def extraction_node(state: PipelineState) -> dict:
    attempt = state.get("extraction_attempts", 0) + 1
    try:
        result, audit = call_structured(ExtractionResult, SYSTEM, build_prompt(state), "extraction")
    except LLMError as exc:
        return {
            "extraction_attempts": attempt,
            "status": "failed",
            "errors": [f"extraction: {exc}"],
            "audit_log": exc.audit,
        }
    for term in result.terms:
        term.verified = None  # never trust a model-set verification flag
    audit.append(AuditEntry(
        agent="extraction", event="completed",
        detail=f"attempt {attempt}: {len(result.terms)} terms, missing={result.missing_terms}",
    ))
    return {"extraction": result, "extraction_attempts": attempt, "audit_log": audit}
