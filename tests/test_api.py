from fastapi.testclient import TestClient

import api


client = TestClient(api.app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_research_endpoint_returns_memo(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "download_prices", lambda force=False: None)
    monkeypatch.setattr(api, "read_experiments", lambda: [])
    monkeypatch.setattr(api, "reset_store", lambda: None)
    monkeypatch.setattr(
        api,
        "run_research",
        lambda question, model=None: ("mock memo", str(tmp_path / "memo.md")),
    )

    response = client.post(
        "/research",
        json={"question": "Test a simple cross-sectional momentum hypothesis."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["memo"] == "mock memo"
    assert body["experiments_run"] == 0
