# Multi-Agent Deal Review Pipeline

A multi-agent system that reviews a financial deal document (a commercial loan agreement)
against a compliance rule set and produces an evidence-backed report. The report contains
extracted terms, a compliance matrix, a prioritized risk register, and an executive summary.

Built with **LangGraph** and **Google Gemini**, with a thin **Streamlit** UI.

> 🚧 Work in progress. See the build plan below.

## Setup

```bash
git clone https://github.com/<your-username>/multi_agent_project.git
cd multi_agent_project
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m scripts.check_gemini
```

After copying, paste your Gemini key into `.env`. `check_gemini` verifies the key and structured output.

## Run

```bash
python run.py --deal samples/normal_loan.pdf
python run.py --deal samples/edge_case_loan.pdf
python -m pytest -q
```

Each run writes `outputs/<deal name>/report.md`, `report.json` and `audit_log.json`.
The tests use a fake LLM, so they run offline without an API key.

## Sample inputs

All data is synthetic. Parties and figures are fictional.

| File | Purpose |
|---|---|
| `samples/normal_loan.pdf` | Normal case: a clean term loan |
| `samples/edge_case_loan.pdf` | Edge case: LTV breach, undefined margin, conflicting dates, missing clauses |
| `rules/lending_policy.yaml` | 13-rule synthetic credit policy |
| `samples/EXPECTED.md` | Hand-written answer key for both cases |

To regenerate the PDFs, run `python -m scripts.make_samples`.

## Planned architecture

```
Ingest → Extract Terms → Verify Evidence ─(retry ≤1)→ Extract
                              ↓
                     Compliance Review → Risk & Summary → [Escalation?] → Report
```

| Agent | Type | Role |
|---|---|---|
| Ingestion | code | Split the PDF into chunks with stable page/section/clause IDs |
| Term Extraction | LLM | Extract material terms, each with a clause reference and a quote |
| Evidence Verifier | code | Confirm that every quote exists in its cited clause |
| Compliance Review | code + LLM | Mark each rule PASS / FAIL / NEEDS_REVIEW, with evidence |
| Risk & Summary | LLM | Build the risk register, gaps and ambiguities, executive summary |
| Orchestrator | LangGraph | Manage shared state, routing, retries, audit log, final report |

## Build plan

- [x] Phase 0: Project skeleton, config, Gemini smoke test
- [x] Phase 1: Synthetic sample deals and rule set
- [x] Phase 2: State schemas and ingestion agent
- [x] Phase 3: Term extraction and evidence verifier
- [x] Phase 4: Compliance review agent
- [x] Phase 5: Risk & summary agent and escalation
- [x] Phase 6: LangGraph orchestrator, CLI, report rendering
- [ ] Phase 7: End-to-end runs and tests
- [ ] Phase 8: Streamlit UI
- [ ] Phase 9: Architecture diagram, docs, Loom
