"""Document Ingestion Agent (deterministic, no LLM).

Turns a deal PDF (or .txt/.md) into citable chunks with stable IDs like 'p2:7.2'
(page 2, clause 7.2), and loads + validates the compliance rule set.

Why no LLM here: chunk IDs are the backbone of traceability. They must be identical on
every run, so they come from code, not from a model.
"""
from __future__ import annotations

import re
from pathlib import Path

import pymupdf
import yaml
from pydantic import ValidationError

from src.state import AuditEntry, Chunk, DocumentInfo, PipelineState, RuleSet

# "7. Security and Collateral"  or  "SCHEDULE 1 Key Dates ..."
SECTION_RE = re.compile(r"^(?P<num>\d{1,2})\.\s+(?P<title>[A-Z\[].*)$")
SCHEDULE_RE = re.compile(r"^(?P<num>SCHEDULE\s+\d+)\s+(?P<title>.*)$", re.IGNORECASE)
# "7.2  An independent appraisal..."  or  "S1.1  Effective Date..."
CLAUSE_RE = re.compile(r"^(?P<num>(?:S\d+|\d{1,2})\.\d{1,2})\s+(?P<text>.+)$")
# Repeated page furniture we don't want inside chunks
NOISE_RE = re.compile(r"^(Page \d+|.*SYNTHETIC DOCUMENT.*)$", re.IGNORECASE)

MIN_TEXT_CHARS = 50  # below this, the PDF is probably scanned / image-only


class IngestionError(Exception):
    """Raised when the document or rule set can't be used at all."""


# ---------------------------------------------------------------- document

def _read_pages(path: Path) -> list[str]:
    if path.suffix.lower() in {".txt", ".md"}:
        return [path.read_text(encoding="utf-8")]
    if path.suffix.lower() != ".pdf":
        raise IngestionError(f"Unsupported file type: {path.suffix} (use .pdf, .txt or .md)")
    try:
        with pymupdf.open(path) as doc:
            return [page.get_text("text") for page in doc]
    except Exception as exc:  # corrupt / encrypted PDF
        raise IngestionError(f"Could not open PDF {path.name}: {exc}") from exc


def _section_key(clause_num: str) -> str:
    """'7.2' -> '7', 'S1.1' -> 'SCHEDULE 1'."""
    head = clause_num.split(".")[0]
    return f"SCHEDULE {head[1:]}" if head.startswith("S") else head


def chunk_document(pages: list[str]) -> tuple[list[Chunk], str, bool]:
    """Return (chunks, title, structured)."""
    lines: list[tuple[int, str]] = []
    for page_no, text in enumerate(pages, start=1):
        for raw in text.splitlines():
            line = raw.strip()
            if line and not NOISE_RE.match(line):
                lines.append((page_no, line))

    title = lines[0][1] if lines else "Untitled"
    chunks: list[Chunk] = []
    section_num, section_title = "", "Preamble"
    current: dict | None = None

    def flush():
        if current and current["text"].strip():
            chunks.append(Chunk(**current))

    for page_no, line in lines:
        if m := SCHEDULE_RE.match(line):
            flush(); current = None
            section_num, section_title = m["num"].upper(), f"{m['num'].upper()} {m['title']}"
            continue
        if m := SECTION_RE.match(line):
            flush(); current = None
            section_num, section_title = m["num"], f"{m['num']}. {m['title']}"
            continue
        m = CLAUSE_RE.match(line)
        # Only accept a clause number that belongs to the current section, so a wrapped
        # line starting with e.g. "2.75 per cent" isn't mistaken for clause 2.75.
        if m and _section_key(m["num"]) == section_num:
            flush()
            current = {
                "chunk_id": f"p{page_no}:{m['num']}",
                "page": page_no,
                "section": section_title,
                "clause": m["num"],
                "text": m["text"],
            }
        elif current is not None:
            current["text"] += " " + line  # continuation of the previous clause
        # lines before the first clause (title, agreement no.) are kept in the title only

    flush()

    if chunks:
        return chunks, title, True

    # Fallback for documents without numbered clauses: one chunk per paragraph block,
    # still traceable by page.
    fallback: list[Chunk] = []
    for page_no, text in enumerate(pages, start=1):
        for i, block in enumerate(p for p in re.split(r"\n\s*\n", text) if p.strip()):
            fallback.append(Chunk(
                chunk_id=f"p{page_no}:b{i + 1}", page=page_no, section=f"Page {page_no}",
                text=" ".join(block.split()),
            ))
    return fallback, title, False


# ---------------------------------------------------------------- rules

def load_rules(path: str | Path) -> RuleSet:
    path = Path(path)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        ruleset = RuleSet.model_validate(data)
    except FileNotFoundError as exc:
        raise IngestionError(f"Rule set not found: {path}") from exc
    except (yaml.YAMLError, ValidationError) as exc:
        raise IngestionError(f"Invalid rule set {path.name}: {exc}") from exc

    ids = [r.id for r in ruleset.rules]
    if len(ids) != len(set(ids)):
        raise IngestionError("Rule set contains duplicate rule IDs")
    for r in ruleset.rules:
        if r.check_type == "threshold" and (r.term is None or r.operator is None or r.value is None):
            raise IngestionError(f"Threshold rule {r.id} needs term, operator and value")
    return ruleset


# ---------------------------------------------------------------- agent entrypoint

def ingest(deal_path: str | Path, rules_path: str | Path) -> dict:
    """Pure function used by the orchestrator node and by tests."""
    deal_path, rules_path = Path(deal_path), Path(rules_path)
    if not deal_path.exists():
        raise IngestionError(f"Deal document not found: {deal_path}")

    pages = _read_pages(deal_path)
    if sum(len(p.strip()) for p in pages) < MIN_TEXT_CHARS:
        raise IngestionError(
            "Document has no extractable text (scanned/image PDF?). OCR is out of scope."
        )

    chunks, title, structured = chunk_document(pages)
    ruleset = load_rules(rules_path)

    info = DocumentInfo(
        path=str(deal_path), title=title, page_count=len(pages),
        chunk_count=len(chunks), structured=structured,
    )
    audit = [AuditEntry(
        agent="ingestion", event="completed",
        detail=f"{len(pages)} pages -> {len(chunks)} chunks (structured={structured}); "
               f"{len(ruleset.rules)} rules loaded from '{ruleset.policy_name}'",
    )]
    return {"document": info, "chunks": chunks, "ruleset": ruleset, "audit_log": audit}


def ingestion_node(state: PipelineState) -> dict:
    """LangGraph node wrapper: converts failures into state instead of crashing the graph."""
    try:
        return ingest(state["deal_path"], state["rules_path"])
    except IngestionError as exc:
        return {
            "status": "failed",
            "errors": [f"ingestion: {exc}"],
            "audit_log": [AuditEntry(agent="ingestion", event="failed", detail=str(exc))],
        }
