"""Smoke tests for the Streamlit UI (headless, fake LLM)."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.agents.ingestion import load_rules
from src.llm import set_llm_factory
from tests.fakes import FakeLLM, edge_extraction, judgments, risk_report

ROOT = Path(__file__).resolve().parent.parent
APP = str(ROOT / "app.py")
JUDGED = [r.id for r in load_rules(ROOT / "rules" / "lending_policy.yaml").rules if r.check_type != "threshold"]


def test_landing_page_renders():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert at.title[0].value == "Multi-Agent Deal Review"


def test_run_sample_deal_shows_report_tabs():
    set_llm_factory(lambda: FakeLLM({
        "ExtractionResult": edge_extraction(),
        "JudgmentBatch": judgments(JUDGED, "FAIL", chunk="p1:4.1"),
        "RiskReport": risk_report(),
    }))
    try:
        at = AppTest.from_file(APP, default_timeout=60).run()
        at.sidebar.selectbox[0].set_value("edge_case_loan.pdf")
        at.sidebar.button[0].click().run()
    finally:
        set_llm_factory(None)

    assert not at.exception
    assert at.title[0].value == "BRIDGE LOAN FACILITY AGREEMENT"
    assert "Escalate to human review" in at.error[0].value
    assert len(at.tabs) == 7
    assert at.metric[1].value == "12"  # fails
