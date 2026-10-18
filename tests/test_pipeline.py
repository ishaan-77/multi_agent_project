"""End-to-end tests of the LangGraph orchestrator with a fake LLM."""
import json
from pathlib import Path

import pytest

from src.agents.ingestion import load_rules
from src.llm import set_llm_factory
from src.pipeline import run_pipeline
from tests.fakes import FakeLLM, edge_extraction, judgments, normal_extraction, risk_report

ROOT = Path(__file__).resolve().parent.parent
RULES = ROOT / "rules" / "lending_policy.yaml"
NORMAL = ROOT / "samples" / "normal_loan.pdf"
EDGE = ROOT / "samples" / "edge_case_loan.pdf"
JUDGED = [r.id for r in load_rules(RULES).rules if r.check_type != "threshold"]


@pytest.fixture
def fake_llm():
    holder = {}

    def install(responses):
        holder["llm"] = FakeLLM(responses)
        set_llm_factory(lambda: holder["llm"])
        return holder["llm"]

    yield install
    set_llm_factory(None)


def test_normal_case_end_to_end(fake_llm, tmp_path):
    fake_llm({
        "ExtractionResult": normal_extraction(),
        "JudgmentBatch": judgments(JUDGED, "PASS"),
        "RiskReport": risk_report().model_copy(update={"risks": []}),
    })
    report, state = run_pipeline(NORMAL, RULES, tmp_path)

    assert report["status"] == "completed"
    assert len(report["compliance_matrix"]) == 13
    assert all(c["status"] == "PASS" for c in report["compliance_matrix"])
    assert report["decision"] == "NO_ESCALATION_REQUIRED"
    assert state["extraction_attempts"] == 1
    out = Path(report["output_dir"])
    assert (out / "report.md").exists() and (out / "audit_log.json").exists()
    assert json.loads((out / "report.json").read_text())["status"] == "completed"


def test_edge_case_retries_bad_citation_and_escalates(fake_llm, tmp_path):
    llm = fake_llm({
        "ExtractionResult": [edge_extraction(hallucinate=True), edge_extraction()],
        "JudgmentBatch": judgments(JUDGED, "FAIL", chunk="p1:4.1"),
        "RiskReport": risk_report(),
    })
    report, state = run_pipeline(EDGE, RULES, tmp_path)
    matrix = {c["rule_id"]: c for c in report["compliance_matrix"]}

    assert llm.calls.count("ExtractionResult") == 2          # verifier triggered one retry
    assert state["extraction_attempts"] == 2
    assert matrix["CR-01"]["status"] == "PASS"               # 40M <= 50M
    assert matrix["CR-03"]["status"] == "FAIL"               # LTV 88.9% on low-confidence value
    assert matrix["CR-05"]["status"] == "FAIL"               # ~10y tenor
    assert matrix["CR-06"]["status"] == "FAIL"               # DSCR 1.10x
    assert matrix["CR-08"]["status"] == "FAIL"               # 180 days
    assert report["decision"] == "ESCALATE_TO_HUMAN_REVIEW"
    assert report["escalations"][0]["severity"] == "critical"
    # risks are re-ranked and invalid citations removed
    assert report["risk_register"][0]["id"] == "R-01" and report["risk_register"][0]["severity"] == "critical"
    assert [e["chunk_id"] for e in report["risk_register"][0]["evidence"]] == ["p2:6.2"]
    # missing terms always surface as gaps
    assert any("prepayment_terms" in g for g in report["gaps"])


def test_risk_llm_failure_falls_back_and_completes_with_errors(fake_llm, tmp_path, monkeypatch):
    monkeypatch.setattr("src.llm.time.sleep", lambda s: None)
    fake_llm({
        "ExtractionResult": edge_extraction(),
        "JudgmentBatch": judgments(JUDGED, "NEEDS_REVIEW", chunk="p1:4.1"),
        "RiskReport": RuntimeError("429 RESOURCE_EXHAUSTED"),
    })
    report, _ = run_pipeline(EDGE, RULES, tmp_path)
    assert report["status"] == "completed_with_errors"
    assert report["executive_summary"].startswith("[Automated fallback")
    assert report["risk_register"]  # built from compliance FAILs
    assert any(e["source"] == "system" for e in report["escalations"])


def test_extraction_failure_still_produces_a_report(fake_llm, tmp_path):
    fake_llm({"ExtractionResult": ValueError("garbage output")})
    report, state = run_pipeline(NORMAL, RULES, tmp_path)
    assert report["status"] == "failed"
    assert report["decision"] == "ESCALATE_TO_HUMAN_REVIEW"
    assert any(a.event == "llm_call_failed" for a in state["audit_log"])
    assert (Path(report["output_dir"]) / "report.md").exists()


def test_missing_document_fails_gracefully(fake_llm, tmp_path):
    fake_llm({})
    report, _ = run_pipeline(ROOT / "samples" / "missing.pdf", RULES, tmp_path)
    assert report["status"] == "failed"
    assert "not found" in report["errors"][0]


def test_high_llm_risk_alone_does_not_escalate_but_critical_does(fake_llm, tmp_path):
    from src.state import Risk
    high = Risk(id="x", category="legal", title="Soft concern", description="d", severity="high", likelihood="medium", recommendation="r")
    base = {"ExtractionResult": normal_extraction(), "JudgmentBatch": judgments(JUDGED, "PASS")}

    fake_llm({**base, "RiskReport": risk_report().model_copy(update={"risks": [high]})})
    report, _ = run_pipeline(NORMAL, RULES, tmp_path)
    assert report["decision"] == "NO_ESCALATION_REQUIRED"
    assert report["risk_register"][0]["severity"] == "high"   # still reported

    fake_llm({**base, "RiskReport": risk_report().model_copy(update={"risks": [high.model_copy(update={"severity": "critical"})]})})
    report, _ = run_pipeline(NORMAL, RULES, tmp_path)
    assert report["decision"] == "ESCALATE_TO_HUMAN_REVIEW"
