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
from scipy.stats import spearmanr
from sklearn.linear_model import LinearRegression
from xgboost import XGBRegressor

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


# ---------- A: forecast next-10-day volatility ----------

RISK_HORIZON = 10
RISK_FEATURES = ["log_vol_5", "log_vol_20", "log_vol_60", "log_atr_pct", "log_range", "BB_Width",
                 "Volume_Ratio", "abs_ret_1", "log_vix", "log_mkt_vol_20"]


def add_risk_columns(df, nifty, vix):
    returns = np.log(df["Close"]).diff()
    nifty_returns = np.log(nifty["Close"].reindex(df.index).ffill()).diff()
    df["log_vol_5"] = np.log(returns.rolling(5).std())
    df["log_vol_20"] = np.log(returns.rolling(20).std())
    df["log_vol_60"] = np.log(returns.rolling(60).std())
    df["log_atr_pct"] = np.log(df["ATR"] / df["Close"])
    df["log_range"] = np.log((df["High"] - df["Low"]) / df["Close"])
    df["abs_ret_1"] = returns.abs()
    df["log_vix"] = np.log(vix["Close"].reindex(df.index).ffill())
    df["log_mkt_vol_20"] = np.log(nifty_returns.rolling(20).std())
    # Target: std of the next 10 daily log returns (needs all 10 days)
    future = pd.concat([returns.shift(-k) for k in range(1, RISK_HORIZON + 1)], axis=1)
    df["log_future_vol"] = np.log(future.std(axis=1).where(future.notna().all(axis=1)))
    return df


def risk_suite(data, n_folds=12, test_days=252):
    """Walk-forward MAE of log volatility (≈ relative error): model vs calibrated simple baselines."""
    cols = RISK_FEATURES + ["log_future_vol"]
    frame = data[cols].replace([np.inf, -np.inf], np.nan).dropna()
    dates = pd.Series(frame.index, index=frame.index)
    unique_dates = np.sort(dates.unique())
    errors = {"past 20d vol": [], "ATR %": [], "model": []}
    fold_wins = 0
    for fold in np.array_split(unique_dates[-test_days:], n_folds):
        start = np.searchsorted(unique_dates, fold[0])
        train = frame[(dates < unique_dates[start - RISK_HORIZON]).values]
        test = frame[dates.isin(fold).values]
        y_train, y_test = train["log_future_vol"], test["log_future_vol"]
        fold_errors = {}
        # Baselines are calibrated (linear fit) on the same training data, so the comparison is fair
        for name, col in (("past 20d vol", "log_vol_20"), ("ATR %", "log_atr_pct")):
            fit = LinearRegression().fit(train[[col]], y_train)
            fold_errors[name] = np.abs(fit.predict(test[[col]]) - y_test).mean()
        model = XGBRegressor(n_estimators=300, learning_rate=0.03, max_depth=4, subsample=0.8,
                             colsample_bytree=0.8, random_state=42)
        model.fit(train[RISK_FEATURES], y_train)
        fold_errors["model"] = np.abs(model.predict(test[RISK_FEATURES]) - y_test).mean()
        for name, err in fold_errors.items():
            errors[name].append(err)
        fold_wins += fold_errors["model"] < min(fold_errors["past 20d vol"], fold_errors["ATR %"])

    mae = {name: float(np.mean(v)) for name, v in errors.items()}
    best_baseline = min(mae["past 20d vol"], mae["ATR %"])
    print("\n### A: next-10-day volatility forecast (MAE of log vol, lower is better)")
    for name, value in mae.items():
        print(f"- {name}: {value:.4f}")
    print(f"- model improvement vs best baseline: {(1 - mae['model'] / best_baseline) * 100:.1f}%")
    print(f"- months where the model beat both baselines: {fold_wins}/{n_folds}", flush=True)


# ---------- B: monthly cross-sectional factor ranking ----------

def factor_suite(frames, symbols, step=21):
    """Rank IC of momentum (12-1) and low volatility vs next-month return relative to the Nifty."""
    nifty = frames["^NSEI"]["Close"]
    closes = pd.DataFrame({s: frames[s]["Close"] for s in symbols if s in frames}).reindex(nifty.index).ffill()
    returns = closes.pct_change()
    factors = {
        "momentum 12-1": closes.shift(21) / closes.shift(252) - 1,
        "low volatility": -returns.rolling(60).std(),
    }
    factors["combined"] = sum(f.rank(axis=1) for f in factors.values())
    forward = closes.shift(-step) / closes - 1
    excess = forward.sub(nifty.shift(-step) / nifty - 1, axis=0)

    dates = closes.index[252::step]
    dates = dates[dates <= closes.index[-step - 1]]  # need a full month ahead
    print(f"\n### B: monthly factor ranking ({len(dates)} months, {closes.shape[1]} stocks; current constituents only)")
    for name, factor in factors.items():
        ics, spreads = [], []
        for d in dates:
            pair = pd.concat([factor.loc[d], excess.loc[d]], axis=1, keys=["factor", "excess"]).dropna()
            if len(pair) < 20:
                continue
            ics.append(spearmanr(pair["factor"], pair["excess"]).statistic)
            ranked = pair.sort_values("factor")
            fifth = len(ranked) // 5
            spreads.append(ranked["excess"].iloc[-fifth:].mean() - ranked["excess"].iloc[:fifth].mean())
        ics = np.array(ics)
        t_stat = ics.mean() / ics.std(ddof=1) * np.sqrt(len(ics))
        print(f"- {name}: mean IC {ics.mean():.3f}, t-stat {t_stat:.2f}, IC>0 in {(ics > 0).mean() * 100:.0f}% of months, "
              f"top-minus-bottom fifth {np.mean(spreads) * 100:.2f}%/month", flush=True)


def main():
    frames = download(NIFTY_50 + [s for s in TOP_NIFTY_STOCKS if s not in NIFTY_50])
    print(f"downloaded {len(frames)} series")
    data = build(frames, list(dict.fromkeys(NIFTY_50 + TOP_NIFTY_STOCKS)))
    current = data[data["Symbol"].isin(TOP_NIFTY_STOCKS)]

    nifty50 = data[data["Symbol"].isin(NIFTY_50)]
    risk_data = pd.concat(
        add_risk_columns(group.copy(), frames["^NSEI"], frames["^INDIAVIX"]) for _, group in nifty50.groupby("Symbol")
    )
    risk_suite(risk_data)
    factor_suite(frames, NIFTY_50)

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
