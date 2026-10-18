"""Evidence Verification Agent (deterministic, no LLM).

Checks that every quote the extractor produced really exists in the chunk it cites.
This is the pipeline's main guard against hallucinated terms.

  verified=True   every citation points to a real chunk and the quote is found in it
                  (exact match after normalising whitespace/quotes/case, or >= 90% token overlap)
  verified=False  no evidence, unknown chunk_id, or quote not found

Failures are sent back to the extractor once. If they persist, the terms stay
verified=False and downstream agents treat them as NEEDS_REVIEW.
"""
from __future__ import annotations

import re

from src.state import AuditEntry, ExtractedTerm, PipelineState

MAX_EXTRACTION_ATTEMPTS = 2
TOKEN_OVERLAP_THRESHOLD = 0.9

_QUOTES = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-"})


def normalize(text: str) -> str:
    text = text.translate(_QUOTES).lower()
    text = re.sub(r"[^\w%.,$/-]+", " ", text)
    return " ".join(text.split())


def quote_in_chunk(quote: str, chunk_text: str) -> bool:
    q, c = normalize(quote), normalize(chunk_text)
    if not q:
        return False
    if q in c:
        return True
    tokens = q.split()
    chunk_tokens = set(c.split())
    overlap = sum(t in chunk_tokens for t in tokens) / len(tokens)
    return overlap >= TOKEN_OVERLAP_THRESHOLD


def verify_term(term: ExtractedTerm, chunk_text: dict[str, str]) -> list[str]:
    """Return a list of problems (empty list = verified)."""
    if not term.evidence:
        return [f"{term.name}: no evidence given"]
    problems = []
    for ev in term.evidence:
        if ev.chunk_id not in chunk_text:
            problems.append(f"{term.name}: cites unknown chunk '{ev.chunk_id}'")
        elif not quote_in_chunk(ev.quote, chunk_text[ev.chunk_id]):
            problems.append(f"{term.name}: quote not found in {ev.chunk_id}: \"{ev.quote[:80]}\"")
    return problems


def verifier_node(state: PipelineState) -> dict:
    chunk_text = {c.chunk_id: c.text for c in state["chunks"]}
    extraction = state["extraction"].model_copy(deep=True)

    problems: list[str] = []
    for term in extraction.terms:
        term_problems = verify_term(term, chunk_text)
        term.verified = not term_problems
        problems.extend(term_problems)

    verified = sum(t.verified for t in extraction.terms)
    detail = f"{verified}/{len(extraction.terms)} terms verified"
    attempts = state.get("extraction_attempts", 1)
    will_retry = bool(problems) and attempts < MAX_EXTRACTION_ATTEMPTS
    if problems:
        detail += f"; {len(problems)} citation problems" + (" -> retrying extraction" if will_retry else " -> kept as unverified")

    return {
        "extraction": extraction,
        "verification_feedback": problems,
        "audit_log": [AuditEntry(agent="verifier", event="completed", detail=detail)],
    }


def route_after_verification(state: PipelineState) -> str:
    """Conditional edge: retry extraction once if citations failed."""
    if state.get("verification_feedback") and state.get("extraction_attempts", 1) < MAX_EXTRACTION_ATTEMPTS:
        return "retry"
    return "continue"
