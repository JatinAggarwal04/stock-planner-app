import os
import joblib
import pandas as pd
import numpy as np
import gc 
from typing import List, Dict, Tuple
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
from huggingface_hub import HfApi

# Constants
MODEL_DIR = "models"
UNIVERSAL_MODEL_FILENAME = "universal_market_model.joblib"
TOP_NIFTY_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "LICI.NS","IDEA.NS"
]

class MLEngine:
    def __init__(self):
        self.xgb_model = None
        self.rf_model = None
        self.scaler = StandardScaler()
        self.feature_importance = {}
        self.backtest = None  # walk-forward report from the last training run
        
        # Ensure model directory exists
        if not os.path.exists(MODEL_DIR):
            os.makedirs(MODEL_DIR)
            
        # Try loading existing universal model
        self.load_model()

    def prepare_features(self, data: pd.DataFrame, target_col: str = 'Target_Moderate') -> Tuple[pd.DataFrame, pd.Series, List[str]]:
        feature_cols = [
            'RSI', 'MACD_Diff', 'ADX', 'Stoch_K', 'BB_Width',
            'Momentum_10', 'Momentum_20', 'Vol_Ratio',
            'Dist_SMA20', 'Dist_SMA50', 'Dist_SMA200',
            'Volume_Ratio', 'Close_Position', 'Trend_Score', 'CMF'
        ]
        
        # Ensure all columns exist
        missing_cols = [c for c in feature_cols if c not in data.columns]
        if missing_cols:
            # If missing, return empty
            return pd.DataFrame(), pd.Series(), feature_cols
            
        if target_col in data.columns:
            clean_data = data[feature_cols + [target_col]].dropna()
            X = clean_data[feature_cols]
            y = clean_data[target_col]
        else:
            # For prediction (no target)
            clean_data = data[feature_cols].dropna()
            X = clean_data
            y = None
        
        return X, y, feature_cols
    
    @staticmethod
    def _fit(X: pd.DataFrame, y: pd.Series):
        """Fit the scaler, XGBoost and Random Forest on one training set."""
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        xgb = XGBClassifier(
            n_estimators=300, learning_rate=0.03, max_depth=5,
            min_child_weight=3, subsample=0.8, colsample_bytree=0.8,
            eval_metric='logloss', random_state=42
        )
        xgb.fit(X_scaled, y)
        rf = RandomForestClassifier(
            n_estimators=200, max_depth=8, min_samples_split=10,
            min_samples_leaf=5, random_state=42
        )
        rf.fit(X_scaled, y)
        return scaler, xgb, rf

    @staticmethod
    def _ensemble_probability(scaler, xgb, rf, X: pd.DataFrame) -> np.ndarray:
        X_scaled = scaler.transform(X)
        return xgb.predict_proba(X_scaled)[:, 1] * 0.6 + rf.predict_proba(X_scaled)[:, 1] * 0.4

    def train_model(self, X: pd.DataFrame, y: pd.Series, feature_cols: List[str]):
        """Fit on all the data (out-of-sample quality comes from walk_forward_backtest) and save."""
        if len(X) < 100:
            raise ValueError("Insufficient data")
        
        self.scaler, self.xgb_model, self.rf_model = self._fit(X, y)
        self.feature_importance = {k: float(v) for k, v in zip(feature_cols, self.xgb_model.feature_importances_)}
        
        # Save after training
        self.save_model()
        gc.collect()
        
        return {
            'top_features': sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]
        }

    def predict(self, latest_data: pd.DataFrame, feature_cols: List[str]) -> Dict:
        if self.xgb_model is None:
            return None # Indicate needed training
            
        X = latest_data[feature_cols]
        X_scaled = self.scaler.transform(X)
        
        xgb_prob = float(self.xgb_model.predict_proba(X_scaled)[0][1])
        rf_prob = float(self.rf_model.predict_proba(X_scaled)[0][1])
        ensemble_prob = (xgb_prob * 0.6) + (rf_prob * 0.4)
        
        return {
            'xgb_probability': round(xgb_prob * 100, 2),
            'rf_probability': round(rf_prob * 100, 2),
            'ensemble_probability': round(ensemble_prob * 100, 2)
        }

    def save_model(self):
        """Saves models and scaler to disk."""
        path = os.path.join(MODEL_DIR, UNIVERSAL_MODEL_FILENAME)
        payload = {
            "xgb": self.xgb_model,
            "rf": self.rf_model,
            "scaler": self.scaler,
            "importance": self.feature_importance,
            "backtest": self.backtest
        }
        # Write to a temp file then rename, so readers never see a half-written model
        tmp_path = f"{path}.tmp"
        joblib.dump(payload, tmp_path)
        os.replace(tmp_path, path)
        print(f"Model saved to {path}")

    def load_model(self):
        """Loads models from disk."""
        path = os.path.join(MODEL_DIR, UNIVERSAL_MODEL_FILENAME)
        if os.path.exists(path):
            try:
                payload = joblib.load(path)
                self.xgb_model = payload["xgb"]
                self.rf_model = payload["rf"]
                self.scaler = payload["scaler"]
                self.feature_importance = payload["importance"]
                self.backtest = payload.get("backtest")
                print("Universal Model loaded successfully.")
                gc.collect()
                return True
            except Exception as e:
                print(f"Failed to load model: {e}")
        return False

    def push_to_hub(self, repo_id: str, token: str):
        """Pushes the saved model to Hugging Face Hub."""
        try:
            api = HfApi(token=token)
            path = os.path.join(MODEL_DIR, UNIVERSAL_MODEL_FILENAME)
            
            api.upload_file(
                path_or_fileobj=path,
                path_in_repo=UNIVERSAL_MODEL_FILENAME,
                repo_id=repo_id,
                repo_type="model"
            )
            print(f"Model pushed to {repo_id}")
            return True
        except Exception as e:
            print(f"HF Push Error: {e}")
            return False


def walk_forward_backtest(X: pd.DataFrame, y: pd.Series, dates: pd.Series,
                          n_folds: int = 12, test_days: int = 252) -> Dict:
    """Out-of-sample evaluation the way the app actually uses the model.

    The last `test_days` trading days are split into `n_folds` consecutive blocks. Each block is predicted by a
    model trained only on dates before it, minus one day: a training row's label is the *next* day's return,
    so the last day before a block would otherwise leak the block's first close into training.
    Rows from all stocks on the same date always land on the same side of the split.
    """
    dates = pd.Series(pd.to_datetime(dates).values, index=X.index)
    unique_dates = np.sort(dates.unique())
    if len(unique_dates) <= test_days + 100:
        raise ValueError("Not enough history for a walk-forward backtest")
    
    probabilities, actual = [], []
    for fold in np.array_split(unique_dates[-test_days:], n_folds):
        fold_start = np.searchsorted(unique_dates, fold[0])
        train_mask = (dates < unique_dates[fold_start - 1]).values  # 1-day embargo
        test_mask = dates.isin(fold).values
        scaler, xgb, rf = MLEngine._fit(X[train_mask], y[train_mask])
        probabilities.append(MLEngine._ensemble_probability(scaler, xgb, rf, X[test_mask]))
        actual.append(y[test_mask].values)
    
    prob = np.concatenate(probabilities)
    up = np.concatenate(actual).astype(int)
    up_rate = float(up.mean())
    bullish, bearish = prob > 0.6, prob < 0.4  # the app's Bullish / Bearish thresholds
    
    def pct(value):
        return round(float(value) * 100, 1)
    
    return {
        "test_predictions": int(len(up)),
        "test_period": f"{pd.Timestamp(unique_dates[-test_days]).date()} to {pd.Timestamp(unique_dates[-1]).date()}",
        "accuracy": pct(((prob > 0.5).astype(int) == up).mean()),
        # Always guessing the most common outcome; the model must beat this to be useful
        "baseline_accuracy": pct(max(up_rate, 1 - up_rate)),
        "auc": round(float(roc_auc_score(up, prob)), 3) if 0 < up_rate < 1 else None,
        "up_day_rate": pct(up_rate),
        "bullish_calls": int(bullish.sum()),
        "bullish_hit_rate": pct(up[bullish].mean()) if bullish.any() else None,
        "bearish_calls": int(bearish.sum()),
        "bearish_hit_rate": pct(1 - up[bearish].mean()) if bearish.any() else None,
    }
