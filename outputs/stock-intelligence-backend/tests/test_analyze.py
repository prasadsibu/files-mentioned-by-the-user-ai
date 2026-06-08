from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_analyze_voltamp_returns_buy_score_90() -> None:
    response = client.post("/analyze", json={"stock": "VOLTAMP"})

    assert response.status_code == 200
    assert response.json() == {"recommendation": "BUY", "score": 90}


def test_analyze_unknown_stock_returns_structured_error() -> None:
    response = client.post("/analyze", json={"stock": "UNKNOWN"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ANALYSIS_ERROR"
