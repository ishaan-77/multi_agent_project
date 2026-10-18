"""Shared data contracts for the whole pipeline.

Every agent reads from and writes to `PipelineState`. Every message between agents is a
Pydantic model, so malformed output is caught at the boundary instead of propagating.
Traceability rule: anything an agent claims must point at a `chunk_id` produced by ingestion.
"""
from __future__ import annotations

import operator
from datetime import datetime, timezone
from typing import Annotated, Literal, Optional, TypedDict

from pydantic import BaseModel, Field

# ---------------------------------------------------------------- ingestion

class Chunk(BaseModel):
    """Smallest citable unit of the document (usually one clause)."""
    chunk_id: str = Field(description="Stable ID, e.g. 'p2:7.2' = page 2, clause 7.2")
    page: int
    section: str = Field(description="Section heading, e.g. '7. Security and Collateral'")
    clause: Optional[str] = Field(default=None, description="Clause number, e.g. '7.2'")
    text: str


class DocumentInfo(BaseModel):
    path: str
    title: str
    page_count: int
    chunk_count: int
    structured: bool = Field(description="True if numbered clauses were detected")


# ---------------------------------------------------------------- rules

class Rule(BaseModel):
    id: str
    name: str
    category: str
    check_type: Literal["threshold", "presence", "judgment"]
    severity: Literal["low", "medium", "high", "critical"]
    description: str
    term: Optional[str] = None
    operator: Optional[Literal["<=", ">=", "<", ">", "=="]] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    # Set only for rules parsed from a policy document (PDF/DOCX/TXT/MD):
    source: Optional[str] = Field(default=None, description="Policy chunk the rule came from, e.g. 'pol:p2:3.1'")
    source_quote: Optional[str] = None
    verified: Optional[bool] = Field(default=None, description="True if source_quote was found in the policy text")


class EscalationPolicy(BaseModel):
    on_fail_severity: list[str] = ["critical", "high"]
    on_needs_review: bool = True
    min_term_confidence: float = 0.7
    # LLM-judged risks are subjective, so by default only critical ones force escalation;
    # high risks still appear in the risk register.
    on_risk_severity: list[str] = ["critical"]


class RuleSet(BaseModel):
    policy_name: str
    version: str
    escalation: EscalationPolicy = EscalationPolicy()
    rules: list[Rule]


# ---------------------------------------------------------------- evidence

class Evidence(BaseModel):
    chunk_id: str = Field(description="chunk_id the quote comes from")
    quote: str = Field(description="Short verbatim quote from that chunk")


# ---------------------------------------------------------------- term extraction

class ExtractedTerm(BaseModel):
    name: str = Field(description="snake_case term name, e.g. principal_amount")
    value: str = Field(description="Value as stated in the document")
    normalized: Optional[float] = Field(
        default=None, description="Numeric form if applicable (USD amount, ratio, days, %)"
    )
    unit: Optional[str] = None
    evidence: list[Evidence] = []
    confidence: float = Field(ge=0, le=1)
    notes: Optional[str] = Field(default=None, description="Ambiguity or conflicts noticed")
    verified: Optional[bool] = Field(default=None, description="Set by the Evidence Verifier")


class ExtractionResult(BaseModel):
    terms: list[ExtractedTerm]
    missing_terms: list[str] = Field(
        default=[], description="Expected terms not found anywhere in the document"
    )


# ---------------------------------------------------------------- compliance

ComplianceStatus = Literal["PASS", "FAIL", "NEEDS_REVIEW"]


class ComplianceResult(BaseModel):
    rule_id: str
    rule_name: str
    severity: str
    status: ComplianceStatus
    evidence: list[Evidence] = []
    rationale: str
    method: Literal["deterministic", "llm"] = "llm"


# ---------------------------------------------------------------- risk & summary

Severity = Literal["low", "medium", "high", "critical"]


class Risk(BaseModel):
    id: str
    category: Literal["financial", "legal", "operational", "compliance"]
    title: str
    description: str
    severity: Severity
    likelihood: Literal["low", "medium", "high"]
    evidence: list[Evidence] = []
    recommendation: str


class RiskReport(BaseModel):
    risks: list[Risk]
    gaps: list[str] = Field(description="Missing or ambiguous information")
    executive_summary: str
    follow_up_actions: list[str]


class Escalation(BaseModel):
    source: str = Field(description="Which agent/rule raised it, e.g. 'compliance:CR-03'")
    reason: str
    severity: Severity


# ---------------------------------------------------------------- audit

class AuditEntry(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent: str
    event: str
    detail: str = ""


# ---------------------------------------------------------------- graph state

class PipelineState(TypedDict, total=False):
    """Shared workflow state passed through the LangGraph orchestrator.

    `audit_log` and `errors` use an add-reducer so each agent appends instead of overwriting.
    """
    # inputs
    deal_path: str
    rules_path: str
    # ingestion
    document: DocumentInfo
    chunks: list[Chunk]
    ruleset: RuleSet                      # None until the Policy Parser runs, for document policies
    policy_source: Literal["structured", "document"]
    policy_chunks: list[Chunk]            # the policy document's chunks (ids start with 'pol:')
    # agents
    extraction: ExtractionResult
    extraction_attempts: int
    verification_feedback: list[str]      # failures sent back to the extractor on retry
    derived_terms: list[ExtractedTerm]    # computed in code, e.g. ltv_ratio, tenor_years
    compliance: list[ComplianceResult]
    risk_report: RiskReport
    escalations: list[Escalation]
    # bookkeeping
    status: Literal["running", "completed", "completed_with_errors", "failed"]
    errors: Annotated[list[str], operator.add]
    audit_log: Annotated[list[AuditEntry], operator.add]
