"""Generate docs/architecture.svg (one-page architecture diagram).

Run from the project root:  python -m scripts.make_diagram
PNG/PDF exports were rendered from the SVG with a headless browser.
"""
from html import escape
from pathlib import Path

W, H = 1600, 1010
out = []
add = out.append

C = {
    "code": ("#EEF2F7", "#5B6B82", "CODE"),
    "llm": ("#F1ECFB", "#7C5CC4", "GEMINI"),
    "hybrid": ("#E6F4EF", "#2F8F75", "HYBRID"),
}
INK, MUTED, RED, LINE = "#1F2430", "#5C6370", "#C0392B", "#3A4150"


def text(x, y, s, size=13, weight="normal", fill=INK, anchor="start", italic=False):
    style = ' font-style="italic"' if italic else ""
    add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{style}>{escape(s)}</text>')


def lines(x, y, rows, size=12.5, fill=INK, gap=17, weight="normal"):
    for i, r in enumerate(rows):
        text(x, y + i * gap, r, size, weight, fill)


def node(x, y, w, h, n, title, kind, desc, writes):
    fill, stroke, tag = C[kind]
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="1.8"/>')
    add(f'<circle cx="{x + 20}" cy="{y + 22}" r="11" fill="{stroke}"/>')
    text(x + 20, y + 26.5, str(n), 12, "bold", "#fff", "middle")
    text(x + 38, y + 27, title, 15, "bold")
    tw = 9 + 7.2 * len(tag)
    add(f'<rect x="{x + w - tw - 10}" y="{y + 12}" width="{tw}" height="19" rx="9.5" fill="{stroke}"/>')
    text(x + w - tw / 2 - 10, y + 25.5, tag, 10.5, "bold", "#fff", "middle")
    lines(x + 14, y + 52, desc)
    text(x + 14, y + h - 12, "writes: " + writes, 11.5, "normal", stroke, italic=True)


def arrow(x1, y1, x2, y2, color=LINE, dash=None, label=None, lx=None, ly=None, marker="arrow"):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.8"{d} marker-end="url(#{marker})"/>')
    if label:
        text(lx if lx is not None else (x1 + x2) / 2, ly if ly is not None else (y1 + y2) / 2 - 6, label, 11.5, "normal", color, "middle", italic=True)


add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Inter, Helvetica, Arial, sans-serif">')
add("""<defs>
<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#3A4150"/></marker>
<marker id="arrow-red" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#C0392B"/></marker>
<marker id="arrow-purple" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#7C5CC4"/></marker>
</defs>""")
add(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>')

# ---------------- title + legend
text(40, 52, "Multi-Agent Deal Review Pipeline: Architecture", 26, "bold")
text(40, 80, "Reviews a loan agreement against a compliance rule set and returns an evidence-backed report. LangGraph orchestration · Gemini · Pydantic contracts", 14, "normal", MUTED)
lx = 1150
for i, k in enumerate(["code", "llm", "hybrid"]):
    fill, stroke, tag = C[k]
    add(f'<rect x="{lx + i * 150}" y="38" width="16" height="16" rx="4" fill="{fill}" stroke="{stroke}" stroke-width="1.8"/>')
    text(lx + 22 + i * 150, 51, {"code": "Deterministic code", "llm": "Gemini LLM", "hybrid": "Hybrid"}[k], 12.5)
add(f'<line x1="{lx}" y1="76" x2="{lx + 34}" y2="76" stroke="{LINE}" stroke-width="1.8" marker-end="url(#arrow)"/>')
text(lx + 42, 80, "flow", 12.5)
add(f'<line x1="{lx + 90}" y1="76" x2="{lx + 124}" y2="76" stroke="#7C5CC4" stroke-width="1.8" stroke-dasharray="5 4" marker-end="url(#arrow-purple)"/>')
text(lx + 132, 80, "retry", 12.5)
add(f'<line x1="{lx + 180}" y1="76" x2="{lx + 214}" y2="76" stroke="{RED}" stroke-width="1.8" stroke-dasharray="5 4" marker-end="url(#arrow-red)"/>')
text(lx + 222, 80, "failure route", 12.5)

# ---------------- left column: inputs / outputs
text(40, 150, "INPUTS", 12, "bold", MUTED)
for y, t, s in [(162, "Deal document", "PDF · TXT · MD"), (238, "Compliance rule set", "YAML: rules + escalation policy")]:
    add(f'<rect x="40" y="{y}" width="210" height="62" rx="8" fill="#FFF8E6" stroke="#C99A2E" stroke-width="1.6"/>')
    text(54, y + 26, t, 14, "bold")
    text(54, y + 46, s, 12, "normal", MUTED)

text(40, 412, "OUTPUTS", 12, "bold", MUTED)
for y, t, s in [(424, "report.md · report.json", "terms · matrix · risks · summary"),
                (500, "audit_log.json", "every agent step + LLM attempt"),
                (576, "Streamlit UI · CLI", "both call run_pipeline()")]:
    add(f'<rect x="40" y="{y}" width="210" height="62" rx="8" fill="#EAF6EC" stroke="#3E8E50" stroke-width="1.6"/>')
    text(54, y + 26, t, 14, "bold")
    text(54, y + 46, s, 11.5, "normal", MUTED)

# ---------------- orchestrator frame
FX, FY, FW, FH = 290, 112, 1270, 548
add(f'<rect x="{FX}" y="{FY}" width="{FW}" height="{FH}" rx="14" fill="#FAFBFC" stroke="{LINE}" stroke-width="1.6" stroke-dasharray="7 5"/>')
text(FX + 20, FY + 30, "ORCHESTRATOR AGENT · LangGraph StateGraph", 14, "bold")
text(FX + 360, FY + 30, "manages shared state · routes tasks · enforces dependencies · retries · failure paths · audit log", 12.5, "normal", MUTED)

NW, NH = 270, 150
cols = [315, 625, 935, 1265]
R1, R2 = 205, 455
node(cols[0], R1, NW, NH, 1, "Ingestion", "code",
     ["Splits the document into clause chunks", "with stable IDs (p2:7.2 = page 2, cl. 7.2).", "Loads + validates the YAML rule set.", "Fallback IDs p1:b2 for unnumbered docs."],
     "document, chunks, ruleset")
node(cols[1], R1, NW, NH, 2, "Term Extraction", "llm",
     ["Extracts ~28 material terms: parties,", "amounts, dates, rates, covenants,", "collateral... each with chunk_id, verbatim", "quote and confidence. Flags conflicts."],
     "extraction")
node(cols[2], R1, NW, NH, 3, "Evidence Verifier", "code",
     ["Checks every quote really exists in", "the chunk it cites (normalized match).", "Hallucinated / unknown citations ->", "feedback + one re-extraction."],
     "verified flags, feedback")
node(cols[3], R1, NW, NH, 4, "Compliance Review", "hybrid",
     ["Thresholds + derived LTV / tenor in code.", "Judgment rules: Gemini, one batched call.", "Grounding guard: PASS without valid", "evidence -> NEEDS_REVIEW."],
     "compliance, derived_terms")
node(cols[3], R2, NW, NH, 5, "Risk & Summary", "llm",
     ["Prioritized risk register (financial,", "legal, operational, compliance), gaps,", "executive summary, follow-up actions.", "Fallback: rule-based report from FAILs."],
     "risk_report")
node(cols[2] - 155, R2, NW, NH, 6, "Human Escalation", "code",
     ["Applies the YAML escalation policy:", "high/critical FAILs, NEEDS_REVIEW,", "low-confidence or unverified terms,", "critical risks, agent errors."],
     "escalations")
node(cols[0], R2, NW, NH, 7, "Assemble Report", "code",
     ["Sets final status: completed /", "completed_with_errors / failed.", "Renders report.md + report.json,", "writes audit_log.json."],
     "status")

# row 1 flow
cy1 = R1 + NH / 2
arrow(250, 230, cols[0], cy1)
arrow(250, 268, cols[0], cy1 + 20)
for a, b in zip(cols[:3], cols[1:]):
    arrow(a + NW, cy1, b, cy1)
# retry loop verifier -> extraction (above row 1)
add(f'<path d="M {cols[2] + 110} {R1} C {cols[2] + 110} {R1 - 40}, {cols[1] + 160} {R1 - 40}, {cols[1] + 160} {R1 - 2}" fill="none" stroke="#7C5CC4" stroke-width="1.8" stroke-dasharray="5 4" marker-end="url(#arrow-purple)"/>')
text((cols[1] + cols[2] + 270) / 2, R1 - 44, "citation failures -> retry once with feedback", 11.5, "normal", "#7C5CC4", "middle", italic=True)
# row 1 -> row 2
arrow(cols[3] + NW / 2, R1 + NH, cols[3] + NW / 2, R2, label="compliance matrix", lx=cols[3] + NW / 2 + 62, ly=(R1 + NH + R2) / 2 + 4)
cy2 = R2 + NH / 2
arrow(cols[3], cy2, cols[2] - 155 + NW, cy2, label="RiskReport")
arrow(cols[2] - 155, cy2, cols[0] + NW, cy2, label="Escalation[]")
# out to outputs
arrow(cols[0], cy2, 250, 455)
arrow(cols[0], cy2 + 25, 250, 531)
# failure routes (ingestion / extraction fail -> escalation)
ex = cols[2] - 155
add(f'<path d="M {cols[0] + 135} {R1 + NH} L {cols[0] + 135} {R1 + NH + 55} L {ex + 70} {R1 + NH + 55} L {ex + 70} {R2 - 2}" fill="none" stroke="{RED}" stroke-width="1.8" stroke-dasharray="5 4" marker-end="url(#arrow-red)"/>')
add(f'<path d="M {cols[1] + 135} {R1 + NH} L {cols[1] + 135} {R1 + NH + 55}" fill="none" stroke="{RED}" stroke-width="1.8" stroke-dasharray="5 4"/>')
text(cols[0] + 145, R1 + NH + 74, "on failure -> skip to escalation (report still produced)", 11.5, "normal", RED, italic=True)


# ---------------- shared state band
SY = 690
add(f'<rect x="{FX}" y="{SY}" width="{FW}" height="118" rx="12" fill="#F4F6FA" stroke="#5B6B82" stroke-width="1.6"/>')
text(FX + 20, SY + 28, "SHARED WORKFLOW STATE · PipelineState", 14, "bold")
text(FX + 340, SY + 28, "every node reads it and returns only the keys it changes · all values are Pydantic models", 12.5, "normal", MUTED)
chips = [("inputs", "deal_path · rules_path"), ("ingestion", "document · chunks · ruleset"),
         ("extraction", "extraction · verification_feedback"), ("compliance", "compliance · derived_terms"),
         ("risk", "risk_report"), ("escalation", "escalations · status"), ("append-only", "errors[] · audit_log[]")]
x = FX + 20
for k, v in chips:
    w = max(len(v), len(k)) * 6.3 + 22
    add(f'<rect x="{x}" y="{SY + 44}" width="{w}" height="56" rx="8" fill="#FFFFFF" stroke="#B7C0CE" stroke-width="1.2"/>')
    text(x + 11, SY + 64, k, 11, "bold", MUTED)
    text(x + 11, SY + 86, v, 12.5)
    x += w + 8
for cx in (450, 1040, 1400):
    add(f'<line x1="{cx}" y1="{FY + FH}" x2="{cx}" y2="{SY}" stroke="#5B6B82" stroke-width="1.4" stroke-dasharray="2 4"/>')

# ---------------- bottom callouts
BY, BW = 836, 494
callouts = [
    ("Grounding & traceability", ["Every term, rule result and risk cites p<page>:<clause>.",
                                  "Quotes are re-checked against the source in code.",
                                  "Invalid citations dropped; unsupported PASS downgraded."]),
    ("Failure handling", ["LLM output validated by schema; retry ≤2 with error feedback.",
                          "429: backoff; daily quota: fail fast. Agent down -> fallback.",
                          "Run ends completed_with_errors, never crashes; report always written."]),
    ("Uncertainty & escalation", ["Missing, unverified or low-confidence input never yields PASS.",
                                  "Conflicts (two effective dates) lower confidence + escalate.",
                                  "Thresholds live in the YAML policy, not in code."]),
]
for i, (t, rows) in enumerate(callouts):
    x = 40 + i * (BW + 19)
    add(f'<rect x="{x}" y="{BY}" width="{BW}" height="140" rx="10" fill="#FFFFFF" stroke="#D0D5DD" stroke-width="1.4"/>')
    add(f'<rect x="{x}" y="{BY}" width="6" height="140" rx="3" fill="{["#3E8E50", RED, "#C99A2E"][i]}"/>')
    text(x + 22, BY + 30, t, 15, "bold")
    for j, r in enumerate(rows):
        text(x + 22, BY + 60 + j * 24, "• " + r, 12.8)

add("</svg>")
open(Path(__file__).resolve().parent.parent / "docs" / "architecture.svg", "w").write("\n".join(out))
print("ok")
