"""Policy Parser Agent (LLM + code checks). Runs only when the rules arrive as a document.

A compliance policy written in prose (PDF, DOCX, TXT, MD) is turned into the same RuleSet
a YAML file produces, so every later agent works unchanged.

    Gemini reads the policy  ->  one rule per requirement, each citing the sentence it came from
    code checks each rule    ->  the cited quote must exist in the cited policy chunk
                                 a threshold rule must have a term, an operator and a number
                                 rule ids must be unique

A rule whose quote can't be found keeps verified=False; the Compliance agent then reports
it as NEEDS_REVIEW instead of trusting a rule that may have been invented.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from src.agents.common import format_chunks
from src.agents.extraction import TERM_CATALOG
from src.agents.verifier import quote_in_chunk
from src.llm import LLMError, call_structured
from src.state import AuditEntry, PipelineState, Rule, RuleSet


class ParsedRule(BaseModel):
    id: str = Field(description="The policy's own number if it has one (e.g. '3.1'), else P-01, P-02 ...")
    name: str = Field(description="Short name of the requirement")
    category: str = Field(description="credit, covenant, financial, reporting, legal, operational or compliance")
    check_type: Literal["threshold", "presence", "judgment"]
    severity: Literal["low", "medium", "high", "critical"]
    description: str = Field(description="The requirement in one or two plain sentences")
    term: Optional[str] = Field(default=None, description="threshold rules only: snake_case term the number applies to")
    operator: Optional[Literal["<=", ">=", "<", ">", "=="]] = None
    value: Optional[float] = Field(default=None, description="threshold rules only: the limit as a plain number")
    unit: Optional[str] = None
    source_chunk_id: str = Field(description="chunk_id the requirement comes from, exactly as shown in brackets")
    source_quote: str = Field(description="Short verbatim quote of the requirement from that chunk")


class ParsedPolicy(BaseModel):
    policy_name: str
    rules: list[ParsedRule]


SYSTEM = """You are the Policy Parser Agent in a credit review pipeline. You turn a written
lending/compliance policy into a list of checkable rules. Be faithful: never add a rule the
policy does not state, and never drop one it does.

For each requirement in the policy:
1. One rule per requirement. Cite the chunk_id exactly as shown in brackets and copy a short
   VERBATIM quote of the requirement (max ~30 words).
2. check_type:
   - threshold: a numeric limit (maximum, minimum, at least, not exceed). Fill term, operator, value, unit.
   - presence: a clause or document must exist / be stated.
   - judgment: anything that needs reading and reasoning.
3. For threshold rules, use these term names whenever they fit (the system computes or extracts them):
   - ltv_ratio: loan-to-value as a DECIMAL (75% -> 0.75)
   - tenor_years: years from effective date to final maturity
{catalog}
   Otherwise invent a clear snake_case name. Amounts are plain numbers (USD 50 million -> 50000000);
   interest rates are percent numbers (9% -> 9); ratios like DSCR are plain numbers (1.25x -> 1.25);
   day limits are numbers of days.
4. severity: use the policy's own wording if it states one. Otherwise: critical for limits the
   policy calls absolute or critical, high for "must"/"shall" requirements, medium for
   reporting and documentation duties, low for formalities.
5. policy_name: the document's title."""


def _catalog_lines() -> str:
    return "\n".join(f"   - {name}: {desc}" for name, desc in TERM_CATALOG.items()
                     if any(k in desc for k in ("normalized", "ISO")))


def check_parsed_rules(parsed: ParsedPolicy, policy_chunks) -> tuple[list[Rule], list[str]]:
    """Code checks on the LLM's rules. Returns (rules, notes for the audit log)."""
    text = {c.chunk_id: c.text for c in policy_chunks}
    rules, notes, seen = [], [], set()
    for i, p in enumerate(parsed.rules, start=1):
        rid = p.id.strip() or f"P-{i:02d}"
        if rid in seen:
            rid = f"{rid}-{i}"
        seen.add(rid)

        check_type = p.check_type
        if check_type == "threshold" and (not p.term or p.operator is None or p.value is None):
            check_type = "judgment"
            notes.append(f"{rid}: threshold without term/operator/value -> judged by the LLM instead")

        verified = p.source_chunk_id in text and quote_in_chunk(p.source_quote, text[p.source_chunk_id])
        if not verified:
            notes.append(f"{rid}: source quote not found in {p.source_chunk_id}")

        rules.append(Rule(
            id=rid, name=p.name, category=p.category or "general", check_type=check_type,
            severity=p.severity, description=p.description,
            term=p.term if check_type == "threshold" else None,
            operator=p.operator if check_type == "threshold" else None,
            value=p.value if check_type == "threshold" else None,
            unit=p.unit, source=p.source_chunk_id, source_quote=p.source_quote, verified=verified,
        ))
    return rules, notes


def policy_parser_node(state: PipelineState) -> dict:
    policy_chunks = state.get("policy_chunks") or []
    user = f"POLICY DOCUMENT (one clause per line, chunk_id in brackets):\n{format_chunks(policy_chunks)}"
    try:
        parsed, audit = call_structured(ParsedPolicy, SYSTEM.format(catalog=_catalog_lines()), user, "policy_parser")
    except LLMError as exc:
        return {"status": "failed", "errors": [f"policy_parser: {exc}"], "audit_log": exc.audit}

    rules, notes = check_parsed_rules(parsed, policy_chunks)
    if not rules:
        return {
            "status": "failed",
            "errors": ["policy_parser: no rules could be read from the policy document"],
            "audit_log": audit + [AuditEntry(agent="policy_parser", event="failed", detail="0 rules parsed")],
        }
    ruleset = RuleSet(policy_name=parsed.policy_name or "Policy document", version="parsed", rules=rules)
    verified = sum(bool(r.verified) for r in rules)
    audit.append(AuditEntry(
        agent="policy_parser", event="completed",
        detail=f"{len(rules)} rules parsed ({verified} traced to the policy text)"
               + (f"; {'; '.join(notes)}" if notes else ""),
    ))
    return {"ruleset": ruleset, "audit_log": audit}
