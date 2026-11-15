"""Track record of the app's BUY/HOLD/SELL signal (trend component, sentiment neutral).

Run from backend/:  python scripts/signal_backtest.py   (needs network access to Yahoo Finance)
Experiment only; the numbers it prints are copied into main.py as the signal's track record.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import spearmanr

from main import FeatureEngine, TechnicalAnalyzer
from experiment import NIFTY_50

HORIZONS = (20, 60)


def trend_probability(df):
    """Vectorised TechnicalAnalyzer.analyze_long_term_view: probability-like trend score per day."""
    close = df["Close"]
    sma200 = df["SMA_200"].fillna(close)
    sma50 = df["SMA_50"].fillna(close)
    adx = df["ADX"].fillna(0.0)
    bullish = close > sma200
    golden = sma50 > sma200
    confidence = pd.Series(60, index=df.index)
    confidence += np.where((bullish & golden) | (~bullish & ~golden), 20, 0)
    confidence += np.where(adx > 25, 10, np.where(adx < 20, -10, 0))
    confidence = confidence.clip(0, 100)
    return pd.Series(np.where(bullish, confidence, 100 - confidence), index=df.index)


def signal(trend_prob):
    """The app's final signal with no ML weight and neutral sentiment (50)."""
    score = (trend_prob * 0.3 + 50 * 0.2) / 0.5
    return pd.Series(np.where(score > 60, "BUY", np.where(score < 40, "SELL", "HOLD")), index=trend_prob.index)


def self_check(df, trend_prob, samples=40, seed=0):
    """The vectorised version must match the app's own code on sampled days."""
    rng = np.random.default_rng(seed)
    for k in rng.choice(np.arange(250, len(df)), size=min(samples, len(df) - 250), replace=False):
        view = TechnicalAnalyzer.analyze_long_term_view(df.iloc[: k + 1].copy())
        expected = view["confidence"] if view["signal"] == "Bullish" else 100 - view["confidence"]
        assert expected == trend_prob.iloc[k], (df.index[k], expected, trend_prob.iloc[k])


def main():
    data = yf.download(NIFTY_50 + ["^NSEI"], start="2015-01-01", group_by="ticker",
                       auto_adjust=True, progress=False, threads=True)
    nifty = data["^NSEI"]["Close"].dropna()
    rows = []
    checked = 0
    for symbol in NIFTY_50:
        if symbol not in data.columns.levels[0]:
            continue
        df = data[symbol].dropna(how="all")
        if len(df) < 400:
            continue
        df = FeatureEngine.calculate_technical_features(df)
        prob = trend_probability(df)
        if checked < 5:
            self_check(df, prob)
            checked += 1
        frame = pd.DataFrame({"trend_prob": prob, "signal": signal(prob)}, index=df.index)
        nifty_aligned = nifty.reindex(df.index).ffill()
        for h in HORIZONS:
            stock_fwd = df["Close"].shift(-h) / df["Close"] - 1
            frame[f"fwd_{h}d"] = stock_fwd
            frame[f"excess_{h}d"] = stock_fwd - (nifty_aligned.shift(-h) / nifty_aligned - 1)
        frame["symbol"] = symbol
        rows.append(frame.iloc[250:])  # skip the 200-day warm-up
    study = pd.concat(rows).dropna()
    print(f"self-check passed on {checked} stocks: vectorised signal matches TechnicalAnalyzer")
    print(f"\n### Signal track record: {len(study)} stock-days, {study['symbol'].nunique()} stocks, "
          f"{study.index.min().date()} to {study.index.max().date()}")
    print(f"share of days: " + ", ".join(f"{s} {p:.0f}%" for s, p in (study['signal'].value_counts(normalize=True) * 100).items()))
    for h in HORIZONS:
        print(f"\n{h} trading days ahead:")
        for name, g in study.groupby("signal"):
            print(f"- {name}: n={len(g)}, up {(g[f'fwd_{h}d'] > 0).mean() * 100:.1f}%, "
                  f"median {g[f'fwd_{h}d'].median() * 100:.2f}%, beat Nifty {(g[f'excess_{h}d'] > 0).mean() * 100:.1f}%, "
                  f"median vs Nifty {g[f'excess_{h}d'].median() * 100:.2f}%", flush=True)
        # Robustness: one IC per month (days within a month overlap heavily)
        monthly = study.groupby(study.index.to_period("M")).apply(
            lambda g: spearmanr(g["trend_prob"], g[f"excess_{h}d"]).statistic if g["trend_prob"].nunique() > 1 else np.nan
        ).dropna()
        t_stat = monthly.mean() / monthly.std(ddof=1) * np.sqrt(len(monthly))
        print(f"- trend score vs return over Nifty: monthly IC {monthly.mean():.3f}, t-stat {t_stat:.2f} "
              f"(overlapping windows inflate this; treat |t| < 3 as no evidence), IC>0 in {(monthly > 0).mean() * 100:.0f}% of months")


if __name__ == "__main__":
    main()
