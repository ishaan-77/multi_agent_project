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


def test_wrapped_numbers_are_not_mistaken_for_clauses_or_sections():
    from src.agents.ingestion import chunk_document
    page = (
        "4. Interest\n"
        "4.1  The rate of interest is fixed at\n"
        "4.75% per annum.\n"
        "4.2  Default interest accrues at a rate of\n"
        "4.75 per cent above the fixed rate, or\n"
        "2.75 per cent if the Lender agrees, as notified under clause\n"
        "2. The Borrower shall pay on demand.\n"
        "4.3  Interest is calculated on a 360-day year.\n"
        "5. Repayment\n"
        "5.1  Repaid in full at maturity.\n"
    )
    chunks, _, _ = chunk_document([page])
    ids = [c.chunk_id for c in chunks]
    assert ids == ["p1:4.1", "p1:4.2", "p1:4.3", "p1:5.1"]
    text_42 = chunks[1].text
    assert "4.75 per cent" in text_42 and "2.75 per cent" in text_42 and "2. The Borrower" in text_42


ALT_RULES = """policy_id: SYN-1
policy_name: Alternative layout
rules:
  - rule_id: R-001
    name: Principal limit
    description: Principal must not exceed USD 750,000.
    field: requested_principal_usd
    operator: less_than_or_equal
    threshold: 750000
    severity: Medium
  - rule_id: R-002
    name: Maturity required
    description: A maturity date must be stated.
    field: maturity_date
    operator: must_exist
    severity: high
  - rule_id: R-003
    name: Governing law
    description: A real governing-law jurisdiction must be named.
    operator: must_be_specified_real_jurisdiction
    severity: high
"""


def test_alternative_rule_layout_is_normalized(tmp_path):
    path = tmp_path / "alt.yaml"
    path.write_text(ALT_RULES)
    rs = load_rules(path)
    r1, r2, r3 = rs.rules
    assert (r1.id, r1.check_type, r1.term, r1.operator, r1.value, r1.severity) == (
        "R-001", "threshold", "requested_principal_usd", "<=", 750000, "medium")
    assert r2.check_type == "presence"
    assert r3.check_type == "judgment" and "must_be_specified_real_jurisdiction" in r3.description
    assert rs.version == "SYN-1"


def test_bad_yaml_indentation_gives_a_clear_error(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(ALT_RULES.replace("  - rule_id: R-001\n", "- rule_id: R-001\n", 1))
    with pytest.raises(IngestionError, match=r"YAML syntax error .* line 5.*indentation"):
        load_rules(path)


def test_clause_prefix_section_text_and_running_headers():
    from src.agents.ingestion import chunk_document
    header = "CONFIDENTIAL TEST DATA\n"
    page1 = header + "Page 1\nLOAN REQUEST\n1. Details\nRequested principal\nUSD 500,000\n2. Terms\nClause 2.1 — Interest. Fixed at 8.5%.\n"
    page2 = header + "Page 2\n3. Not Included\nNo governing law is specified.\n"
    chunks, title, structured = chunk_document([page1, page2])
    by_id = {c.chunk_id: c for c in chunks}
    assert title == "LOAN REQUEST" and structured
    assert list(by_id) == ["p1:intro", "p1:1", "p1:2.1", "p2:3"]
    assert by_id["p1:2.1"].text == "Interest. Fixed at 8.5%."
    assert "USD 500,000" in by_id["p1:1"].text
    assert "governing law" in by_id["p2:3"].text           # section text is kept, not dropped
    assert all("CONFIDENTIAL" not in c.text for c in chunks)  # repeated header removed


def test_policy_terms_are_added_to_the_extraction_catalog(tmp_path):
    from src.agents.extraction import build_prompt
    path = tmp_path / "alt.yaml"
    path.write_text(ALT_RULES)
    prompt = build_prompt({"ruleset": load_rules(path), "chunks": ingest(NORMAL, RULES)["chunks"]})
    assert "- requested_principal_usd: Required by policy rule R-001" in prompt
