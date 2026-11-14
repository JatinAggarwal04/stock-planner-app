"""API tests through FastAPI's TestClient, using synthetic market data."""
import os

import pytest

import main
import ml_engine
from tests.conftest import FakeTicker


def test_root(client):
    assert client.get("/").json()["service"].startswith("TradeWise")


def test_analyze_while_model_is_training(client, untrained_model):
    response = client.get("/analyze/TEST.NS")
    assert response.status_code == 200
    data = response.json()
    assert data["ml_analysis"]["model_accuracy"] == "Model training"
    assert data["recommendation"]["views"]["short_term"]["indicators"]["ml_score"] == 50.0


def test_analyze_with_trained_model(client, trained_model):
    model_path = os.path.join(ml_engine.MODEL_DIR, ml_engine.UNIVERSAL_MODEL_FILENAME)
    modified = os.path.getmtime(model_path)

    response = client.get("/analyze/TEST")
    assert response.status_code == 200
    data = response.json()

    assert data["symbol"] == "TEST.NS"
    assert data["ml_analysis"]["model_accuracy"] == "Universal Model"
    assert data["recommendation"]["signal"] in ("BUY", "SELL", "HOLD")
    assert data["recommendation"]["risk_rating"] in ("Low", "Medium", "High")
    assert data["market_data"]["pe_ratio"] is None
    expected_swing = {"BUY": "LONG", "SELL": "SHORT", "HOLD": "WAIT"}[data["recommendation"]["signal"]]
    assert data["trading_plan"]["swing"]["recommendation"] == expected_swing
    # Serving a request must not retrain or rewrite the model
    assert os.path.getmtime(model_path) == modified


def test_personalized_does_not_leak_into_shared_cache(client):
    response = client.get("/analyze/TEST.NS/personalized", params={"buy_price": 100, "quantity": 10})
    assert response.status_code == 200
    assert response.json()["personalized_recommendation"]["position_summary"]["quantity"] == 10

    assert "personalized_recommendation" not in client.get("/analyze/TEST.NS").json()


@pytest.mark.parametrize(
    "path, params",
    [
        ("/analyze/TEST.NS/personalized", {"buy_price": 0, "quantity": 10}),
        ("/analyze/TEST.NS/personalized", {"buy_price": 10, "quantity": 0}),
        ("/analyze/TEST.NS/personalized", {"buy_price": 10, "quantity": -1}),
        ("/analyze/TEST.NS", {"account_size": "nan"}),
        ("/analyze/TEST.NS", {"account_size": -5}),
        ("/analyze/TEST.NS", {"risk_per_trade": 101}),
    ],
)
def test_invalid_inputs_are_rejected(client, path, params):
    assert client.get(path, params=params).status_code == 422


@pytest.mark.parametrize("path", ["/analyze/FOO.NS", "/quote/FOO.NS"])
def test_unknown_symbol_is_404(client, path):
    response = client.get(path)
    assert response.status_code == 404


def test_quote_is_cached(client):
    before = FakeTicker.history_calls
    first = client.get("/quote/TEST.NS")
    second = client.get("/quote/TEST.NS")
    assert first.status_code == 200 and first.json() == second.json()
    assert FakeTicker.history_calls - before == 1


def test_history(client):
    response = client.get("/history/TEST.NS", params={"period": "1M"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) > 0 and data["meta"]["symbol"] == "TEST.NS"


def test_search_filters_to_indian_exchanges(client, monkeypatch):
    class Response:
        def json(self):
            return {"quotes": [
                {"symbol": "TCS.NS", "shortname": "TCS"},
                {"symbol": "TCS.BO", "longname": "Tata Consultancy"},
                {"symbol": "AAPL", "shortname": "Apple"},
            ]}

    seen = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        seen["timeout"] = timeout
        return Response()

    monkeypatch.setattr(main.requests, "get", fake_get)
    results = client.get("/search", params={"query": "tcs"}).json()
    assert [r["symbol"] for r in results] == ["TCS.NS", "TCS.BO"]
    assert seen["timeout"] == 10


def test_search_failure_returns_empty_list(client):
    assert client.get("/search", params={"query": "tcs"}).json() == []


def test_errors_do_not_expose_internals(client, monkeypatch):
    def broken(*args, **kwargs):
        raise ValueError("secret internal detail")

    monkeypatch.setattr(main, "_build_analysis", broken)
    response = client.get("/analyze/TEST.NS")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}


# ---------- admin ----------

@pytest.mark.parametrize("headers", [{}, {"X-Admin-Key": "wrong"}])
def test_admin_requires_key(client, headers):
    assert client.post("/admin/train-universal", headers=headers).status_code == 403
    assert client.post("/admin/push-model", params={"repo_id": "a/b"}, headers=headers).status_code == 403


def test_admin_non_ascii_key_is_403(client):
    response = client.post("/admin/train-universal", headers=[(b"X-Admin-Key", "caf\xe9".encode("latin-1"))])
    assert response.status_code == 403


def test_admin_rejects_concurrent_training(client, admin_headers):
    main._training_lock.acquire()
    try:
        assert client.post("/admin/train-universal", headers=admin_headers).status_code == 409
    finally:
        main._training_lock.release()


@pytest.mark.parametrize("has_model, expected_runs", [(False, 3), (True, 2)])
def test_model_scheduler_trains_on_start_and_weekly(monkeypatch, has_model, expected_runs):
    runs, sleeps = [], []

    class Engine:
        xgb_model = object() if has_model else None

    def fake_sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) > 2:
            raise StopIteration  # end the infinite loop after two weekly cycles

    monkeypatch.setattr(main, "ml_engine", Engine())
    monkeypatch.setattr(main, "train_universal_model_job", lambda: runs.append(1))
    monkeypatch.setattr(main.time, "sleep", fake_sleep)
    with pytest.raises(StopIteration):
        main._model_scheduler()
    assert len(runs) == expected_runs
    assert sleeps[0] == 7 * 24 * 3600


def test_push_model_needs_hf_token(client, admin_headers):
    response = client.post("/admin/push-model", params={"repo_id": "a/b"}, headers=admin_headers)
    assert response.status_code == 400


# ---------- chat ----------

def test_chat_is_rate_limited_per_ip(client, monkeypatch):
    async def fake_chat(message, context=None):
        return "ok"

    monkeypatch.setattr(main.agent, "chat", fake_chat)
    body = {"message": "hi"}
    codes = [client.post("/api/chat", json=body).status_code for _ in range(main.CHAT_RATE_LIMIT + 1)]
    assert codes[:-1] == [200] * main.CHAT_RATE_LIMIT and codes[-1] == 429
    other_ip = client.post("/api/chat", json=body, headers={"X-Forwarded-For": "203.0.113.9"})
    assert other_ip.status_code == 200


@pytest.mark.parametrize("message", ["", "x" * 2001])
def test_chat_message_length_is_validated(client, message):
    assert client.post("/api/chat", json={"message": message}).status_code == 422


def test_chat_without_groq_key_reports_unavailable(client):
    response = client.post("/api/chat", json={"user_id": "u1", "message": "hi"})
    assert response.status_code == 200
    assert "unavailable" in response.json()["response"]
