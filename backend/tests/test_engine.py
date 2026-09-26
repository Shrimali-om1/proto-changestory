from pathlib import Path

from app.services.engine import analyze


ROOT = Path(__file__).resolve().parents[2]


def test_calculation_scenario_detects_symbol_callers_and_tests() -> None:
    report = analyze((ROOT / "fixtures/diffs/calculation.diff").read_text(), ROOT / "sample-project")
    assert [symbol.name for symbol in report.changed_symbols] == ["calculate_total"]
    assert len(report.relationships) >= 2
    assert report.test_recommendations[0].confidence == "high"
    assert any(risk.title == "Potential shared-impact risk" for risk in report.risks)


def test_shared_utility_scenario_detects_consumers() -> None:
    report = analyze((ROOT / "fixtures/diffs/shared-utility.diff").read_text(), ROOT / "sample-project")
    assert report.change_summary.symbols_affected >= 2
    assert report.change_summary.potential_risks >= 1
