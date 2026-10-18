"""Orchestrator Agent: the LangGraph workflow.

    ingest ──policy is a document──▶ parse_policy ──ok──▶ extract   (PDF/DOCX/TXT/MD rules only)
    ingest ──ok──▶ extract ──ok──▶ verify ──continue──▶ compliance ─▶ risk ─▶ escalate ─▶ assemble
       │              ▲  │           │
       │              └──┼─retry─────┘   (citation failures, max 1 retry)
       └──failed─────────┴──failed──────────────────────────────────▶ escalate

Shared state lives in `PipelineState`. Each node returns only the keys it changes.
`errors` and `audit_log` are append-only. Failures move the run to the escalate step
instead of crashing it, so the run always produces a report.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.agents.compliance import compliance_node
from src.agents.escalation import escalation_node
from src.agents.extraction import extraction_node
from src.agents.ingestion import ingestion_node
from src.agents.policy_parser import policy_parser_node
from src.agents.risk import risk_node
from src.agents.verifier import route_after_verification, verifier_node
from src.state import AuditEntry, PipelineState


def _ok_or_failed(state: PipelineState) -> str:
    return "failed" if state.get("status") == "failed" else "ok"


def _after_ingest(state: PipelineState) -> str:
    if state.get("status") == "failed":
        return "failed"
    return "parse_policy" if state.get("ruleset") is None else "ok"


def assemble_node(state: PipelineState) -> dict:
    if state.get("status") == "failed":
        status = "failed"
    elif state.get("errors"):
        status = "completed_with_errors"
    else:
        status = "completed"
    return {"status": status, "audit_log": [AuditEntry(agent="orchestrator", event="finished", detail=f"status={status}")]}


def build_graph():
    g = StateGraph(PipelineState)
    g.add_node("ingest", ingestion_node)
    g.add_node("parse_policy", policy_parser_node)
    g.add_node("extract", extraction_node)
    g.add_node("verify", verifier_node)
    g.add_node("compliance", compliance_node)
    g.add_node("risk", risk_node)
    g.add_node("escalate", escalation_node)
    g.add_node("assemble", assemble_node)

    g.add_edge(START, "ingest")
    g.add_conditional_edges("ingest", _after_ingest, {"ok": "extract", "parse_policy": "parse_policy", "failed": "escalate"})
    g.add_conditional_edges("parse_policy", _ok_or_failed, {"ok": "extract", "failed": "escalate"})
    g.add_conditional_edges("extract", _ok_or_failed, {"ok": "verify", "failed": "escalate"})
    g.add_conditional_edges("verify", route_after_verification, {"retry": "extract", "continue": "compliance"})
    g.add_edge("compliance", "risk")
    g.add_edge("risk", "escalate")
    g.add_edge("escalate", "assemble")
    g.add_edge("assemble", END)
    return g.compile()
