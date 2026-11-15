"""Post-results drift context."""
import numpy as np
import pandas as pd
import pytest

import main

DAYS = pd.bdate_range("2026-01-01", periods=120, tz="Asia/Kolkata")
HISTORY = {"strong_negative": {"beat_nifty_pct": 49}, "strong_positive": {"beat_nifty_pct": 58}}


@pytest.fixture(autouse=True)
def calibration(monkeypatch):
    monkeypatch.setattr(main, "REACTION_CUTOFFS", (-0.02, 0.02))
    monkeypatch.setattr(main, "RESULTS_DRIFT_HISTORY", HISTORY)


def prices(jump_at, jump):
    """Flat stock and Nifty, with the stock jumping `jump` on day `jump_at`."""
    close = pd.Series(100.0, index=DAYS)
    close.iloc[jump_at:] *= 1 + jump
    nifty = pd.Series(20000.0, index=DAYS)
    return close, nifty


def results_on(i):
    return DAYS[i].tz_convert("UTC")  # Yahoo dates come in their own time zone


def test_strong_positive_reaction():
    close, nifty = prices(100, 0.06)
    drift = main.results_drift(close, nifty, results_on(100))
    assert drift["group"] == "strong_positive"
    assert drift["reaction_vs_nifty_pct"] == 6.0
    assert drift["results_date"] == str(DAYS[100].date())
    assert drift["trading_days_since"] == 119 - 101
    assert drift["days_remaining"] == 60 - 18
    assert drift["since_reaction_vs_nifty_pct"] == 0.0
    assert drift["historical"] == HISTORY


@pytest.mark.parametrize("jump, group", [(-0.05, "strong_negative"), (0.01, "neutral")])
def test_groups(jump, group):
    close, nifty = prices(100, jump)
    assert main.results_drift(close, nifty, results_on(100))["group"] == group


def test_reaction_is_relative_to_the_nifty():
    close, nifty = prices(100, 0.06)
    nifty.iloc[100:] *= 1.06  # the whole market rose as much
    assert main.results_drift(close, nifty, results_on(100))["group"] == "neutral"


@pytest.mark.parametrize(
    "results_index, reason",
    [(119, "reaction window not complete"), (50, "older than 60 trading days")],
)
def test_no_context_outside_the_window(results_index, reason):
    close, nifty = prices(results_index, 0.06)
    assert main.results_drift(close, nifty, results_on(results_index)) is None, reason


def test_no_context_without_data(monkeypatch):
    close, nifty = prices(100, 0.06)
    assert main.results_drift(close, nifty, None) is None
    assert main.results_drift(close, None, results_on(100)) is None
    monkeypatch.setattr(main, "REACTION_CUTOFFS", (None, None))
    assert main.results_drift(close, nifty, results_on(100)) is None


def test_analysis_survives_missing_results_data(client):
    # The fake ticker has no earnings dates: the field is simply absent, nothing breaks
    data = client.get("/analyze/NORESULTS.NS").json()
    assert data["results_drift"] is None
