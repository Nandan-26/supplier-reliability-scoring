"""Isolated, labelled assessment fixtures for the five Round 2 edge cases.

These records are intentionally invalid and never inserted into clean operational tables.
Ground-truth labels live beside the fixtures, not in scoring feature tables.
"""
from __future__ import annotations

from datetime import date


def validate_edge_case(case: dict) -> list[str]:
    case_id = case.get("edge_case_id")
    payload = case.get("payload", {})
    errors: list[str] = []

    if case_id == "EC-01":
        if not payload.get("po_id") or not payload.get("po_line_id"):
            errors.append("Shipment is missing its PO or PO-line reference.")
        elif payload.get("po_exists") is not True or payload.get("po_line_exists") is not True:
            errors.append("Shipment references a PO/PO line that does not exist.")
    elif case_id == "EC-02":
        dispatch = payload.get("dispatch_date")
        delivery = payload.get("actual_delivery_date")
        if not dispatch or not delivery:
            errors.append("Dispatch and actual delivery dates are required.")
        elif date.fromisoformat(delivery) < date.fromisoformat(dispatch):
            errors.append("Actual delivery date precedes shipment dispatch date.")
    elif case_id == "EC-03":
        cutoff = payload.get("as_of_date")
        event_date = payload.get("contributing_event_date")
        available = payload.get("system_available_at")
        if not cutoff or not event_date or not available:
            errors.append("As-of date, contributing event date and system availability date are required.")
        elif date.fromisoformat(event_date) > date.fromisoformat(cutoff) or date.fromisoformat(available) > date.fromisoformat(cutoff):
            errors.append("Score uses future or not-yet-available evidence beyond its as-of date.")
    elif case_id == "EC-04":
        if not payload.get("source") or not str(payload.get("source")).strip():
            errors.append("Risk signal source provenance is missing.")
        if not payload.get("signal_date"):
            errors.append("Risk signal timestamp/date is missing.")
    elif case_id == "EC-05":
        supplier_id = payload.get("po_supplier_id")
        site_supplier_id = payload.get("site_supplier_id")
        if not supplier_id or not site_supplier_id:
            errors.append("PO supplier and site owner are required.")
        elif supplier_id != site_supplier_id:
            errors.append("PO supplier does not own the referenced site.")
    else:
        errors.append(f"Unknown edge_case_id: {case_id!r}.")

    return errors


def evaluate_edge_case_catalogue(cases: list[dict]) -> dict:
    results = []
    for case in cases:
        errors = validate_edge_case(case)
        expected = case.get("expected_result", "QUARANTINE")
        passed = bool(errors) if expected == "QUARANTINE" else not errors
        results.append({
            "edge_case_id": case.get("edge_case_id"),
            "expected_result": expected,
            "actual_result": "QUARANTINE" if errors else "ACCEPT",
            "detected_reasons": errors,
            "passed": passed,
        })
    return {
        "total": len(results),
        "passed": sum(1 for item in results if item["passed"]),
        "failed": sum(1 for item in results if not item["passed"]),
        "results": results,
        "overall_passed": len(results) > 0 and all(item["passed"] for item in results),
    }
