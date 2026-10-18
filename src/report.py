"""Turn the final pipeline state into report.json and report.md."""
from __future__ import annotations

from typing import Any

from src.state import PipelineState

STATUS_ICON = {"PASS": "✅ PASS", "FAIL": "❌ FAIL", "NEEDS_REVIEW": "⚠️ REVIEW"}


def _dump(x: Any) -> Any:
    if isinstance(x, list):
        return [_dump(i) for i in x]
    return x.model_dump() if hasattr(x, "model_dump") else x


def build_report(state: PipelineState) -> dict:
    extraction = state.get("extraction")
    return {
        "status": state.get("status"),
        "document": _dump(state.get("document")),
        "policy": {
            "name": state["ruleset"].policy_name, "version": state["ruleset"].version,
            "source": state.get("policy_source", "structured"),
            "rules": _dump(state["ruleset"].rules),
        } if state.get("ruleset") else None,
        "decision": "ESCALATE_TO_HUMAN_REVIEW" if state.get("escalations") else "NO_ESCALATION_REQUIRED",
        "executive_summary": state["risk_report"].executive_summary if state.get("risk_report") else None,
        "escalations": _dump(state.get("escalations", [])),
        "compliance_matrix": _dump(state.get("compliance", [])),
        "risk_register": _dump(state["risk_report"].risks) if state.get("risk_report") else [],
        "gaps": state["risk_report"].gaps if state.get("risk_report") else [],
        "follow_up_actions": state["risk_report"].follow_up_actions if state.get("risk_report") else [],
        "extracted_terms": _dump(extraction.terms) if extraction else [],
        "derived_terms": _dump(state.get("derived_terms", [])),
        "missing_terms": extraction.missing_terms if extraction else [],
        "errors": state.get("errors", []),
        "extraction_attempts": state.get("extraction_attempts", 0),
    }


def _cell(text: Any) -> str:
    return str(text if text is not None else "").replace("|", "\\|").replace("\n", " ")


def _refs(evidence: list[dict]) -> str:
    return ", ".join(f"`{e['chunk_id']}`" for e in evidence) or "—"


def render_markdown(r: dict) -> str:
    doc = r["document"] or {}
    md = [f"# Deal Review Report: {doc.get('title', 'Unknown document')}", ""]
    md.append(f"**Document:** `{doc.get('path', '?')}` ({doc.get('page_count', '?')} pages)  ")
    if r["policy"]:
        md.append(f"**Policy:** {r['policy']['name']} v{r['policy']['version']}  ")
    md.append(f"**Run status:** `{r['status']}`  ")
    decision = "🔴 **ESCALATE TO HUMAN REVIEW**" if r["decision"] == "ESCALATE_TO_HUMAN_REVIEW" else "🟢 **No escalation required**"
    md += [f"**Decision:** {decision}", ""]
    md.append("> Evidence references use `p<page>:<clause>`. For example, `p2:7.2` is page 2, clause 7.2.\n")

    if r["executive_summary"]:
        md += ["## Executive Summary", "", r["executive_summary"], ""]

    if r["escalations"]:
        md += ["## Escalations for Human Review", "", "| Severity | Source | Reason |", "|---|---|---|"]
        md += [f"| {e['severity']} | `{e['source']}` | {_cell(e['reason'])} |" for e in r["escalations"]]
        md.append("")

    if r["compliance_matrix"]:
        counts = {s: sum(c["status"] == s for c in r["compliance_matrix"]) for s in STATUS_ICON}
        md += ["## Compliance Matrix", "",
               f"{counts['PASS']} pass · {counts['FAIL']} fail · {counts['NEEDS_REVIEW']} needs review", "",
               "| Rule | Name | Severity | Result | Evidence | Rationale | Method |", "|---|---|---|---|---|---|---|"]
        md += [f"| {c['rule_id']} | {_cell(c['rule_name'])} | {c['severity']} | {STATUS_ICON[c['status']]} | "
               f"{_refs(c['evidence'])} | {_cell(c['rationale'])} | {c['method']} |" for c in r["compliance_matrix"]]
        md.append("")

    if r["risk_register"]:
        md += ["## Risk Register (prioritized)", "",
               "| ID | Severity | Likelihood | Category | Risk | Evidence | Recommendation |", "|---|---|---|---|---|---|---|"]
        md += [f"| {k['id']} | {k['severity']} | {k['likelihood']} | {k['category']} | **{_cell(k['title'])}**: "
               f"{_cell(k['description'])} | {_refs(k['evidence'])} | {_cell(k['recommendation'])} |" for k in r["risk_register"]]
        md.append("")

    if r["gaps"]:
        md += ["## Missing or Ambiguous Information", ""] + [f"- {g}" for g in r["gaps"]] + [""]
    if r["follow_up_actions"]:
        md += ["## Follow-up Actions", ""] + [f"{i}. {a}" for i, a in enumerate(r["follow_up_actions"], 1)] + [""]

    terms = r["extracted_terms"] + r["derived_terms"]
    if terms:
        md += ["## Extracted Terms", "", "| Term | Value | Evidence | Confidence | Verified | Notes |", "|---|---|---|---|---|---|"]
        md += [f"| {t['name']} | {_cell(t['value'])} | {_refs(t['evidence'])} | {t['confidence']:.2f} | "
               f"{'✅' if t['verified'] else '❌'} | {_cell(t['notes'])} |" for t in terms]
        md.append("")
        if r["missing_terms"]:
            md += [f"**Not found in document:** {', '.join(r['missing_terms'])}", ""]

    policy = r.get("policy") or {}
    if policy.get("source") == "document":
        md += ["## Rules Parsed from the Policy Document", "",
               "These rules were read from the policy by the Policy Parser. Check them before relying on the results.", "",
               "| Rule | Name | Check | Limit | Severity | Source | Traced |", "|---|---|---|---|---|---|---|"]
        for p in policy.get("rules", []):
            limit = f"{p['term']} {p['operator']} {p['value']:g}" if p.get("check_type") == "threshold" else "—"
            md.append(f"| {p['id']} | {_cell(p['name'])} | {p['check_type']} | `{limit}` | {p['severity']} | "
                      f"`{p.get('source') or '—'}` | {'✅' if p.get('verified') else '❌'} |")
        md.append("")

    if r["errors"]:
        md += ["## Errors", ""] + [f"- {e}" for e in r["errors"]] + [""]
    return "\n".join(md)
