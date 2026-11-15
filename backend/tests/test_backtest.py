"""Walk-forward backtest: no look-ahead, sensible metrics."""
import numpy as np
import pandas as pd
import pytest

import main
import ml_engine
from ml_engine import MLEngine, walk_forward_backtest


def dataset(days=500, stocks=2, signal=True, seed=0):
    """Rows for several stocks per business day. With `signal`, feature f0 predicts the label."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2022-01-03", periods=days, tz="Asia/Kolkata")
    frames = []
    for _ in range(stocks):
        X = pd.DataFrame(rng.normal(size=(days, 3)), columns=["f0", "f1", "f2"], index=dates)
        noise = rng.normal(scale=0.5, size=days)
        y = pd.Series(((X["f0"] + noise) > 0).astype(int) if signal else rng.integers(0, 2, days), index=dates)
        frames.append((X, y))
    X = pd.concat(f[0] for f in frames)
    y = pd.concat(f[1] for f in frames)
    return X, y


def test_no_training_row_is_from_the_test_block_or_the_day_before(monkeypatch):
    X, y = dataset()
    trained_until = []
    real_fit = MLEngine._fit

    def recording_fit(X_train, y_train):
        trained_until.append(X_train.index.max())
        return real_fit(X_train, y_train)

    monkeypatch.setattr(MLEngine, "_fit", staticmethod(recording_fit))
    walk_forward_backtest(X, y, X.index, n_folds=4, test_days=100)

    unique_dates = X.index.unique().sort_values()
    blocks = np.array_split(unique_dates[-100:], 4)
    assert len(trained_until) == 4
    for last_train_day, block in zip(trained_until, blocks):
        day_before_block = unique_dates[unique_dates.get_loc(block[0]) - 1]
        assert last_train_day < day_before_block


def test_metrics_on_learnable_data():
    X, y = dataset(signal=True)
    report = walk_forward_backtest(X, y, X.index, n_folds=4, test_days=100)
    assert report["test_predictions"] == 200  # 100 days x 2 stocks
    assert report["accuracy"] > report["baseline_accuracy"] + 10
    assert report["auc"] > 0.75
    assert report["bullish_calls"] > 0 and report["bullish_hit_rate"] > 60


def test_metrics_on_pure_noise_show_no_edge():
    X, y = dataset(signal=False, seed=3)
    report = walk_forward_backtest(X, y, X.index, n_folds=4, test_days=100)
    assert 0.35 < report["auc"] < 0.65
    assert report["accuracy"] < report["baseline_accuracy"] + 8


def test_needs_enough_history():
    X, y = dataset(days=150)
    with pytest.raises(ValueError):
        walk_forward_backtest(X, y, X.index, test_days=100)


def test_last_day_target_is_unknown_not_down():
    df = main.FeatureEngine.create_targets(pd.DataFrame({"Close": [100.0, 101.0, 100.5, 102.0]}))
    assert df["Target_Moderate"].tolist()[:3] == [1.0, 0.0, 1.0]
    assert np.isnan(df["Target_Moderate"].iloc[-1])


def test_backtest_is_saved_with_the_model(tmp_path, monkeypatch, trained_model):
    monkeypatch.setattr(ml_engine, "MODEL_DIR", str(tmp_path))
    trained_model.backtest = {"accuracy": 51.0}
    trained_model.save_model()
    assert MLEngine().backtest == {"accuracy": 51.0}
    trained_model.backtest = None


def test_model_report_endpoint(client, admin_headers, trained_model):
    report = client.get("/admin/model-report", headers=admin_headers)
    assert report.status_code == 200
    assert report.json()["trained"] is True
    assert client.get("/admin/model-report").status_code == 403
