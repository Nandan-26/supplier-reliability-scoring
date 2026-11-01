import json
from pathlib import Path

from src.edge_cases import evaluate_edge_case_catalogue, validate_edge_case

FIXTURES = Path(__file__).resolve().parents[1] / "data" / "edge_case_fixtures.json"


def load_cases():
    return json.loads(FIXTURES.read_text(encoding="utf-8"))["fixtures"]


def test_all_five_labelled_edge_cases_are_detected():
    report = evaluate_edge_case_catalogue(load_cases())
    assert report["total"] == 5
    assert report["passed"] == 5
    assert report["failed"] == 0
    assert report["overall_passed"] is True
    assert {item["edge_case_id"] for item in report["results"]} == {
        "EC-01", "EC-02", "EC-03", "EC-04", "EC-05"
    }


def test_future_data_fixture_reports_both_temporal_dimensions():
    case = next(x for x in load_cases() if x["edge_case_id"] == "EC-03")
    reasons = validate_edge_case(case)
    assert reasons
    assert "future or not-yet-available" in reasons[0]


def test_missing_risk_source_and_timestamp_reports_both_fields():
    case = next(x for x in load_cases() if x["edge_case_id"] == "EC-04")
    reasons = validate_edge_case(case)
    assert len(reasons) == 2
    assert any("source provenance" in reason for reason in reasons)
    assert any("timestamp/date" in reason for reason in reasons)


def test_edge_case_ground_truth_is_separate_from_operational_features():
    artifact = json.loads(FIXTURES.read_text(encoding="utf-8"))
    assert artifact["ground_truth_separate_from_features"] is True
    assert all("edge_case_id" in case and "expected_result" in case for case in artifact["fixtures"])
