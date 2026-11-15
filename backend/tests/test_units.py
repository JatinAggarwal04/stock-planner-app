"""Unit tests for the pure calculation helpers in main.py and ml_engine.py."""
import os

import numpy as np
import pandas as pd
import pytest

import main
import ml_engine
from tests.conftest import synthetic_prices


def test_convert_to_python_type_handles_numpy_and_non_finite():
    data = {
        "int": np.int64(3),
        "float": np.float32(1.5),
        "nan": float("nan"),
        "inf": np.float64("inf"),
        "array": np.array([1, 2]),
        "nested": [np.float64(2.0), (np.int8(1),)],
    }
    assert main.convert_to_python_type(data) == {
        "int": 3,
        "float": 1.5,
        "nan": None,
        "inf": None,
        "array": [1, 2],
        "nested": [2.0, [1]],
    }


def test_position_size_risks_the_requested_amount():
    result = main.RiskManager.calculate_position_size(100_000, 2, entry_price=100, stop_loss=95)
    assert result == {"shares": 400, "position_value": 40_000.0, "risk_amount": 2_000.0}


def test_position_size_with_zero_risk_per_share():
    result = main.RiskManager.calculate_position_size(100_000, 2, entry_price=100, stop_loss=100)
    assert result["shares"] == 0


@pytest.mark.parametrize("signal, below", [("BUY", True), ("SELL", False)])
def test_stop_levels_are_on_the_correct_side(signal, below):
    levels = main.RiskManager.calculate_stop_levels(100, atr=2, signal=signal)
    for value in levels.values():
        assert (value < 100) == below


def test_intraday_pivots_use_previous_candle():
    df = pd.DataFrame({"High": [110.0, 999.0], "Low": [90.0, 1.0], "Close": [100.0, 105.0]})
    plan = main.TradingPlanGenerator.calculate_intraday_levels(df)
    assert plan["cpr"]["pivot"] == 100.0
    assert plan["resistance"]["R1"] == 110.0
    assert plan["support"]["S1"] == 90.0
    assert plan["current_price"] == 105.0


def test_intraday_pivots_need_two_candles():
    df = pd.DataFrame({"High": [1.0], "Low": [1.0], "Close": [1.0]})
    assert "error" in main.TradingPlanGenerator.calculate_intraday_levels(df)


@pytest.mark.parametrize(
    "trend, recommendation, stop_below",
    [("Bullish", "LONG", True), ("Bearish", "SHORT", False), ("Neutral", "WAIT", True)],
)
def test_swing_targets_follow_trend(trend, recommendation, stop_below):
    df = synthetic_prices(30)
    df["ATR"] = 2.0
    plan = main.TradingPlanGenerator.calculate_swing_targets(df, 100.0, trend)
    assert plan["recommendation"] == recommendation
    assert (plan["stop_loss"] < 100) == stop_below


@pytest.mark.parametrize(
    "current, action",
    [(120, "BOOK_PARTIAL_PROFIT"), (110, "HOLD_TRAIL_SL"), (100, "HOLD"), (97, "MONITOR_CLOSELY"), (90, "EXIT_IMMEDIATELY")],
)
def test_personalized_action_by_profit(current, action):
    rec = main.PersonalizedRecommendation.analyze_user_position(
        current_price=current, buy_price=100, quantity=10, stop_loss=80,
        targets={"target_1": 130}, risk_metrics={}, trading_plan={"swing": {"atr": 2}},
    )
    assert rec["recommendation"]["action"] == action
    assert rec["position_summary"]["profit_loss"] == round((current - 100) * 10, 2)


def test_long_term_view_detects_uptrend():
    df = synthetic_prices(300)
    df["Close"] = np.linspace(100, 200, 300)
    df["High"] = df["Close"] * 1.01
    df["Low"] = df["Close"] * 0.99
    view = main.TechnicalAnalyzer.analyze_long_term_view(df)
    assert view["signal"] == "Bullish"
    assert view["indicators"]["is_golden_cross"] is True


def prices_from_path(path):
    """OHLCV frame whose closes follow `path`, with a 1% high/low band."""
    close = np.asarray(path, dtype=float)
    return pd.DataFrame({
        "Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close,
        "Volume": np.full(len(close), 100_000),
    })


def wave(*legs):
    """Piecewise-linear path through the given turning points, 20 bars per leg."""
    points = []
    for start, end in zip(legs, legs[1:]):
        points.extend(np.linspace(start, end, 20, endpoint=False))
    points.append(legs[-1])
    return points


def test_support_resistance_shape():
    levels = main.SupportResistanceAnalyzer.find_levels(synthetic_prices())
    assert levels["trend"] in ("Bullish", "Bearish", "Neutral")
    for value in levels["all_support_levels"]:
        assert value > 0


def test_resistance_found_from_older_highs():
    # Peaked at 160 months ago, now 135: the old code only looked at the last 50 days and returned None
    df = prices_from_path(wave(100, 160, 120, 150, 110, 140, 130, 135) + [135] * 60)
    levels = main.SupportResistanceAnalyzer.find_levels(df)
    assert levels["nearest_resistance"] is not None
    assert all(r > 135 for r in levels["all_resistance_levels"])
    assert all(s < 135 for s in levels["all_support_levels"])
    # Nearest first
    assert levels["all_resistance_levels"] == sorted(levels["all_resistance_levels"])
    assert levels["all_support_levels"] == sorted(levels["all_support_levels"], reverse=True)


def test_broken_resistance_becomes_support():
    # Topped at 120 twice, then broke out to 150: 120 is now support
    df = prices_from_path(wave(100, 120, 105, 120, 110, 150) + [150] * 10)
    levels = main.SupportResistanceAnalyzer.find_levels(df)
    assert any(abs(s - 121.2) < 3 for s in levels["all_support_levels"])  # 120 high + 1% band


def test_new_high_falls_back_to_52_week_high():
    # Straight uptrend: no swing high above the price, but today's intraday high is
    df = prices_from_path(np.linspace(100, 200, 260))
    levels = main.SupportResistanceAnalyzer.find_levels(df)
    assert levels["nearest_resistance"] == round(200 * 1.01, 2)
    assert levels["nearest_support"] is not None


def test_prepare_features_without_indicators_returns_empty():
    engine = ml_engine.MLEngine.__new__(ml_engine.MLEngine)
    X, y, cols = engine.prepare_features(synthetic_prices())
    assert X.empty and len(cols) == 15


def test_model_save_is_atomic_and_reloadable(trained_model, tmp_path, monkeypatch):
    monkeypatch.setattr(ml_engine, "MODEL_DIR", str(tmp_path))
    trained_model.save_model()
    assert os.listdir(tmp_path) == [ml_engine.UNIVERSAL_MODEL_FILENAME]

    reloaded = ml_engine.MLEngine()
    assert reloaded.xgb_model is not None


def test_long_term_levels_are_symmetric_ranges():
    plan = main.TradingPlanGenerator.calculate_long_term_targets(100.0, volatility_annual=30.0)
    ranges = plan["likely_ranges"]
    assert list(ranges) == ["1_month", "3_months", "6_months", "1_year"]
    for r in ranges.values():
        assert r["low"] < 100 < r["high"]
        assert abs(r["low"] * r["high"] - 100 ** 2) < 0.5  # symmetric in log terms: equally likely either side
    assert ranges["1_year"] == {"low": round(100 * np.exp(-0.3), 2), "high": round(100 * np.exp(0.3), 2)}
    widths = [r["high"] - r["low"] for r in ranges.values()]
    assert widths == sorted(widths)  # longer horizon, wider range
    assert "not price targets" in plan["note"]
    assert "statistical_targets" not in plan
