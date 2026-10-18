"""Human Escalation Agent (deterministic).

Applies the rule set's escalation policy to everything the other agents produced, and
decides what a human must look at before the deal can proceed.
"""
from __future__ import annotations

from src.agents.common import SEVERITY_RANK
from src.state import AuditEntry, Escalation, PipelineState


def escalation_node(state: PipelineState) -> dict:
    out: list[Escalation] = []

    if state.get("status") == "failed":
        out.append(Escalation(source="orchestrator", severity="critical",
                              reason="Pipeline could not complete; the deal must be reviewed manually."))
    else:
        policy = state["ruleset"].escalation

        for c in state.get("compliance", []):
            if c.status == "FAIL" and c.severity in policy.on_fail_severity:
                out.append(Escalation(source=f"compliance:{c.rule_id}", severity=c.severity,
                                      reason=f"{c.rule_name} failed: {c.rationale}"))
            elif c.status == "NEEDS_REVIEW" and policy.on_needs_review:
                out.append(Escalation(source=f"compliance:{c.rule_id}", severity=c.severity,
                                      reason=f"{c.rule_name} needs human judgment: {c.rationale}"))

        for t in state["extraction"].terms:
            if t.verified is False:
                out.append(Escalation(source=f"extraction:{t.name}", severity="medium",
                                      reason=f"Term '{t.name}' could not be verified against the document."))
            elif t.confidence < policy.min_term_confidence:
                out.append(Escalation(source=f"extraction:{t.name}", severity="medium",
                                      reason=f"Low-confidence term '{t.name}' ({t.confidence:.2f}): {t.notes or t.value}"))

        report = state.get("risk_report")
        for r in (report.risks if report else []):
            if r.severity in policy.on_risk_severity:
                out.append(Escalation(source=f"risk:{r.id}", severity=r.severity, reason=f"{r.title}: {r.description}"))

    for err in state.get("errors", []):
        out.append(Escalation(source="system", severity="high", reason=f"Agent error: {err[:200]}"))

    out.sort(key=lambda e: SEVERITY_RANK[e.severity], reverse=True)
    return {
        "escalations": out,
        "audit_log": [AuditEntry(agent="escalation", event="completed",
                                 detail=f"{len(out)} items escalated for human review")],
    }
