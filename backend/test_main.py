"""
Tests for the Backpack job-costing API.

Run:  pytest -v

Covers:
  * the pure cost-calculation function (unit tests)
  * the HTTP endpoints (integration tests via FastAPI TestClient)
"""

from fastapi.testclient import TestClient

from main import app, calculate_cost, JobIn, VehicleIn, PlantIn

client = TestClient(app)


# ---------------------------------------------------------------- unit tests
def test_labour_only():
    job = JobIn(reference="J1", operative_name="A", time_on_site_hours=2)
    b = calculate_cost(job)
    assert b.labour_cost == 57.00          # 2 * 28.50
    assert b.total_cost == 57.00


def test_full_breakdown():
    job = JobIn(
        reference="J2", operative_name="B", time_on_site_hours=4,
        materials_cost=120.0,
        vehicles=[VehicleIn(vehicle_type="Van", days_on_site=1)],
        plant=[PlantIn(plant_type="Generator", days_on_site=2)],
    )
    b = calculate_cost(job)
    assert b.labour_cost == 114.00         # 4 * 28.50
    assert b.vehicle_cost == 45.00         # Van 1 day
    assert b.plant_cost == 80.00           # Generator 40 * 2
    assert b.materials_cost == 120.00
    assert b.total_cost == 359.00          # sum


def test_unknown_item_costs_zero():
    job = JobIn(
        reference="J3", operative_name="C", time_on_site_hours=0,
        vehicles=[VehicleIn(vehicle_type="Hovercraft", days_on_site=1)],
    )
    b = calculate_cost(job)
    assert b.vehicle_cost == 0.0
    assert b.total_cost == 0.0


# --------------------------------------------------------- integration tests
def test_health_endpoint():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_and_fetch_job():
    payload = {
        "reference": "STREETLIGHT-042",
        "operative_name": "Jordan Smith",
        "description": "Repair streetlight on Melton Rd",
        "time_on_site_hours": 3,
        "materials_cost": 65.0,
        "vehicles": [{"vehicle_type": "Cherry Picker", "days_on_site": 1}],
        "plant": [{"plant_type": "Hand Tools (kit)", "days_on_site": 1}],
    }
    r = client.post("/jobs", json=payload)
    assert r.status_code == 200
    data = r.json()
    # 3*28.50 + 180 + 10 + 65 = 340.50
    assert data["breakdown"]["total_cost"] == 340.50

    job_id = data["id"]
    r2 = client.get(f"/jobs/{job_id}")
    assert r2.status_code == 200
    assert r2.json()["reference"] == "STREETLIGHT-042"


def test_get_missing_job_returns_404():
    r = client.get("/jobs/999999")
    assert r.status_code == 404
