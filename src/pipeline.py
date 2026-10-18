"""One function used by both the CLI and the Streamlit UI."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

from src.graph import build_graph
from src.report import build_report, render_markdown
from src.state import PipelineState

StepCallback = Callable[[str, dict], None]


def run_pipeline(
    deal_path: str | Path,
    rules_path: str | Path,
    out_dir: str | Path | None = "outputs",
    on_step: Optional[StepCallback] = None,
) -> tuple[dict, dict]:
    """Run the full review. Returns (report_dict, final_state).

    on_step(node_name, update) is called after each agent finishes, which lets the UI
    show live progress. If out_dir is given, writes <out_dir>/<deal name>/report.json,
    report.md and audit_log.json.
    """
    initial: PipelineState = {
        "deal_path": str(deal_path), "rules_path": str(rules_path),
        "status": "running", "errors": [], "audit_log": [], "extraction_attempts": 0,
    }
    state: dict = dict(initial)
    for mode, chunk in build_graph().stream(initial, stream_mode=["updates", "values"]):
        if mode == "values":
            state = chunk
        elif on_step is not None:
            for node, update in chunk.items():
                on_step(node, update or {})

    report = build_report(state)

    if out_dir is not None:
        folder = Path(out_dir) / Path(deal_path).stem
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        (folder / "report.md").write_text(render_markdown(report), encoding="utf-8")
        audit = [a.model_dump() for a in state.get("audit_log", [])]
        (folder / "audit_log.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
        report["output_dir"] = str(folder)
    return report, state
