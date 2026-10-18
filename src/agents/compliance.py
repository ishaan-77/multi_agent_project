"""Compliance Review Agent (hybrid: code + LLM).

- Threshold rules (LTV, tenor, DSCR, ...) are checked in code from extracted/derived
  numbers, so the arithmetic is exact and repeatable.
- Presence/judgment rules (pricing defined, guarantee required, ...) are decided by the LLM
  in one batched call, then passed through a grounding guard:
    * citations to non-existent chunks are dropped
    * a PASS without valid evidence is downgraded to NEEDS_REVIEW
    * a rule the model forgot to answer becomes NEEDS_REVIEW
- Uncertainty never produces a PASS: missing, unverified or low-confidence inputs give
  NEEDS_REVIEW (or FAIL if even the uncertain value breaches the limit).
"""
from __future__ import annotations

import operator
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from src.agents.common import format_chunks, format_terms, keep_valid_evidence
from src.llm import LLMError, call_structured
from src.state import (
    AuditEntry, ComplianceResult, ComplianceStatus, Evidence, EscalationPolicy,
    ExtractedTerm, PipelineState, Rule,
)

OPS = {"<=": operator.le, ">=": operator.ge, "<": operator.lt, ">": operator.gt, "==": operator.eq}


# ---------------------------------------------------------------- derived metrics

def parse_date(value: str) -> Optional[date]:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d %B %Y", "%B %d, %Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _combine(name: str, value: str, normalized: float, unit: str, sources: list[ExtractedTerm], how: str) -> ExtractedTerm:
    notes = [how] + [f"{s.name}: {s.notes}" for s in sources if s.notes]
    return ExtractedTerm(
        name=name, value=value, normalized=normalized, unit=unit,
        evidence=[e for s in sources for e in s.evidence],
        confidence=min(s.confidence for s in sources),
        verified=all(bool(s.verified) for s in sources),
        notes=" | ".join(notes),
    )


def derive_terms(terms: dict[str, ExtractedTerm]) -> list[ExtractedTerm]:
    derived = []
    principal, collateral = terms.get("principal_amount"), terms.get("collateral_value")
    if principal and collateral and principal.normalized and collateral.normalized:
        ltv = principal.normalized / collateral.normalized
        derived.append(_combine(
            "ltv_ratio", f"{ltv:.1%}", round(ltv, 4), "ratio", [principal, collateral],
            "derived: principal_amount / collateral_value",
        ))
    eff, mat = terms.get("effective_date"), terms.get("maturity_date")
    if eff and mat:
        d1, d2 = parse_date(eff.value), parse_date(mat.value)
        if d1 and d2:
            years = (d2 - d1).days / 365.25
            derived.append(_combine(
                "tenor_years", f"{years:.1f} years", round(years, 2), "years", [eff, mat],
                "derived: maturity_date - effective_date",
            ))
    return derived


# ---------------------------------------------------------------- deterministic checks

def _num(x: float) -> str:
    return f"{x:,.0f}" if abs(x) >= 1000 else f"{x:g}"


def check_threshold(rule: Rule, term: Optional[ExtractedTerm], policy: EscalationPolicy) -> ComplianceResult:
    def result(status: ComplianceStatus, rationale: str, evidence: list[Evidence] | None = None):
        return ComplianceResult(
            rule_id=rule.id, rule_name=rule.name, severity=rule.severity, status=status,
            evidence=evidence or [], rationale=rationale, method="deterministic",
        )

    limit = f"{rule.operator} {_num(rule.value)}{' ' + rule.unit if rule.unit else ''}"
    if term is None or term.normalized is None:
        return result("NEEDS_REVIEW", f"Required term '{rule.term}' was not found or is not numeric, so the limit ({limit}) cannot be checked.")

    passed = OPS[rule.operator](term.normalized, rule.value)
    actual = f"{rule.term} = {term.value} (normalized {_num(term.normalized)}); policy requires {limit}"

    if term.verified is False:
        return result("NEEDS_REVIEW", f"{actual}. Supporting evidence could not be verified against the document.", term.evidence)
    if term.confidence < policy.min_term_confidence:
        if passed:
            return result("NEEDS_REVIEW", f"{actual}. Would pass, but the input is low-confidence ({term.confidence:.2f}): {term.notes or 'ambiguous'}", term.evidence)
        return result("FAIL", f"{actual}. Breaches the limit even on a low-confidence value ({term.confidence:.2f}): {term.notes or 'ambiguous'}", term.evidence)
    return result("PASS" if passed else "FAIL", actual + (". Within limit." if passed else ". Limit breached."), term.evidence)


# ---------------------------------------------------------------- LLM judgment

class RuleJudgment(BaseModel):
    rule_id: str
    status: ComplianceStatus
    evidence: list[Evidence]
    rationale: str


class JudgmentBatch(BaseModel):
    results: list[RuleJudgment]


SYSTEM = """You are the Compliance Review Agent in a credit review pipeline.
For each policy rule, decide PASS, FAIL or NEEDS_REVIEW using ONLY the document and the
extracted terms provided.

- PASS: the document clearly satisfies the rule. You MUST cite at least one chunk_id.
- FAIL: the document clearly violates the rule, or a REQUIRED clause is absent.
- NEEDS_REVIEW: evidence is ambiguous, conflicting, undefined ("to be agreed"), or depends
  on documents that are not provided.
Cite evidence as chunk_id (exactly as shown in brackets) plus a short verbatim quote.
The rationale must be 1-3 sentences explaining the decision with reference to the evidence.
Answer every rule exactly once."""


def judge_rules(rules: list[Rule], state: PipelineState) -> tuple[list[ComplianceResult], list[AuditEntry], list[str]]:
    if not rules:
        return [], [], []
    rule_text = "\n".join(f"- {r.id} [{r.check_type}, severity {r.severity}] {r.name}: {r.description.strip()}" for r in rules)
    terms = state["extraction"].terms + state.get("derived_terms", [])
    user = (
        f"POLICY RULES TO EVALUATE:\n{rule_text}\n\n"
        f"EXTRACTED TERMS (verified = citation checked by code):\n{format_terms(terms)}\n\n"
        f"DOCUMENT:\n{format_chunks(state['chunks'])}"
    )
    by_id = {r.id: r for r in rules}
    try:
        batch, audit = call_structured(JudgmentBatch, SYSTEM, user, "compliance")
    except LLMError as exc:
        fallback = [
            ComplianceResult(rule_id=r.id, rule_name=r.name, severity=r.severity, status="NEEDS_REVIEW",
                             rationale="Compliance LLM unavailable; rule must be checked manually.")
            for r in rules
        ]
        return fallback, exc.audit, [f"compliance: {exc}"]

    chunk_ids = {c.chunk_id for c in state["chunks"]}
    results: dict[str, ComplianceResult] = {}
    for j in batch.results:
        rule = by_id.get(j.rule_id)
        if rule is None or j.rule_id in results:
            continue
        evidence, dropped = keep_valid_evidence(j.evidence, chunk_ids)
        status, rationale = j.status, j.rationale
        if dropped:
            rationale += f" [{dropped} invalid citation(s) removed]"
        if status == "PASS" and not evidence:
            status = "NEEDS_REVIEW"
            rationale += " [Downgraded from PASS: no valid evidence cited]"
        results[j.rule_id] = ComplianceResult(
            rule_id=rule.id, rule_name=rule.name, severity=rule.severity,
            status=status, evidence=evidence, rationale=rationale, method="llm",
        )
    for r in rules:
        if r.id not in results:
            results[r.id] = ComplianceResult(
                rule_id=r.id, rule_name=r.name, severity=r.severity, status="NEEDS_REVIEW",
                rationale="Agent returned no decision for this rule.", method="llm",
            )
    return [results[r.id] for r in rules], audit, []


# ---------------------------------------------------------------- node

def compliance_node(state: PipelineState) -> dict:
    ruleset = state["ruleset"]
    terms = {t.name: t for t in state["extraction"].terms}
    derived = derive_terms(terms)
    all_terms = {**terms, **{d.name: d for d in derived}}
    state = {**state, "derived_terms": derived}

    deterministic = {
        r.id: check_threshold(r, all_terms.get(r.term), ruleset.escalation)
        for r in ruleset.rules if r.check_type == "threshold"
    }
    llm_rules = [r for r in ruleset.rules if r.check_type != "threshold"]
    judged, audit, errors = judge_rules(llm_rules, state)
    judged_by_id = {j.rule_id: j for j in judged}

    matrix = [deterministic.get(r.id) or judged_by_id[r.id] for r in ruleset.rules]
    counts = {s: sum(m.status == s for m in matrix) for s in ("PASS", "FAIL", "NEEDS_REVIEW")}
    audit.append(AuditEntry(
        agent="compliance", event="completed",
        detail=f"{len(deterministic)} deterministic + {len(llm_rules)} LLM rules -> {counts}",
    ))
    return {"compliance": matrix, "derived_terms": derived, "errors": errors, "audit_log": audit}
