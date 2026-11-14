"""Shared test setup.

Tests never touch the network or the real models/ folder:
- yfinance is replaced by a fake ticker with synthetic prices
- outgoing requests.get raises unless a test patches it
- the model folder points at a temp dir, so the real models/ is never touched
"""
import os
import tempfile

import numpy as np
import pandas as pd
import pytest

# Must run before main/agent_service are imported
import dotenv
dotenv.load_dotenv = lambda *args, **kwargs: False  # ignore any local backend/.env
for var in ("GROQ_API_KEY", "HF_API_KEY", "HF_TOKEN"):
    os.environ.pop(var, None)
os.environ["ADMIN_KEY"] = "test-admin-key"

import ml_engine
ml_engine.MODEL_DIR = tempfile.mkdtemp(prefix="tradewise-models-")


def synthetic_prices(rows: int = 500, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.015, rows)))
    index = pd.date_range("2024-01-01", periods=rows, freq="B", tz="Asia/Kolkata")
    return pd.DataFrame(
        {
            "Open": close * 0.995,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": rng.integers(100_000, 1_000_000, rows),
        },
        index=index,
    )


class FakeTicker:
    """Stands in for yfinance.Ticker. Symbols starting with FOO have no data."""

    history_calls = 0

    def __init__(self, symbol):
        self.symbol = symbol

    def history(self, period="2y", **kwargs):
        FakeTicker.history_calls += 1
        if self.symbol.startswith("FOO"):
            return pd.DataFrame()
        return synthetic_prices()

    @property
    def info(self):
        return {"longName": "Test Co", "marketCap": 1_000, "trailingPE": None, "previousClose": 100.0}

    @property
    def actions(self):
        return pd.DataFrame()


import yfinance as yf
yf.Ticker = FakeTicker

import main  # noqa: E402
import agent_service  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    """Reset in-memory state, stub news, and block real HTTP for every test."""
    main._analysis_cache.clear()
    main._quote_cache.clear()
    main._chat_requests.clear()

    async def no_news(symbol, max_items=5):
        return {"news": [], "sentiment": main.neutral_sentiment()}

    monkeypatch.setattr(main, "fetch_stock_news", no_news)

    def blocked(*args, **kwargs):
        raise RuntimeError("Network access is blocked in tests")

    monkeypatch.setattr(main.requests, "get", blocked)


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.fixture(scope="session")
def trained_model():
    """Train the universal model once on synthetic data (written to the temp dir)."""
    main.train_universal_model_job()
    assert main.ml_engine.xgb_model is not None
    return main.ml_engine


@pytest.fixture
def untrained_model(monkeypatch):
    class NoModel:
        xgb_model = None

        def predict(self, *args, **kwargs):
            return None

    monkeypatch.setattr(main, "ml_engine", NoModel())


@pytest.fixture
def admin_headers():
    return {"X-Admin-Key": "test-admin-key"}
