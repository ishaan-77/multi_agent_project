"""Rule sets in other formats: JSON, CSV (read by code) and PDF/DOCX/TXT/MD (Policy Parser)."""
import json
from pathlib import Path

import pytest

from src.agents.ingestion import IngestionError, load_policy, load_rules
from src.agents.policy_parser import ParsedPolicy, ParsedRule, check_parsed_rules
from src.llm import set_llm_factory
from src.pipeline import run_pipeline
from tests.fakes import FakeLLM, judgments, normal_extraction, risk_report

ROOT = Path(__file__).resolve().parent.parent
NORMAL = ROOT / "samples" / "normal_loan.pdf"
POLICY_PDF = ROOT / "rules" / "lending_policy.pdf"


# ---------------------------------------------------------------- structured formats

def test_json_rules(tmp_path):
    path = tmp_path / "rules.json"
    path.write_text(json.dumps({"policy_name": "JSON policy", "rules": [
        {"id": "J-1", "name": "Exposure", "field": "principal_amount", "operator": "<=", "threshold": 50000000, "severity": "high"},
        {"id": "J-2", "name": "Governing law", "description": "Law must be stated", "operator": "must_exist", "severity": "low"},
    ]}))
    rs = load_rules(path)
    assert [r.check_type for r in rs.rules] == ["threshold", "presence"]
    assert rs.rules[0].value == 50000000


def test_csv_rules(tmp_path):
    path = tmp_path / "credit_rules.csv"
    path.write_text(
        "rule_id,name,description,field,operator,threshold,severity\n"
        "C-1,DSCR minimum,DSCR covenant at least 1.25x,dscr_covenant,greater_than_or_equal,1.25,high\n"
        "C-2,Guarantee,Guarantee required above USD 10M,,,,high\n"
    )
    rs = load_rules(path)
    assert rs.policy_name == "Credit Rules"
    c1, c2 = rs.rules
    assert (c1.check_type, c1.operator, c1.value) == ("threshold", ">=", 1.25)
    assert c2.check_type == "judgment"


def test_bad_json_gives_a_clear_error(tmp_path):
    path = tmp_path / "rules.json"
    path.write_text('{"rules": [ {"id": "x",} ]}')
    with pytest.raises(IngestionError, match="JSON syntax error .* line 1"):
        load_rules(path)


def test_unsupported_rule_format(tmp_path):
    path = tmp_path / "rules.xlsx"
    path.write_bytes(b"x")
    with pytest.raises(IngestionError, match="Unsupported rule set format"):
        load_policy(path)


# ---------------------------------------------------------------- document formats

def test_policy_pdf_becomes_policy_chunks():
    ruleset, chunks, source = load_policy(POLICY_PDF)
    assert ruleset is None and source == "document"
    ids = [c.chunk_id for c in chunks]
    assert "pol:p1:1.2" in ids and all(i.startswith("pol:") for i in ids)
    assert "75%" in next(c.text for c in chunks if c.chunk_id == "pol:p1:1.2")


def test_policy_docx_is_read(tmp_path):
    docx = pytest.importorskip("docx")
    doc = docx.Document()
    doc.add_paragraph("CREDIT POLICY")
    doc.add_paragraph("1. Limits")
    doc.add_paragraph("1.1 The principal must not exceed USD 750,000. Severity: medium.")
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text, table.rows[0].cells[1].text = "Maximum rate", "9%"
    path = tmp_path / "policy.docx"
    doc.save(path)
    _, chunks, source = load_policy(path)
    text = {c.chunk_id: c.text for c in chunks}
    assert source == "document"
    assert "USD 750,000" in text["pol:p1:1.1"] and "Maximum rate" in text["pol:p1:1.1"]


# ---------------------------------------------------------------- the parser's code checks

def _parsed(**overrides):
    base = dict(id="1.2", name="LTV", category="credit", check_type="threshold", severity="critical",
                description="LTV max 75%", term="ltv_ratio", operator="<=", value=0.75,
                source_chunk_id="pol:p1:1.2", source_quote="The loan-to-value ratio must not exceed 75%")
    return ParsedRule(**{**base, **overrides})


def test_parser_checks_quotes_thresholds_and_ids():
    _, chunks, _ = load_policy(POLICY_PDF)
    parsed = ParsedPolicy(policy_name="P", rules=[
        _parsed(),                                                         # good
        _parsed(source_quote="LTV may be up to 95% with approval"),        # invented quote
        _parsed(id="1.2", value=None),                                     # duplicate id + no number
    ])
    rules, notes = check_parsed_rules(parsed, chunks)
    assert rules[0].verified is True and rules[0].check_type == "threshold"
    assert rules[1].verified is False
    assert rules[2].id != "1.2" and rules[2].check_type == "judgment"
    assert any("source quote not found" in n for n in notes)


# ---------------------------------------------------------------- end to end

@pytest.fixture
def fake_llm():
    yield lambda responses: set_llm_factory(lambda: FakeLLM(responses))
    set_llm_factory(None)


def test_pipeline_with_policy_pdf_runs_parser_then_reviews(fake_llm, tmp_path):
    parsed = ParsedPolicy(policy_name="Harborview (PDF)", rules=[
        _parsed(),
        _parsed(id="2.2", name="DSCR", term="dscr_covenant", operator=">=", value=1.25, severity="high",
                source_chunk_id="pol:p1:2.2", source_quote="debt service coverage ratio covenant of at least 1.25x"),
        _parsed(id="3.3", name="Governing law", check_type="presence", term=None, operator=None, value=None,
                severity="low", source_chunk_id="pol:p1:3.3", source_quote="must state a governing law"),
        _parsed(id="9.9", name="Invented", check_type="judgment", term=None, operator=None, value=None,
                source_chunk_id="pol:p1:3.3", source_quote="borrowers must be headquartered in Ohio"),
    ])
    steps = []
    fake_llm({"ParsedPolicy": parsed, "ExtractionResult": normal_extraction(),
              "JudgmentBatch": judgments(["3.3"], "PASS", chunk="p3:14.1"), "RiskReport": risk_report()})
    report, _ = run_pipeline(NORMAL, POLICY_PDF, tmp_path, on_step=lambda n, u: steps.append(n))

    assert steps[:3] == ["ingest", "parse_policy", "extract"]
    m = {c["rule_id"]: c for c in report["compliance_matrix"]}
    assert m["1.2"]["status"] == "PASS" and m["1.2"]["method"] == "deterministic"   # 64.9% <= 0.75
    assert m["2.2"]["status"] == "PASS"
    assert m["3.3"]["status"] == "PASS"
    assert m["9.9"]["status"] == "NEEDS_REVIEW" and "could not be found" in m["9.9"]["rationale"]
    assert report["policy"]["source"] == "document"
    assert "Rules Parsed from the Policy Document" in (Path(report["output_dir"]) / "report.md").read_text()


def test_policy_parser_failure_fails_the_run_safely(fake_llm, tmp_path):
    fake_llm({"ParsedPolicy": ValueError("bad output")})
    report, _ = run_pipeline(NORMAL, POLICY_PDF, tmp_path)
    assert report["status"] == "failed"
    assert report["decision"] == "ESCALATE_TO_HUMAN_REVIEW"
    assert "policy_parser" in report["errors"][0]
