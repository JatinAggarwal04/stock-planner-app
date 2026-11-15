"""Compare model variants with the walk-forward backtest (needs network access to Yahoo Finance).

Run from backend/:  python scripts/experiment.py
Used by .github/workflows/experiment.yml; not part of the app.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import yfinance as yf

from main import FEATURE_COLS, FeatureEngine
from ml_engine import TOP_NIFTY_STOCKS, walk_forward_backtest

NIFTY_50 = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "BHARTIARTL", "ITC", "LT", "SBIN", "KOTAKBANK",
    "AXISBANK", "HINDUNILVR", "BAJFINANCE", "M&M", "MARUTI", "SUNPHARMA", "HCLTECH", "NTPC", "TITAN",
    "ULTRACEMCO", "ASIANPAINT", "POWERGRID", "TATASTEEL", "ADANIPORTS", "BAJAJFINSV", "ONGC", "COALINDIA",
    "NESTLEIND", "JSWSTEEL", "GRASIM", "WIPRO", "TECHM", "HINDALCO", "CIPLA", "DRREDDY", "BAJAJ-AUTO",
    "EICHERMOT", "HEROMOTOCO", "BRITANNIA", "APOLLOHOSP", "TATACONSUM", "SBILIFE", "HDFCLIFE", "INDUSINDBK",
    "ADANIENT", "SHRIRAMFIN", "BEL", "TRENT", "ETERNAL", "TMPV",
]
NIFTY_50 = [f"{s}.NS" for s in NIFTY_50]
MARKET_COLS = ["Mkt_Ret_5", "Mkt_Ret_20", "Mkt_Dist_SMA50", "Rel_Strength_20", "VIX", "VIX_Change_5"]


def download(symbols):
    data = yf.download(symbols + ["^NSEI", "^INDIAVIX"], period="5y", group_by="ticker",
                       auto_adjust=True, progress=False, threads=True)
    frames = {s: data[s].dropna(how="all") for s in symbols + ["^NSEI", "^INDIAVIX"] if s in data.columns.levels[0]}
    return frames


def add_market_features(df, nifty, vix):
    nifty_close = nifty["Close"].reindex(df.index).ffill()
    vix_close = vix["Close"].reindex(df.index).ffill()
    df["Mkt_Ret_5"] = nifty_close.pct_change(5)
    df["Mkt_Ret_20"] = nifty_close.pct_change(20)
    df["Mkt_Dist_SMA50"] = nifty_close / nifty_close.rolling(50).mean() - 1
    df["Rel_Strength_20"] = df["Close"].pct_change(20) - df["Mkt_Ret_20"]
    df["VIX"] = vix_close
    df["VIX_Change_5"] = vix_close.pct_change(5)
    return df


def add_targets(df, nifty):
    nifty_close = nifty["Close"].reindex(df.index).ffill()
    targets = {}
    fwd1 = df["Close"].pct_change(1).shift(-1)
    targets["next_day_up_0.2pct"] = (fwd1 > 0.002).astype(float).where(fwd1.notna())
    for h in (5, 10):
        excess = df["Close"].pct_change(h).shift(-h) - nifty_close.pct_change(h).shift(-h)
        targets[f"beats_nifty_{h}d"] = (excess > 0).astype(float).where(excess.notna())
    return targets


def build(frames, symbols):
    nifty, vix = frames["^NSEI"], frames["^INDIAVIX"]
    rows = []
    for symbol in symbols:
        if symbol not in frames or len(frames[symbol]) < 300:
            print(f"skip {symbol}: not enough data")
            continue
        df = FeatureEngine.calculate_technical_features(frames[symbol])
        df = FeatureEngine.calculate_alpha_features(df)
        df = add_market_features(df, nifty, vix)
        for name, target in add_targets(df, nifty).items():
            df[name] = target
        df["Symbol"] = symbol
        rows.append(df)
    return pd.concat(rows)


def run(data, features, target, horizon):
    subset = data[features + [target]].replace([np.inf, -np.inf], np.nan).dropna()
    start = time.time()
    report = walk_forward_backtest(subset[features], subset[target], subset.index, embargo_days=horizon)
    report["seconds"] = round(time.time() - start)
    return report


def main():
    frames = download(NIFTY_50 + [s for s in TOP_NIFTY_STOCKS if s not in NIFTY_50])
    print(f"downloaded {len(frames)} series")
    data = build(frames, list(dict.fromkeys(NIFTY_50 + TOP_NIFTY_STOCKS)))
    current = data[data["Symbol"].isin(TOP_NIFTY_STOCKS)]

    experiments = [
        ("current: 11 stocks, next day", current, FEATURE_COLS, "next_day_up_0.2pct", 1),
        ("Nifty 50, next day", data, FEATURE_COLS, "next_day_up_0.2pct", 1),
        ("Nifty 50, next day, + market", data, FEATURE_COLS + MARKET_COLS, "next_day_up_0.2pct", 1),
        ("Nifty 50, beats Nifty 5d", data, FEATURE_COLS, "beats_nifty_5d", 5),
        ("Nifty 50, beats Nifty 5d, + market", data, FEATURE_COLS + MARKET_COLS, "beats_nifty_5d", 5),
        ("Nifty 50, beats Nifty 10d", data, FEATURE_COLS, "beats_nifty_10d", 10),
        ("Nifty 50, beats Nifty 10d, + market", data, FEATURE_COLS + MARKET_COLS, "beats_nifty_10d", 10),
    ]
    print("\n| Variant | Preds | Accuracy | Baseline | AUC | Bullish calls (hit %) | Bearish calls (hit %) | s |")
    print("|---|---|---|---|---|---|---|---|")
    for name, frame, features, target, horizon in experiments:
        r = run(frame, features, target, horizon)
        print(f"| {name} | {r['test_predictions']} | {r['accuracy']} | {r['baseline_accuracy']} | {r['auc']} | "
              f"{r['bullish_calls']} ({r['bullish_hit_rate']}) | {r['bearish_calls']} ({r['bearish_hit_rate']}) | "
              f"{r['seconds']} |", flush=True)
        print(f"|   ↳ monthly AUCs: {r['fold_aucs']} | | | | | | | |", flush=True)


if __name__ == "__main__":
    main()
