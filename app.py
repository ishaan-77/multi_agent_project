"""Streamlit UI for the deal review pipeline.

    streamlit run app.py

A thin layer over src.pipeline.run_pipeline: pick or upload a deal and a rule set, run the
agents with live progress, and explore the report. Saved reports in outputs/ can be opened
without calling the LLM.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from src.agents.ingestion import IngestionError, ingest
from src.report import render_markdown

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "samples"
DEFAULT_RULES = ROOT / "rules" / "lending_policy.yaml"
SAVED = ROOT / "outputs"
RUNS = ROOT / "outputs" / "runs"  # git-ignored, so UI runs don't overwrite committed samples

AGENT_LABELS = {
    "ingest": "📄 Ingestion: chunking document, loading rules",
    "parse_policy": "📜 Policy Parser (Gemini): turning the policy document into rules",
    "extract": "🔎 Term Extraction (Gemini)",
    "verify": "✅ Evidence Verifier: checking every quote",
    "compliance": "📋 Compliance Review: code checks + Gemini judgment",
    "risk": "⚠️ Risk & Summary (Gemini)",
    "escalate": "🚩 Escalation: applying policy",
    "assemble": "🧩 Orchestrator: assembling report",
}
STATUS_BADGE = {"PASS": "✅ PASS", "FAIL": "❌ FAIL", "NEEDS_REVIEW": "⚠️ REVIEW"}
SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

st.set_page_config(page_title="Deal Review Pipeline", page_icon="📑", layout="wide")


# ---------------------------------------------------------------- helpers

def save_upload(upload) -> Path:
    folder = Path(tempfile.mkdtemp(prefix="deal_review_"))
    path = folder / upload.name
    path.write_bytes(upload.getvalue())
    return path


def step_detail(update: dict) -> str:
    entries = [a for a in update.get("audit_log", []) if a.event in ("completed", "finished", "failed", "fallback")]
    errors = update.get("errors") or []
    text = entries[-1].detail if entries else ""
    if errors:
        text += f"  ⚠️ {errors[0][:160]}"
    return text


@st.cache_data(show_spinner=False)
def chunk_lookup(doc_path: str) -> dict[str, dict]:
    """Re-ingest the document (deterministic, no LLM) so evidence IDs can be resolved to text."""
    try:
        result = ingest(doc_path, DEFAULT_RULES)
    except (IngestionError, OSError):
        return {}
    return {c.chunk_id: c.model_dump() for c in result["chunks"]}


def refs(evidence: list[dict]) -> str:
    return ", ".join(e["chunk_id"] for e in evidence)


# ---------------------------------------------------------------- sidebar

st.sidebar.title("📑 Deal Review")
mode = st.sidebar.radio("Mode", ["Run a new review", "Open a saved report"], label_visibility="collapsed")

if mode == "Run a new review":
    st.sidebar.subheader("1. Deal document")
    sample_files = sorted(p.name for p in SAMPLES.glob("*.pdf"))
    deal_choice = st.sidebar.radio("Source", ["Sample", "Upload"], horizontal=True, key="deal_src")
    if deal_choice == "Sample":
        deal_name = st.sidebar.selectbox("Sample deal", sample_files)
        deal_path = SAMPLES / deal_name if deal_name else None
    else:
        up = st.sidebar.file_uploader("PDF, DOCX, TXT or MD", type=["pdf", "docx", "txt", "md"])
        deal_path = save_upload(up) if up else None

    st.sidebar.subheader("2. Rule set")
    rules_up = st.sidebar.file_uploader(
        "Custom rules (optional)", type=["yaml", "yml", "json", "csv", "pdf", "docx", "txt", "md"],
        help="Structured rules (YAML, JSON, CSV) are read directly. A written policy (PDF, DOCX, TXT, MD) "
             "is turned into rules by the Policy Parser agent, using one extra Gemini call.",
    )
    rules_path = save_upload(rules_up) if rules_up else DEFAULT_RULES
    st.sidebar.caption(f"Using: `{Path(rules_path).name}`")

    is_policy_doc = Path(rules_path).suffix.lower() in {".pdf", ".docx", ".txt", ".md"}
    st.sidebar.caption(f"This run makes {4 if is_policy_doc else 3} Gemini calls (free tier: ~20/day).")
    if st.sidebar.button("▶ Run review", type="primary", disabled=deal_path is None, use_container_width=True):
        from src.pipeline import run_pipeline

        with st.status("Running agents…", expanded=True) as status:
            def on_step(node: str, update: dict) -> None:
                st.write(f"**{AGENT_LABELS.get(node, node)}** — {step_detail(update)}")

            try:
                report, final_state = run_pipeline(deal_path, rules_path, RUNS, on_step=on_step)
            except Exception as exc:  # last-resort guard; the graph itself shouldn't raise
                status.update(label="Pipeline crashed", state="error")
                st.exception(exc)
                st.stop()
            ok = report["status"] == "completed"
            status.update(label=f"Finished: {report['status']}", state="complete" if ok else "error", expanded=not ok)

        st.session_state["report"] = report
        st.session_state["audit"] = [a.model_dump() for a in final_state.get("audit_log", [])]
else:
    saved = sorted(p.parent.name for p in SAVED.glob("*/report.json"))
    if not saved:
        st.sidebar.info("No saved reports yet. Run `python run.py --deal ...` first.")
    else:
        choice = st.sidebar.selectbox("Saved report", saved)
        if st.sidebar.button("Open", type="primary", use_container_width=True):
            folder = SAVED / choice
            st.session_state["report"] = json.loads((folder / "report.json").read_text())
            audit_file = folder / "audit_log.json"
            st.session_state["audit"] = json.loads(audit_file.read_text()) if audit_file.exists() else []


# ---------------------------------------------------------------- main view

report = st.session_state.get("report")
if report is None:
    st.title("Multi-Agent Deal Review")
    st.markdown(
        "Upload a loan agreement and a compliance rule set. Six agents extract the terms, check every "
        "quote against the source, test each policy rule, assess risk and decide what needs a human.\n\n"
        "**Start from the sidebar** by running a sample deal or opening a saved report."
    )
    st.code(" → ".join(AGENT_LABELS[k].split(":")[0] for k in AGENT_LABELS), language=None)
    st.stop()

doc = report.get("document") or {}
st.title(doc.get("title", "Deal Review"))
st.caption(f"`{doc.get('path', '')}` · {doc.get('page_count', '?')} pages · "
           f"policy: {(report.get('policy') or {}).get('name', '?')} · run status: `{report['status']}`")

if report["decision"] == "ESCALATE_TO_HUMAN_REVIEW":
    st.error(f"🔴 **Escalate to human review**: {len(report['escalations'])} items need attention")
else:
    st.success("🟢 **No escalation required**")
for err in report.get("errors", []):
    st.warning(f"Agent error (pipeline degraded gracefully): {err[:300]}")

matrix = report.get("compliance_matrix", [])
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Pass", sum(c["status"] == "PASS" for c in matrix))
c2.metric("Fail", sum(c["status"] == "FAIL" for c in matrix))
c3.metric("Needs review", sum(c["status"] == "NEEDS_REVIEW" for c in matrix))
c4.metric("Risks", len(report.get("risk_register", [])))
c5.metric("Terms verified", f"{sum(bool(t.get('verified')) for t in report.get('extracted_terms', []))}"
                            f"/{len(report.get('extracted_terms', []))}")

tabs = st.tabs(["Summary", "Escalations", "Compliance matrix", "Risk register", "Extracted terms", "Evidence lookup", "Audit log"])

with tabs[0]:
    st.subheader("Executive summary")
    st.write(report.get("executive_summary") or "_Not available._")
    left, right = st.columns(2)
    with left:
        st.subheader("Missing or ambiguous information")
        for g in report.get("gaps", []):
            st.markdown(f"- {g}")
    with right:
        st.subheader("Follow-up actions")
        for i, a in enumerate(report.get("follow_up_actions", []), 1):
            st.markdown(f"{i}. {a}")

with tabs[1]:
    if report["escalations"]:
        st.dataframe(pd.DataFrame(report["escalations"])[["severity", "source", "reason"]],
                     use_container_width=True, hide_index=True)
    else:
        st.info("Nothing escalated.")

with tabs[2]:
    if matrix:
        df = pd.DataFrame([{
            "Rule": c["rule_id"], "Name": c["rule_name"], "Severity": c["severity"],
            "Result": STATUS_BADGE[c["status"]], "Evidence": refs(c["evidence"]),
            "Method": c["method"], "Rationale": c["rationale"],
        } for c in matrix])
        st.dataframe(df, use_container_width=True, hide_index=True, height=(len(df) + 1) * 35 + 3,
                     column_config={"Rationale": st.column_config.TextColumn(width="large")})
    policy = report.get("policy") or {}
    if policy.get("source") == "document":
        with st.expander(f"Rules parsed from the policy document ({len(policy.get('rules', []))})", expanded=False):
            st.caption("The Policy Parser read these rules from the uploaded policy. "
                       "'Traced' means its quote was found in the policy text by code.")
            st.dataframe(pd.DataFrame([{
                "Rule": p["id"], "Name": p["name"], "Check": p["check_type"],
                "Limit": f"{p['term']} {p['operator']} {p['value']:g}" if p["check_type"] == "threshold" else "",
                "Severity": p["severity"], "Source": p.get("source") or "", "Traced": "✅" if p.get("verified") else "❌",
                "Policy text": p.get("source_quote") or "",
            } for p in policy.get("rules", [])]), use_container_width=True, hide_index=True)

with tabs[3]:
    risks = sorted(report.get("risk_register", []), key=lambda r: SEV_ORDER[r["severity"]])
    for r in risks:
        with st.expander(f"{r['id']} · {r['severity'].upper()} · {r['category']} · {r['title']}",
                         expanded=r["severity"] in ("critical", "high")):
            st.write(r["description"])
            st.markdown(f"**Likelihood:** {r['likelihood']}  \n**Evidence:** {refs(r['evidence']) or '—'}  \n"
                        f"**Recommendation:** {r['recommendation']}")

with tabs[4]:
    terms = report.get("extracted_terms", []) + report.get("derived_terms", [])
    if terms:
        st.dataframe(pd.DataFrame([{
            "Term": t["name"], "Value": t["value"], "Evidence": refs(t["evidence"]),
            "Confidence": t["confidence"], "Verified": "✅" if t["verified"] else "❌", "Notes": t.get("notes") or "",
        } for t in terms]), use_container_width=True, hide_index=True)
    if report.get("missing_terms"):
        st.caption("Not found in document: " + ", ".join(report["missing_terms"]))

with tabs[5]:
    chunks = chunk_lookup(doc.get("path", ""))
    if not chunks:
        st.info("Source document not available for lookup.")
    else:
        st.caption("Every evidence ID in the report points to a clause below: `p<page>:<clause>`.")
        cid = st.selectbox("Evidence ID", list(chunks))
        c = chunks[cid]
        st.markdown(f"**Page {c['page']} · {c['section']}**")
        st.info(c["text"])

with tabs[6]:
    audit = st.session_state.get("audit", [])
    if audit:
        st.dataframe(pd.DataFrame(audit)[["timestamp", "agent", "event", "detail"]],
                     use_container_width=True, hide_index=True)

st.divider()
d1, d2 = st.columns(2)
d1.download_button("⬇ Download report (Markdown)", render_markdown(report), file_name="report.md", use_container_width=True)
d2.download_button("⬇ Download report (JSON)", json.dumps(report, indent=2, default=str), file_name="report.json",
                   use_container_width=True)
