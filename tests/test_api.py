import pytest
from httpx import AsyncClient, ASGITransport
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.main import app

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")

@pytest.mark.asyncio
async def test_status_endpoint(client):
    r = await client.get("/api/status")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "online"
    assert "modules" in data
    assert "zinav" in data["modules"]
    assert "zihab" in data["modules"]
    assert "zipower" in data["modules"]

@pytest.mark.asyncio
async def test_hierarchy_endpoint(client):
    r = await client.get("/api/hierarchy")
    assert r.status_code == 200
    data = r.json()
    assert "zinav" in data
    assert data["zinav"]["subsystem"]["ziaxis"]["description"].startswith("Sistema estructural")

@pytest.mark.asyncio
async def test_gpd_calculation(client):
    r = await client.get("/api/gpd/calculate?altitude_km=400&velocity_kms=7.68&mass_kg=50000")
    assert r.status_code == 200
    data = r.json()
    assert "gradient" in data
    assert data["gradient"] < 0
    assert data["tidal_force_n"] != 0
    assert data["energy"]["distributed"] == True

@pytest.mark.asyncio
async def test_inference_endpoint(client):
    r = await client.post("/api/infer", json={
        "module": "zinav",
        "instruction": "check orbital status",
        "input_data": "alt_km=400"
    })
    assert r.status_code == 200
    data = r.json()
    assert "engine_a" in data
    assert "engine_b" in data
    assert "merged" in data
    assert data["engine_a"]["engine"] == "engine_a"
    assert data["engine_b"]["engine"] == "engine_b"

@pytest.mark.asyncio
async def test_inference_all_modules(client):
    for mod in ["zinav","zihab","zipower","ziship","zidrone","zirobot","zicomm","zieco"]:
        r = await client.post("/api/infer", json={
            "module": mod,
            "instruction": f"check {mod} status",
            "input_data": "status=nominal"
        })
        assert r.status_code == 200, f"Module {mod} failed"

@pytest.mark.asyncio
async def test_zty_templates(client):
    r = await client.get("/api/zty/templates")
    assert r.status_code == 200
    data = r.json()
    assert "templates" in data
    assert "blackvanta" in data["templates"]

@pytest.mark.asyncio
async def test_zty_report(client):
    r = await client.get("/api/zty/report/blackvanta")
    assert r.status_code == 200
    data = r.json()
    assert "total_mass_kg" in data
    assert data["total_mass_kg"] > 0
    assert data["delta_v_m_s"] > 0

@pytest.mark.asyncio
async def test_zty_report_not_found(client):
    r = await client.get("/api/zty/report/nonexistent")
    assert r.status_code == 404

@pytest.mark.asyncio
async def test_module_telemetry_update(client):
    r = await client.post("/api/telemetry/zinav", json={"alt_km": 500, "vel_kms": 8.0})
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    r2 = await client.get("/api/status")
    assert r2.json()["modules"]["zinav"]["alt_km"] == 500

@pytest.mark.asyncio
async def test_module_telemetry_update_all(client):
    for mod in ["zihab","zinav","zipower","ziship","zidrone","zirobot","zicomm","zieco","zimed","zicorex","zilink","zivr","zisec","zicriogen","zimaury"]:
        r = await client.post(f"/api/telemetry/{mod}", json={"status": "test"})
        assert r.status_code == 200
