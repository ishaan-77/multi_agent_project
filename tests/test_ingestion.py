from pathlib import Path

import pytest

from src.agents.ingestion import IngestionError, ingest, ingestion_node, load_rules

ROOT = Path(__file__).resolve().parent.parent
NORMAL = ROOT / "samples" / "normal_loan.pdf"
EDGE = ROOT / "samples" / "edge_case_loan.pdf"
RULES = ROOT / "rules" / "lending_policy.yaml"


def by_clause(result):
    return {c.clause: c for c in result["chunks"]}


def test_normal_doc_is_chunked_by_clause_with_pages():
    result = ingest(NORMAL, RULES)
    chunks = by_clause(result)

    assert result["document"].structured is True
    assert result["document"].page_count == 3
    assert chunks["3.1"].chunk_id == "p1:3.1"
    assert "USD 12,000,000" in chunks["3.1"].text
    assert chunks["7.2"].page == 2
    assert chunks["7.2"].section == "7. Security and Collateral"
    assert "18,500,000" in chunks["7.2"].text


def test_wrapped_lines_are_joined_into_one_clause():
    chunks = by_clause(ingest(NORMAL, RULES))
    # 6.1 wraps over several lines in the PDF
    assert "nil thereafter" in chunks["6.1"].text


def test_page_furniture_is_removed():
    for c in ingest(NORMAL, RULES)["chunks"]:
        assert "SYNTHETIC DOCUMENT" not in c.text
        assert not c.text.startswith("Page ")


def test_chunk_ids_are_unique_and_stable():
    a = [c.chunk_id for c in ingest(EDGE, RULES)["chunks"]]
    b = [c.chunk_id for c in ingest(EDGE, RULES)["chunks"]]
    assert a == b
    assert len(a) == len(set(a))


def test_edge_doc_schedule_clauses_are_captured():
    chunks = by_clause(ingest(EDGE, RULES))
    assert "1 May 2026" in chunks["S1.1"].text        # conflicting date lives in the schedule
    assert chunks["S1.1"].section.startswith("SCHEDULE 1")
    assert "1 April 2026" in chunks["2.1"].text


def test_rules_load_and_validate():
    ruleset = load_rules(RULES)
    assert len(ruleset.rules) == 13
    assert ruleset.escalation.min_term_confidence == 0.7


def test_missing_file_raises():
    with pytest.raises(IngestionError):
        ingest(ROOT / "samples" / "nope.pdf", RULES)


def test_node_turns_errors_into_state_instead_of_crashing():
    out = ingestion_node({"deal_path": "missing.pdf", "rules_path": str(RULES)})
    assert out["status"] == "failed"
    assert out["errors"] and out["audit_log"][0].event == "failed"


def test_unstructured_text_falls_back_to_page_blocks(tmp_path):
    doc = tmp_path / "memo.txt"
    doc.write_text("A short memo without numbered clauses.\n\nThe loan amount is USD 5,000,000.")
    result = ingest(doc, RULES)
    assert result["document"].structured is False
    assert result["chunks"][1].chunk_id == "p1:b2"
