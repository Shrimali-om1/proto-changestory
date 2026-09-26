from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.analysis.diff_parser import DiffParseError
from app.models import AnalyzeRequest, AnalysisReport, VerifyRequest
from app.services.engine import analyze
from app.services.reports import PROJECT_ROOT, load_report, save_report, to_markdown
from app.services.runner import run_controlled_tests


app = FastAPI(title="ChangeStory API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_methods=["*"], allow_headers=["*"])
SAMPLE_ROOT = PROJECT_ROOT / "sample-project"


def repository_for(request: AnalyzeRequest) -> Path:
    if request.source_mode == "sample":
        return SAMPLE_ROOT
    if not request.repository_path:
        raise HTTPException(422, "repository_path is required for local analysis.")
    root = Path(request.repository_path).resolve()
    if not root.is_dir():
        raise HTTPException(422, "The requested local repository path does not exist.")
    return root


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/analyze", response_model=AnalysisReport)
def analyze_change(request: AnalyzeRequest) -> AnalysisReport:
    try:
        report = analyze(request.diff_text, repository_for(request))
    except DiffParseError as error:
        raise HTTPException(422, str(error)) from error
    save_report(report)
    return report


@app.get("/api/v1/reports/{session_id}", response_model=AnalysisReport)
def get_report(session_id: str) -> AnalysisReport:
    try:
        report = load_report(session_id)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    if not report:
        raise HTTPException(404, "Report not found.")
    return report


@app.get("/api/v1/reports/{session_id}/export.json")
def export_json(session_id: str) -> Response:
    report = get_report(session_id)
    return Response(
        content=report.model_dump_json(indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="changestory-{session_id}.json"'},
    )


@app.get("/api/v1/reports/{session_id}/export.md")
def export_markdown(session_id: str) -> Response:
    return Response(
        content=to_markdown(get_report(session_id)),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="changestory-{session_id}.md"'},
    )


@app.post("/api/v1/reports/{session_id}/verify", response_model=AnalysisReport)
def verify(session_id: str, _: VerifyRequest | None = None) -> AnalysisReport:
    report = get_report(session_id)
    report.verification = run_controlled_tests()
    save_report(report)
    return report
