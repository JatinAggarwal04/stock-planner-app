"""Probe free event data (earnings, analyst actions) and test post-earnings drift.

Run from backend/:  python scripts/events.py   (needs network access to Yahoo Finance)
Experiment only; not part of the app.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import spearmanr

from experiment import NIFTY_50

HORIZONS = (20, 40, 60)


def probe(symbols):
    """What event data does Yahoo have for these stocks, and how far back?"""
    earnings, coverage = [], []
    for symbol in symbols:
        ticker = yf.Ticker(symbol)
        row = {"symbol": symbol}
        try:
            dates = ticker.get_earnings_dates(limit=60)
        except Exception as e:
            dates = None
            row["earnings_error"] = type(e).__name__
        if dates is not None and len(dates):
            reported = dates.dropna(subset=["Reported EPS"])
            row.update(quarters=len(reported), first=str(reported.index.min().date()) if len(reported) else None,
                       with_estimate=int(reported["EPS Estimate"].notna().sum()))
            frame = reported.reset_index().rename(columns={"Earnings Date": "date"})
            frame["symbol"] = symbol
            earnings.append(frame)
        for name, attr in (("upgrades", "upgrades_downgrades"), ("eps_revisions", "eps_revisions")):
            try:
                value = getattr(ticker, attr)
                row[name] = 0 if value is None else len(value)
                if name == "upgrades" and value is not None and len(value):
                    row["upgrades_first"] = str(pd.to_datetime(value.index).min().date())
            except Exception as e:
                row[name] = type(e).__name__
        coverage.append(row)
        time.sleep(0.5)
    coverage = pd.DataFrame(coverage)
    print("### Data coverage (per stock)")
    print(coverage.to_string(index=False))
    print(f"\nstocks with earnings history: {(coverage.get('quarters', pd.Series(dtype=float)).fillna(0) > 0).sum()}/{len(symbols)}")
    return pd.concat(earnings) if earnings else pd.DataFrame()


def event_study(events, symbols):
    data = yf.download(symbols + ["^NSEI"], start="2015-01-01", group_by="ticker",
                       auto_adjust=True, progress=False, threads=True)
    nifty = data["^NSEI"]["Close"].dropna()
    rows = []
    for _, event in events.iterrows():
        close = data[event["symbol"]]["Close"].dropna() if event["symbol"] in data.columns.levels[0] else None
        if close is None or close.empty:
            continue
        # Results are often published after the close: the reaction window spans the day before to the day after
        day = pd.Timestamp(event["date"]).tz_localize(None).normalize()
        i = close.index.searchsorted(day)
        if i < 1 or i + 2 + max(HORIZONS) >= len(close):
            continue
        def excess(a, b):
            d0, d1 = close.index[a], close.index[b]
            n0, n1 = nifty.asof(d0), nifty.asof(d1)
            return close.iloc[b] / close.iloc[a] - 1 - (n1 / n0 - 1)
        row = {"symbol": event["symbol"], "date": close.index[i], "year": close.index[i].year,
               "reaction": excess(i - 1, i + 1),
               "eps_surprise": event.get("Surprise(%)")}
        for h in HORIZONS:  # drift measured from two days after the announcement: no look-ahead
            row[f"drift_{h}d"] = excess(i + 1, i + 1 + h)
        rows.append(row)
    study = pd.DataFrame(rows)
    print(f"\n### Post-earnings drift: {len(study)} announcements, {study['symbol'].nunique()} stocks, "
          f"{study['date'].min().date() if len(study) else '-'} to {study['date'].max().date() if len(study) else '-'}")
    for signal in ("reaction", "eps_surprise"):
        for h in HORIZONS:
            pair = study[[signal, f"drift_{h}d", "year"]].replace([np.inf, -np.inf], np.nan).dropna()
            if len(pair) < 50:
                print(f"- {signal} -> {h}d: only {len(pair)} events, skipped")
                continue
            ic = spearmanr(pair[signal], pair[f"drift_{h}d"]).statistic
            t_stat = ic * np.sqrt((len(pair) - 2) / (1 - ic ** 2))
            terciles = pd.qcut(pair[signal].rank(method="first"), 3, labels=False)
            spread = pair[f"drift_{h}d"][terciles == 2].mean() - pair[f"drift_{h}d"][terciles == 0].mean()
            yearly = pair.groupby("year").apply(lambda g: spearmanr(g[signal], g[f"drift_{h}d"]).statistic
                                                if len(g) >= 10 else np.nan).dropna()
            print(f"- {signal} -> {h}d: n={len(pair)}, IC {ic:.3f}, t-stat {t_stat:.2f}, "
                  f"top-minus-bottom third {spread * 100:.2f}%, IC>0 in {(yearly > 0).sum()}/{len(yearly)} years", flush=True)
    return study


def robustness(study):
    """Stricter checks: one IC per earnings season (events in a season move together), and recent years alone."""
    study = study.assign(season=study["date"].dt.to_period("Q"))
    print("\n### Robustness: market reaction signal")
    for h in HORIZONS:
        col = f"drift_{h}d"
        seasonal = study.groupby("season").apply(
            lambda g: spearmanr(g["reaction"], g[col]).statistic if len(g) >= 15 else np.nan).dropna()
        t_stat = seasonal.mean() / seasonal.std(ddof=1) * np.sqrt(len(seasonal))
        recent = study[study["date"] >= "2022-11-01"]
        recent_ic = spearmanr(recent["reaction"], recent[col]).statistic
        print(f"- {h}d: per-season IC {seasonal.mean():.3f}, t-stat {t_stat:.2f} over {len(seasonal)} seasons, "
              f"IC>0 in {(seasonal > 0).mean() * 100:.0f}% | last 4 years alone: IC {recent_ic:.3f} (n={len(recent)})", flush=True)


def calibration(study):
    """Numbers the app uses: reaction cut-offs for thirds and how each third did afterwards."""
    low, high = study["reaction"].quantile([1 / 3, 2 / 3])
    print(f"\n### Calibration: reaction cut-offs {low:.5f} / {high:.5f}")
    groups = pd.cut(study["reaction"], [-np.inf, low, high, np.inf], labels=["strong_negative", "neutral", "strong_positive"])
    for name, g in study.groupby(groups, observed=True):
        for h in (20, 60):
            d = g[f"drift_{h}d"]
            print(f"- {name} {h}d: n={len(d)}, mean {d.mean() * 100:.2f}%, median {d.median() * 100:.2f}%, "
                  f"beat Nifty {(d > 0).mean() * 100:.0f}%", flush=True)


def main():
    symbols = NIFTY_50
    events = probe(symbols)
    if events.empty:
        print("No earnings history available; nothing to test.")
        return
    study = event_study(events, symbols)
    robustness(study)
    calibration(study)


if __name__ == "__main__":
    main()
