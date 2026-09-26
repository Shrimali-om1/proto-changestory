from __future__ import annotations

import json
from pathlib import Path

from app.models import AnalysisReport


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPORTS_DIR = PROJECT_ROOT / "reports"


def _safe_id(session_id: str) -> str:
    if not session_id or any(char not in "0123456789abcdef" for char in session_id) or len(session_id) > 64:
        raise ValueError("Invalid session ID.")
    return session_id


def save_report(report: AnalysisReport) -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    (REPORTS_DIR / f"{_safe_id(report.session_id)}.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    (REPORTS_DIR / f"{report.session_id}.md").write_text(to_markdown(report), encoding="utf-8")


def load_report(session_id: str) -> AnalysisReport | None:
    path = REPORTS_DIR / f"{_safe_id(session_id)}.json"
    return AnalysisReport.model_validate_json(path.read_text(encoding="utf-8")) if path.is_file() else None


def to_markdown(report: AnalysisReport) -> str:
    summary = report.change_summary
    lines = ["# ChangeStory Report", "", f"Session: `{report.session_id}`", "", "## Change summary", "",
             f"- Files changed: {summary.files_changed}", f"- Lines added/deleted: {summary.lines_added}/{summary.lines_deleted}",
             f"- Symbols changed/affected: {summary.symbols_changed}/{summary.symbols_affected}", "", "## Changed files", ""]
    lines += [f"- `{file.path}` — {file.change_type}, +{file.lines_added}/-{file.lines_deleted}" for file in report.files] or ["- None"]
    lines += ["", "## Changed symbols", ""] + [f"- `{s.qualified_name}` ({s.type}) — {s.file_path}:{s.start_line}-{s.end_line}" for s in report.changed_symbols]
    lines += ["", "## Potential risks", ""] + [f"- **{r.severity.title()}** — {r.title}: {r.description}" for r in report.risks]
    lines += ["", "## Suggested tests", ""] + [f"- **{r.title}** — {r.reason}" for r in report.test_recommendations]
    lines += ["", "## Verification", "", report.verification.summary if report.verification else "No controlled verification has been run yet."]
    lines += ["", "## Limitations", ""] + [f"- {limitation}" for limitation in report.limitations]
    return "\n".join(lines) + "\n"
