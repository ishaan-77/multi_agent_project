"""Risk & Summary Agent (LLM, with a deterministic fallback).

Builds a prioritized risk register (financial / legal / operational / compliance), lists
missing or ambiguous information, and writes an executive summary with follow-up actions.

If the LLM fails, a rule-based report is built from the compliance FAILs, so the pipeline
still returns a usable (clearly labelled) result.
"""
from __future__ import annotations

from src.agents.common import LIKELIHOOD_RANK, SEVERITY_RANK, format_chunks, format_terms, keep_valid_evidence
from src.llm import LLMError, call_structured
from src.state import AuditEntry, PipelineState, Risk, RiskReport

SYSTEM = """You are the Risk & Summary Agent in a credit review pipeline. You write for a credit
committee. Using ONLY the document, extracted terms and compliance matrix provided:

1. risks: identify concrete financial, legal, operational and compliance risks. Each risk needs
   a short title, a description that says why it matters, severity (low/medium/high/critical),
   likelihood (low/medium/high), evidence (chunk_id exactly as shown + verbatim quote) and a
   specific recommendation. Include risks from undefined or conflicting terms, not just
   policy failures. Do not duplicate risks.
2. gaps: missing information, undefined terms ("to be agreed"), conflicting values, and
   documents referenced but not provided.
3. executive_summary: 120-200 words. State the deal, the overall risk view, the most
   important issues, and a recommendation (approve / approve with conditions / do not approve
   pending resolution).
4. follow_up_actions: specific, actionable next steps, most important first.
Never invent facts that are not in the inputs."""

CATEGORY_MAP = {
    "credit": "financial", "covenant": "financial", "financial": "financial",
    "reporting": "operational", "operational": "operational",
    "legal": "legal", "compliance": "compliance",
}


def _prioritize(risks: list[Risk]) -> list[Risk]:
    risks = sorted(risks, key=lambda r: (SEVERITY_RANK[r.severity], LIKELIHOOD_RANK[r.likelihood]), reverse=True)
    for i, r in enumerate(risks, start=1):
        r.id = f"R-{i:02d}"
    return risks


def fallback_report(state: PipelineState) -> RiskReport:
    rules = {r.id: r for r in state["ruleset"].rules}
    risks = [
        Risk(
            id="", category=CATEGORY_MAP.get(rules[c.rule_id].category, "compliance"),
            title=f"Policy breach: {c.rule_name}", description=c.rationale,
            severity=c.severity, likelihood="high", evidence=c.evidence,
            recommendation=f"Resolve {c.rule_id} before approval or obtain a documented policy exception.",
        )
        for c in state.get("compliance", []) if c.status == "FAIL"
    ]
    extraction = state.get("extraction")
    gaps = [f"Not found in document: {m}" for m in (extraction.missing_terms if extraction else [])]
    gaps += [f"{c.rule_id} {c.rule_name}: {c.rationale}" for c in state.get("compliance", []) if c.status == "NEEDS_REVIEW"]
    return RiskReport(
        risks=_prioritize(risks), gaps=gaps,
        executive_summary=(
            "[Automated fallback - the Risk & Summary LLM was unavailable.] "
            f"{len(risks)} policy breaches and {len(gaps)} open items were identified by the "
            "compliance review. A human reviewer should assess overall credit risk."
        ),
        follow_up_actions=["Re-run the risk analysis when the LLM is available."]
        + [f"Address: {r.title}" for r in risks],
    )


def risk_node(state: PipelineState) -> dict:
    extraction = state["extraction"]
    matrix = "\n".join(
        f"- {c.rule_id} {c.rule_name} [{c.severity}]: {c.status} - {c.rationale} (evidence: {[e.chunk_id for e in c.evidence]})"
        for c in state.get("compliance", [])
    )
    user = (
        f"COMPLIANCE MATRIX:\n{matrix}\n\n"
        f"EXTRACTED TERMS:\n{format_terms(extraction.terms + state.get('derived_terms', []))}\n"
        f"Terms not found in document: {extraction.missing_terms}\n\n"
        f"DOCUMENT:\n{format_chunks(state['chunks'])}"
    )
    try:
        report, audit = call_structured(RiskReport, SYSTEM, user, "risk")
    except LLMError as exc:
        return {
            "risk_report": fallback_report(state),
            "errors": [f"risk: {exc}"],
            "audit_log": exc.audit + [AuditEntry(agent="risk", event="fallback", detail="used rule-based risk report")],
        }

    chunk_ids = {c.chunk_id for c in state["chunks"]}
    for risk in report.risks:
        risk.evidence, _ = keep_valid_evidence(risk.evidence, chunk_ids)
    report.risks = _prioritize(report.risks)

    # Make sure terms the extractor couldn't find always show up as gaps.
    known = " ".join(report.gaps).lower()
    for missing in extraction.missing_terms:
        if missing.replace("_", " ") not in known and missing not in known:
            report.gaps.append(f"Not found in document: {missing}")

    audit.append(AuditEntry(
        agent="risk", event="completed",
        detail=f"{len(report.risks)} risks, {len(report.gaps)} gaps, {len(report.follow_up_actions)} actions",
    ))
    return {"risk_report": report, "audit_log": audit}
