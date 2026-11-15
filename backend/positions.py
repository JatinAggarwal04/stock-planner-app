"""Exit plan and alerts for positions the user already holds.

These are risk-management rules (ATR stops, the 7% capital-protection rule, a trailing stop), not predictions:
the backtests found ATR to be the best available estimate of how far a stock normally moves.
"""
from typing import Dict, List, Optional

import pandas as pd

ATR_STOP_MULTIPLE = 2.0  # initial and trailing stop distance, in ATRs
TRAIL_AFTER_ATRS = 1.0  # start trailing once the position is this many ATRs in profit
CAPITAL_PROTECTION_PCT = 7.0  # never risk more than 7% of the entry price
NEAR_STOP_ATRS = 1.0
RESULTS_SOON_DAYS = 7
MAX_POSITION_WEIGHT_PCT = 25.0


def review_position(symbol: str, quantity: float, average_price: float, close: pd.Series, atr: float,
                    since: Optional[pd.Timestamp] = None, results_drift: Optional[Dict] = None,
                    next_results_date: Optional[pd.Timestamp] = None, today: Optional[pd.Timestamp] = None) -> Dict:
    """Stop, trailing stop, money at risk and alerts for one holding. Negative quantity means a short."""
    long = quantity > 0
    shares = abs(quantity)
    price = float(close.iloc[-1])
    side = 1 if long else -1

    # Initial stop: the tighter of 2 ATRs and the 7% capital-protection rule
    atr_stop = average_price - side * ATR_STOP_MULTIPLE * atr
    protection_stop = average_price * (1 - side * CAPITAL_PROTECTION_PCT / 100)
    initial_stop = max(atr_stop, protection_stop) if long else min(atr_stop, protection_stop)

    # Trailing stop from the best close since entry (falls back to the last month if the entry date is unknown)
    held = close[close.index >= since] if since is not None else close.tail(22)
    if held.empty:
        held = close.tail(1)
    best_close = float(held.max() if long else held.min())
    trailing_stop = None
    if side * (best_close - average_price) >= TRAIL_AFTER_ATRS * atr:
        trailing_stop = best_close - side * ATR_STOP_MULTIPLE * atr
    stop = initial_stop if trailing_stop is None else (
        max(initial_stop, trailing_stop) if long else min(initial_stop, trailing_stop))

    pnl = side * (price - average_price) * shares
    pnl_pct = side * (price - average_price) / average_price * 100
    distance_to_stop = side * (price - stop)  # positive while the stop hasn't been hit
    stop_hit = distance_to_stop <= 0

    alerts: List[Dict] = []
    if stop_hit:
        alerts.append({"type": "STOP_HIT", "level": "critical",
                       "message": f"Price has crossed your stop at ₹{stop:.2f}."})
    elif distance_to_stop < NEAR_STOP_ATRS * atr:
        alerts.append({"type": "NEAR_STOP", "level": "warning",
                       "message": f"Within one normal day's move (₹{atr:.2f}) of your stop at ₹{stop:.2f}."})
    if pnl_pct <= -CAPITAL_PROTECTION_PCT:
        alerts.append({"type": "LOSS_OVER_7_PCT", "level": "critical",
                       "message": f"Down {abs(pnl_pct):.1f}%: beyond the 7% capital-protection limit."})
    if next_results_date is not None and today is not None:
        days = (pd.Timestamp(next_results_date).normalize() - pd.Timestamp(today).normalize()).days
        if 0 <= days <= RESULTS_SOON_DAYS:
            alerts.append({"type": "RESULTS_SOON", "level": "info",
                           "message": f"Quarterly results expected in {days} day{'s' if days != 1 else ''}: expect a bigger move."})
    if results_drift:
        against = "strong_negative" if long else "strong_positive"
        if results_drift.get("group") == against:
            alerts.append({"type": "RESULTS_REACTION_AGAINST", "level": "warning",
                           "message": f"The market reacted {'badly' if long else 'well'} to the latest results "
                                      f"({results_drift['reaction_vs_nifty_pct']:+.1f}% vs Nifty), against your position."})

    types = {a["type"] for a in alerts}
    if types & {"STOP_HIT", "LOSS_OVER_7_PCT"}:
        action, reason = "EXIT", "Your exit rule has been triggered."
    elif types & {"NEAR_STOP", "RESULTS_REACTION_AGAINST"}:
        action, reason = "REVIEW", "Close to your exit rule; decide now whether you still want this position."
    else:
        action, reason = "HOLD", "Within your plan: the stop has not been approached."

    return {
        "symbol": symbol,
        "side": "LONG" if long else "SHORT",
        "quantity": shares,
        "average_price": round(average_price, 2),
        "current_price": round(price, 2),
        "invested": round(average_price * shares, 2),
        "market_value": round(price * shares, 2),
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 2),
        "atr": round(atr, 2),
        "exit_plan": {
            "initial_stop": round(initial_stop, 2),
            "trailing_stop": round(trailing_stop, 2) if trailing_stop is not None else None,
            "stop": round(stop, 2),
            "stop_type": "trailing" if stop == trailing_stop else "initial",
            # Money lost from here if the stop is hit, or profit already protected once the stop is past entry
            "risk_to_stop": round(max(distance_to_stop, 0) * shares, 2),
            "locked_in_profit": round(max(side * (stop - average_price), 0) * shares, 2),
        },
        "alerts": alerts,
        "plan_action": action,
        "plan_reason": reason,
    }


def portfolio_summary(reviews: List[Dict]) -> Dict:
    """Totals across holdings, plus concentration alerts added to the heaviest positions."""
    exposure = sum(r["market_value"] for r in reviews) or 1.0
    for r in reviews:
        r["weight_pct"] = round(r["market_value"] / exposure * 100, 1)
        if len(reviews) > 1 and r["weight_pct"] > MAX_POSITION_WEIGHT_PCT:
            r["alerts"].append({"type": "CONCENTRATION", "level": "warning",
                                "message": f"{r['weight_pct']:.0f}% of your portfolio is in this one stock."})
    total_risk = sum(r["exit_plan"]["risk_to_stop"] for r in reviews)
    # Positions already through their stop have no "risk to stop" left: their whole value is outside the plan
    past_stop = [r for r in reviews if any(a["type"] == "STOP_HIT" for a in r["alerts"])]
    return {
        "positions": len(reviews),
        "invested": round(sum(r["invested"] for r in reviews), 2),
        "market_value": round(sum(r["market_value"] for r in reviews), 2),
        "pnl": round(sum(r["pnl"] for r in reviews), 2),
        "risk_to_stops": round(total_risk, 2),
        "risk_to_stops_pct": round(total_risk / exposure * 100, 2),
        "locked_in_profit": round(sum(r["exit_plan"]["locked_in_profit"] for r in reviews), 2),
        "past_stop_value": round(sum(r["market_value"] for r in past_stop), 2),
        "past_stop_pct": round(sum(r["market_value"] for r in past_stop) / exposure * 100, 1),
        "needs_attention": sum(r["plan_action"] != "HOLD" for r in reviews),
    }
