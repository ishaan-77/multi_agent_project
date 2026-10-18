"""Unit tests for the verifier and compliance logic (no LLM needed)."""
from pathlib import Path

from src.agents.compliance import check_threshold, derive_terms, judge_rules
from src.agents.ingestion import ingest
from src.agents.verifier import quote_in_chunk, route_after_verification, verifier_node
from src.llm import set_llm_factory
from src.state import EscalationPolicy, Evidence, ExtractedTerm, Rule
from tests.fakes import FakeLLM, edge_extraction

ROOT = Path(__file__).resolve().parent.parent
RULES = ROOT / "rules" / "lending_policy.yaml"
POLICY = EscalationPolicy()


def edge_state(**extra):
    base = ingest(ROOT / "samples" / "edge_case_loan.pdf", RULES)
    return {**base, **extra}


# ---------------------------------------------------------------- verifier

def test_quote_matching_tolerates_whitespace_case_and_smart_quotes():
    chunk = 'The "Effective Date" means 1 March 2026.'
    assert quote_in_chunk("the  “effective date”  MEANS 1 march 2026", chunk)
    assert not quote_in_chunk("Effective Date means 1 June 2027", chunk)


def test_verifier_flags_hallucinated_quote_and_requests_retry():
    state = edge_state(extraction=edge_extraction(hallucinate=True), extraction_attempts=1)
    out = verifier_node(state)
    terms = {t.name: t for t in out["extraction"].terms}
    assert terms["principal_amount"].verified is False
    assert terms["dscr_covenant"].verified is True
    assert route_after_verification({**state, **out}) == "retry"
    # second attempt with the same problem -> give up and continue
    assert route_after_verification({**state, **out, "extraction_attempts": 2}) == "continue"


def test_verifier_flags_unknown_chunk():
    bad = edge_extraction()
    bad.terms[0].evidence = [Evidence(chunk_id="p7:99.1", quote="anything")]
    out = verifier_node(edge_state(extraction=bad, extraction_attempts=1))
    assert "unknown chunk" in out["verification_feedback"][0]


# ---------------------------------------------------------------- derived terms + thresholds

def test_derived_ltv_and_tenor():
    terms = {t.name: t for t in edge_extraction().terms}
    for t in terms.values():
        t.verified = True
    derived = {d.name: d for d in derive_terms(terms)}
    assert derived["ltv_ratio"].normalized == round(40 / 45, 4)
    assert 9.9 < derived["tenor_years"].normalized < 10.1
    assert derived["tenor_years"].confidence == 0.4  # inherits the date conflict


def rule(**kw):
    base = dict(id="T", name="t", category="credit", check_type="threshold", severity="high",
                description="d", term="x", operator="<=", value=0.75)
    return Rule(**{**base, **kw})


def term(normalized, confidence=1.0, verified=True):
    return ExtractedTerm(name="x", value=str(normalized), normalized=normalized, confidence=confidence,
                         verified=verified, evidence=[Evidence(chunk_id="p1:1.1", quote="q")])


def test_threshold_pass_fail_and_missing():
    assert check_threshold(rule(), term(0.6), POLICY).status == "PASS"
    assert check_threshold(rule(), term(0.9), POLICY).status == "FAIL"
    assert check_threshold(rule(), None, POLICY).status == "NEEDS_REVIEW"


def test_uncertainty_never_produces_pass():
    assert check_threshold(rule(), term(0.6, confidence=0.5), POLICY).status == "NEEDS_REVIEW"
    assert check_threshold(rule(), term(0.9, confidence=0.5), POLICY).status == "FAIL"
    assert check_threshold(rule(), term(0.6, verified=False), POLICY).status == "NEEDS_REVIEW"


# ---------------------------------------------------------------- LLM grounding guard

def test_grounding_guard_downgrades_unsupported_pass_and_fills_missing_rules():
    rules = [rule(id="J1", check_type="judgment"), rule(id="J2", check_type="judgment")]
    fake = {"results": [{"rule_id": "J1", "status": "PASS", "evidence": [{"chunk_id": "p9:9.9", "quote": "made up"}], "rationale": "ok"}]}
    set_llm_factory(lambda: FakeLLM({"JudgmentBatch": fake}))
    try:
        results, _, errors = judge_rules(rules, edge_state(extraction=edge_extraction()))
    finally:
        set_llm_factory(None)
    by_id = {r.rule_id: r for r in results}
    assert by_id["J1"].status == "NEEDS_REVIEW" and "Downgraded" in by_id["J1"].rationale
    assert by_id["J2"].status == "NEEDS_REVIEW" and "no decision" in by_id["J2"].rationale
    assert errors == []
