from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AnalyzeRequest(BaseModel):
    diff_text: str = Field(min_length=1, max_length=1_000_000)
    repository_path: str | None = None
    source_mode: Literal["sample", "local"] = "sample"


class Evidence(BaseModel):
    id: str
    kind: str
    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    symbol: str | None = None
    description: str
    snippet: str | None = None


class Symbol(BaseModel):
    id: str
    name: str
    qualified_name: str
    type: Literal["function", "method", "class", "async_function"]
    file_path: str
    start_line: int
    end_line: int
    evidence_ids: list[str] = Field(default_factory=list)


class ChangedFile(BaseModel):
    path: str
    change_type: Literal["modified", "added", "deleted", "renamed"]
    lines_added: int
    lines_deleted: int
    related_symbols: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class Relationship(BaseModel):
    source: str
    target: str
    relationship: Literal["calls"] = "calls"
    evidence_ids: list[str] = Field(default_factory=list)


class Risk(BaseModel):
    id: str
    severity: Literal["low", "medium", "high"]
    title: str
    description: str
    related_symbols: list[str]
    evidence_ids: list[str]
    is_potential: bool = True


class Recommendation(BaseModel):
    id: str
    title: str
    reason: str
    related_symbols: list[str]
    evidence_ids: list[str]
    confidence: Literal["low", "medium", "high"]


class Verification(BaseModel):
    status: Literal["passed", "failed", "error"]
    passed: list[str] = Field(default_factory=list)
    failed: list[str] = Field(default_factory=list)
    duration_seconds: float
    summary: str


class VerifyRequest(BaseModel):
    """Empty by design: verification never accepts a command or target path."""
    model_config = ConfigDict(extra="forbid")


class ChangeSummary(BaseModel):
    files_changed: int
    lines_added: int
    lines_deleted: int
    symbols_changed: int
    symbols_affected: int
    potential_risks: int
    test_recommendations: int


class AnalysisReport(BaseModel):
    schema_version: str = "1.0"
    session_id: str
    change_summary: ChangeSummary
    files: list[ChangedFile]
    changed_symbols: list[Symbol]
    affected_symbols: list[Symbol]
    relationships: list[Relationship]
    evidence: list[Evidence]
    risks: list[Risk]
    test_recommendations: list[Recommendation]
    verification: Verification | None = None
    limitations: list[str]
    explanations: list[str]
