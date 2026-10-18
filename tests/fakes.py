"""A fake LLM that returns canned structured outputs, so the graph can be tested offline.

responses maps a schema class name -> one of:
  - a Pydantic object / dict to return
  - an Exception to raise
  - a list of the above, consumed one per call (to simulate "bad first answer, good retry")
"""
from __future__ import annotations

from src.state import Evidence as E, ExtractedTerm as T, ExtractionResult, Risk, RiskReport


class FakeLLM:
    def __init__(self, responses: dict):
        self.responses = responses
        self.calls: list[str] = []

    def with_structured_output(self, schema):
        parent = self

        class _Runner:
            def invoke(self, messages):
                name = schema.__name__
                parent.calls.append(name)
                r = parent.responses[name]
                if isinstance(r, list):
                    r = r.pop(0) if len(r) > 1 else r[0]
                if isinstance(r, Exception):
                    raise r
                return r.model_copy(deep=True) if hasattr(r, "model_copy") else r

        return _Runner()


def normal_extraction() -> ExtractionResult:
    return ExtractionResult(terms=[
        T(name="borrower", value="Northwind Fabrication Ltd.", evidence=[E(chunk_id="p1:1.2", quote="Northwind Fabrication Ltd., a Delaware corporation")], confidence=1),
        T(name="principal_amount", value="USD 12,000,000", normalized=12_000_000, unit="USD", evidence=[E(chunk_id="p1:3.1", quote="aggregate amount of USD 12,000,000")], confidence=1),
        T(name="collateral_value", value="USD 18,500,000", normalized=18_500_000, unit="USD", evidence=[E(chunk_id="p2:7.2", quote="valued the collateral at USD 18,500,000")], confidence=0.95),
        T(name="effective_date", value="2026-03-01", evidence=[E(chunk_id="p1:2.1", quote='"Effective Date" means 1 March 2026.')], confidence=1),
        T(name="maturity_date", value="2031-03-31", evidence=[E(chunk_id="p2:5.2", quote="The Final Maturity Date is 31 March 2031")], confidence=1),
        T(name="dscr_covenant", value="1.35x", normalized=1.35, evidence=[E(chunk_id="p2:9.1", quote="DSCR of not less than 1.35x")], confidence=1),
        T(name="audited_financials_days", value="120 days", normalized=120, evidence=[E(chunk_id="p3:10.1", quote="audited annual financial statements within 120 days")], confidence=1),
    ], missing_terms=[])


def edge_extraction(hallucinate: bool = False) -> ExtractionResult:
    principal_quote = "bridge loan of USD 40 million" if hallucinate else "aggregate amount of USD 40,000,000"
    return ExtractionResult(terms=[
        T(name="principal_amount", value="USD 40,000,000", normalized=40_000_000, unit="USD", evidence=[E(chunk_id="p1:3.1", quote=principal_quote)], confidence=1),
        T(name="collateral_value", value="USD 45,000,000 (borrower estimate)", normalized=45_000_000, unit="USD", evidence=[E(chunk_id="p2:6.2", quote="preliminary internal estimate of the Bayfront Parcel is USD 45,000,000")], confidence=0.5, notes="Borrower estimate; independent valuation to be delivered"),
        T(name="effective_date", value="2026-04-01", evidence=[E(chunk_id="p1:2.1", quote='"Effective Date" means 1 April 2026.'), E(chunk_id="p3:S1.1", quote="Effective Date: 1 May 2026.")], confidence=0.4, notes="Conflict: 1 April 2026 (2.1) vs 1 May 2026 (Schedule 1)"),
        T(name="maturity_date", value="2036-03-31", evidence=[E(chunk_id="p2:5.2", quote="The Final Maturity Date is 31 March 2036.")], confidence=1),
        T(name="dscr_covenant", value="1.10x", normalized=1.10, evidence=[E(chunk_id="p2:7.1", quote="not less than 1.10x")], confidence=1),
        T(name="audited_financials_days", value="180 days", normalized=180, evidence=[E(chunk_id="p2:8.1", quote="within 180 days after the end of each financial year")], confidence=1),
    ], missing_terms=["guarantor", "guarantee", "prepayment_terms", "conditions_precedent"])


def judgments(rule_ids: list[str], status: str = "PASS", chunk: str = "p1:3.1") -> dict:
    return {"results": [{"rule_id": r, "status": status, "evidence": [{"chunk_id": chunk, "quote": "x"}], "rationale": "test"} for r in rule_ids]}


def risk_report() -> RiskReport:
    return RiskReport(
        risks=[
            Risk(id="x", category="financial", title="Minor", description="d", severity="low", likelihood="low", recommendation="r"),
            Risk(id="y", category="financial", title="LTV breach", description="d", severity="critical", likelihood="high",
                 evidence=[E(chunk_id="p2:6.2", quote="q"), E(chunk_id="p9:99.9", quote="fake")], recommendation="r"),
        ],
        gaps=["Margin undefined"], executive_summary="Summary.", follow_up_actions=["Obtain valuation"],
    )
