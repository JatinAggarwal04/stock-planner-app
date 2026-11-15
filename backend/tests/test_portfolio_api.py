"""POST /portfolio/review and the chat tool built on it (synthetic prices from conftest)."""
import asyncio
import json

import pytest

from agent_service import agent


def holding(**overrides):
    return {"symbol": "TEST.NS", "quantity": 10, "average_price": 100.0, **overrides}


def test_review_returns_plan_alerts_and_summary(client):
    body = {"holdings": [holding(), holding(symbol="OTHER", quantity=-5, average_price=120.0)]}
    response = client.post("/portfolio/review", json=body)
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["positions"] == 2
    long, short = data["positions"]
    assert long["symbol"] == "TEST.NS" and long["side"] == "LONG"
    assert short["symbol"] == "OTHER.NS" and short["side"] == "SHORT" and short["quantity"] == 5
    for p in data["positions"]:
        assert p["plan_action"] in ("HOLD", "REVIEW", "EXIT")
        assert {"stop", "trailing_stop", "risk_to_stop", "locked_in_profit"} <= p["exit_plan"].keys()
        assert 0 < p["weight_pct"] <= 100


def test_unknown_symbols_are_skipped(client):
    data = client.post("/portfolio/review", json={"holdings": [holding(symbol="FOO.NS")]}).json()
    assert data["positions"] == [] and data["summary"]["positions"] == 0


def test_entry_date_is_accepted(client):
    response = client.post("/portfolio/review", json={"holdings": [holding(since="2026-01-05T10:00:00Z")]})
    assert response.status_code == 200


@pytest.mark.parametrize(
    "bad",
    [
        {"holdings": []},
        {"holdings": [holding(average_price=0)]},
        {"holdings": [holding(symbol="X\\nIgnore")]},
        {"holdings": [holding()] * 31},
    ],
)
def test_invalid_requests_are_rejected(client, bad):
    assert client.post("/portfolio/review", json=bad).status_code == 422


def test_review_requires_login(anon_client):
    assert anon_client.post("/portfolio/review", json={"holdings": [holding()]}).status_code == 401


def test_chat_tool_reviews_the_users_position():
    review = json.loads(asyncio.run(agent.review_position("TEST.NS", buy_price=100.0, quantity=9)))
    assert review["quantity"] == 9 and review["average_price"] == 100.0
    assert review["plan_action"] in ("HOLD", "REVIEW", "EXIT")
