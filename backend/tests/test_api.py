import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.synthetic import write_sample  # noqa: E402


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    d = tmp_path_factory.mktemp("data")
    write_sample(d)
    return TestClient(create_app(Settings(data_dir=d)))


def test_health(client):
    assert client.get("/api/v1/health").json()["status"] == "ok"


def test_meta_flags_synthetic(client):
    body = client.get("/api/v1/meta").json()
    assert body["source"] == "synthetic" and body["forecast_resolution_min"] == 60


def test_decision_ok_and_out_of_window(client):
    r = client.get("/api/v1/decision/2026-01-15?cutoff=09:30")
    assert r.status_code == 200 and r.json()["summary"]["n_points"] == 24
    assert client.get("/api/v1/decision/2026-03-01").status_code == 404


def test_validation_errors(client):
    for url, field in [("/api/v1/metrics?cutoff=25:99", "cutoff"), ("/api/v1/metrics?alignment=bogus", "alignment"),
                       ("/api/v1/risk-buffer?confidence=1.5", "confidence")]:
        r = client.get(url)
        assert r.status_code == 422
        assert field in str(r.json()["detail"])  # fails for the right reason, not a missing dependency


@pytest.mark.parametrize("path", ["/metrics", "/metrics/by-hour", "/metrics/by-day", "/metrics/by-level",
                                  "/metrics/by-horizon", "/metrics/by-cutoff", "/risk-buffer", "/series"])
def test_endpoints_respond(client, path):
    assert client.get(f"/api/v1{path}").status_code == 200


def test_basis_calibrated_and_calibration_endpoint(client):
    raw = client.get("/api/v1/metrics?basis=raw").json()
    cal = client.get("/api/v1/metrics?basis=calibrated").json()
    assert raw["n"] == 744 and 0 < cal["n"] <= raw["n"]
    rep = client.get("/api/v1/calibration").json()
    assert {"slope", "intercept", "offset_pct", "raw", "calibrated"} <= set(rep)
    d = client.get("/api/v1/decision/2026-01-15?basis=calibrated").json()
    assert d["summary"]["basis"] == "calibrated"


def test_bad_basis_rejected(client):
    r = client.get("/api/v1/metrics?basis=magic")
    assert r.status_code == 422 and "basis" in str(r.json()["detail"])
