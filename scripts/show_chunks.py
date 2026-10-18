"""Print the chunks the ingestion agent produces for a document.

Usage:  python -m scripts.show_chunks samples/edge_case_loan.pdf
"""
import sys

from src.agents.ingestion import ingest

RULES = "rules/lending_policy.yaml"


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "samples/normal_loan.pdf"
    result = ingest(path, RULES)
    doc = result["document"]
    print(f"{doc.title}  |  {doc.page_count} pages  |  {doc.chunk_count} chunks  |  structured={doc.structured}\n")
    for c in result["chunks"]:
        print(f"[{c.chunk_id:>8}]  {c.section[:30]:<30}  {c.text[:80]}")


if __name__ == "__main__":
    main()
