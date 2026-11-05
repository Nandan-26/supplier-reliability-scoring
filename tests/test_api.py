import pytest
from fastapi.testclient import TestClient

from src import api
from src.generator import generate_synthetic_data
from src.scoring import calculate_supplier_scores


@pytest.fixture()
def client_with_database(tmp_path, monkeypatch):
    db_path = tmp_path / "api_test.db"
    generate_synthetic_data(
        db_path=db_path, num_suppliers=25, num_pos=100,
        num_shipments=150, num_inspections=200, seed=20261022,
    )
    calculate_supplier_scores(as_of_date="2026-12-31", db_path=db_path)
    monkeypatch.setenv("SUPPLIER_DB_PATH", str(db_path))
    with TestClient(api.app) as client:
        yield client


def test_health_returns_database_status(client_with_database):
    response = client_with_database.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "connected"


def test_summary_counts_all_scored_suppliers(client_with_database):
    response = client_with_database.get("/api/v1/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_suppliers"] == 25
    assert sum(payload["classification_counts"].values()) == 25


def test_supplier_list_supports_pagination(client_with_database):
    response = client_with_database.get("/api/v1/suppliers?limit=5")
    assert response.status_code == 200
    assert response.json()["total"] == 25
    assert len(response.json()["items"]) == 5


def test_supplier_list_rejects_unknown_classification(client_with_database):
    response = client_with_database.get("/api/v1/suppliers?classification=Unknown")
    assert response.status_code == 400


def test_supplier_detail_returns_score_and_decision(client_with_database):
    item = client_with_database.get("/api/v1/suppliers?limit=1").json()["items"][0]
    response = client_with_database.get(f"/api/v1/suppliers/{item['supplier_id']}")
    assert response.status_code == 200
    assert response.json()["supplier_id"] == item["supplier_id"]
    assert "delivery_score" in response.json()
    assert "classification" in response.json()


def test_missing_supplier_returns_404(client_with_database):
    assert client_with_database.get("/api/v1/suppliers/NOT-A-SUPPLIER").status_code == 404


def test_missing_database_returns_503(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPPLIER_DB_PATH", str(tmp_path / "missing.db"))
    with TestClient(api.app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 503
