"""Exit plans and alerts for held positions (pure rules, hand-checkable numbers)."""
import pandas as pd
import pytest

from positions import portfolio_summary, review_position

DAYS = pd.bdate_range("2026-09-01", periods=30)


def closes(*values):
    """Flat at the first value, then the given path at the end."""
    path = [values[0]] * (len(DAYS) - len(values)) + list(values)
    return pd.Series(path, index=DAYS, dtype=float)


def test_long_within_plan():
    # Avg 100, ATR 2: ATR stop 96 is tighter than the 7% stop (93)
    r = review_position("X", 10, 100.0, closes(100.0, 101.0), atr=2.0)
    plan = r["exit_plan"]
    assert plan["initial_stop"] == 96.0 and plan["trailing_stop"] is None and plan["stop"] == 96.0
    assert plan["risk_to_stop"] == (101 - 96) * 10
    assert r["pnl"] == 10.0 and r["plan_action"] == "HOLD" and r["alerts"] == []


def test_seven_percent_rule_caps_a_wide_atr_stop():
    r = review_position("X", 10, 100.0, closes(100.0), atr=5.0)  # ATR stop would be 90
    assert r["exit_plan"]["stop"] == 93.0


def test_trailing_stop_locks_in_profit_and_never_loosens():
    # Ran to 120 since entry, now 115; ATR 2 -> trail at 120 - 4 = 116, above entry
    since = DAYS[10]
    r = review_position("X", 10, 100.0, closes(100.0, 120.0, 115.0), atr=2.0, since=since)
    plan = r["exit_plan"]
    assert plan["trailing_stop"] == 116.0 and plan["stop"] == 116.0 and plan["stop_type"] == "trailing"
    assert plan["locked_in_profit"] == 160.0
    assert r["plan_action"] == "EXIT"  # 115 is already below the 116 trailing stop
    assert r["alerts"][0]["type"] == "STOP_HIT"


def test_no_trailing_until_one_atr_in_profit():
    r = review_position("X", 10, 100.0, closes(100.0, 101.5), atr=2.0)
    assert r["exit_plan"]["trailing_stop"] is None


def test_near_stop_needs_review():
    r = review_position("X", 10, 100.0, closes(100.0, 97.0), atr=2.0)  # 1 above the 96 stop, ATR 2
    assert [a["type"] for a in r["alerts"]] == ["NEAR_STOP"]
    assert r["plan_action"] == "REVIEW"


def test_loss_beyond_seven_percent_exits():
    r = review_position("X", 10, 100.0, closes(100.0, 92.0), atr=5.0)
    assert {"STOP_HIT", "LOSS_OVER_7_PCT"} <= {a["type"] for a in r["alerts"]}
    assert r["plan_action"] == "EXIT" and r["exit_plan"]["risk_to_stop"] == 0


def test_short_is_mirrored():
    r = review_position("X", -10, 100.0, closes(100.0, 99.0), atr=2.0)
    plan = r["exit_plan"]
    assert r["side"] == "SHORT" and r["quantity"] == 10
    assert plan["stop"] == 104.0 and plan["risk_to_stop"] == (104 - 99) * 10
    assert r["pnl"] == 10.0 and r["plan_action"] == "HOLD"


def test_results_alerts():
    drift = {"group": "strong_negative", "reaction_vs_nifty_pct": -4.2}
    r = review_position("X", 10, 100.0, closes(100.0, 105.0), atr=2.0, results_drift=drift,
                        next_results_date=pd.Timestamp("2026-10-15"), today=pd.Timestamp("2026-10-10"))
    types = [a["type"] for a in r["alerts"]]
    assert types == ["RESULTS_SOON", "RESULTS_REACTION_AGAINST"]
    assert r["plan_action"] == "REVIEW"
    # A strong negative reaction is good news for a short, so no alert there
    short = review_position("X", -10, 100.0, closes(100.0, 95.0), atr=2.0, results_drift=drift)
    assert short["alerts"] == []


def test_portfolio_totals_and_concentration():
    big = review_position("BIG", 30, 100.0, closes(100.0), atr=2.0)
    small = review_position("SMALL", 10, 100.0, closes(100.0), atr=2.0)
    summary = portfolio_summary([big, small])
    assert summary["market_value"] == 4000.0 and summary["risk_to_stops"] == 160.0
    assert summary["risk_to_stops_pct"] == 4.0
    assert big["weight_pct"] == 75.0 and big["alerts"][-1]["type"] == "CONCENTRATION"
    assert small["alerts"] == []


def test_single_position_is_not_flagged_as_concentrated():
    only = review_position("ONLY", 10, 100.0, closes(100.0), atr=2.0)
    portfolio_summary([only])
    assert only["alerts"] == []
