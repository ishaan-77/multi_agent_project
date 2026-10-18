# Loom demo script (~5 minutes)

Before recording:
- Run `streamlit run app.py`.
- Open `docs/architecture.png` in another tab.
- Open the edge-case PDF.

## 1. The problem (20s)
"Reviewing a loan agreement means extracting terms, checking them against policy, assessing
risk and deciding what needs a human. I built a multi-agent pipeline that does this and
backs every claim with a citation to the source clause."

## 2. Architecture (60s): show `docs/architecture.png`
- There are seven agents, and the LangGraph orchestrator owns the shared state and routing.
- Point out the colours. Code agents do work that must be deterministic and auditable: chunk IDs, quote verification, arithmetic and escalation policy. Gemini does the reading comprehension: extraction, judgment rules and risk.
- Point at the purple retry loop: a hallucinated quote sends the extractor back once, with feedback.
- Point at the red failure route: the system degrades instead of crashing, and a report is always produced.
- Point at the shared state band: Pydantic contracts, and append-only errors and audit log.

## 3. Live run: edge case (90s)
- In the sidebar: Run a new review → Sample → `edge_case_loan.pdf` → Run.
- While it runs, narrate each agent as it completes.
- When it finishes, show the red **Escalate** banner and the metrics row (2 pass, 11 fail).
- Compliance matrix tab:
  - CR-03 LTV 88.9% is computed **in code** (`deterministic` method).
  - CR-02 margin undefined is judged by Gemini (`llm` method).
- Evidence lookup tab: pick `p3:S1.1` to show that "Effective Date: 1 May 2026" conflicts with `p1:2.1`. That's traceability.
- Risk register: the critical LTV risk is at the top.

## 4. Normal case (30s)
- Open a saved report → `normal_loan`.
- 13/13 pass, 28/28 terms verified, no escalation.
- Mention the design decision: only *critical* LLM-judged risks force escalation, and that's configurable in YAML.

## 5. Failure handling (40s)
- Open a saved report → `edge_case_loan_quota_exhausted`.
- "This is a real run where the Gemini free quota ran out partway through. The code-checked rules still FAIL correctly, the Gemini rules became NEEDS_REVIEW, the risk agent fell back to a rule-based report, and the run escalated. It didn't crash."
- Show the Audit log tab with the `llm_call_failed` entries.

## 6. Quality and wrap-up (30s)
- Show `pytest`: 26 tests with a fake LLM, covering the retry loop, fallbacks and quota fail-fast.
- Show the README limitations section: no OCR, one extraction pass, free-tier quota. Then name the next step: LangGraph interrupts for human-in-the-loop resume.
- "Thanks, the repo link is in the email."
