"""Helpers shared by the LLM agents."""
from __future__ import annotations

import json

from src.state import Chunk, Evidence, ExtractedTerm


def format_chunks(chunks: list[Chunk]) -> str:
    """Render the document so the model sees the exact chunk IDs it must cite."""
    return "\n".join(f"[{c.chunk_id}] ({c.section}) {c.text}" for c in chunks)


def format_terms(terms: list[ExtractedTerm]) -> str:
    rows = []
    for t in terms:
        rows.append({
            "name": t.name, "value": t.value, "normalized": t.normalized, "unit": t.unit,
            "confidence": t.confidence, "verified": t.verified, "notes": t.notes,
            "evidence": [e.chunk_id for e in t.evidence],
        })
    return json.dumps(rows, indent=1)


def keep_valid_evidence(evidence: list[Evidence], chunk_ids: set[str]) -> tuple[list[Evidence], int]:
    """Drop citations to chunks that don't exist. Returns (kept, dropped_count)."""
    kept = [e for e in evidence if e.chunk_id in chunk_ids]
    return kept, len(evidence) - len(kept)


SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}
LIKELIHOOD_RANK = {"high": 3, "medium": 2, "low": 1}
