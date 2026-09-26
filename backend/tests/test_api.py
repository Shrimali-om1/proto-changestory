from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)


def test_health_and_report_exports() -> None:
    assert client.get("/health").json() == {"status": "ok"}
    diff = (ROOT / "fixtures/diffs/calculation.diff").read_text()
    response = client.post("/api/v1/analyze", json={"diff_text": diff, "source_mode": "sample"})
    assert response.status_code == 200
    session_id = response.json()["session_id"]
    assert client.get(f"/api/v1/reports/{session_id}").status_code == 200
    markdown = client.get(f"/api/v1/reports/{session_id}/export.md")
    assert markdown.text.startswith("# ChangeStory Report")
    assert "attachment; filename=" in markdown.headers["content-disposition"]


def test_controlled_verification_rejects_user_commands() -> None:
    # The API offers no command or cwd fields; verification is tied to a saved report.
    diff = (ROOT / "fixtures/diffs/calculation.diff").read_text()
    session_id = client.post("/api/v1/analyze", json={"diff_text": diff, "source_mode": "sample"}).json()["session_id"]
    response = client.post(f"/api/v1/reports/{session_id}/verify", json={"command": "whoami && echo unsafe"})
    assert response.status_code == 422
    safe_response = client.post(f"/api/v1/reports/{session_id}/verify")
    assert safe_response.status_code == 200
    assert safe_response.json()["verification"]["status"] in {"passed", "failed", "error"}
