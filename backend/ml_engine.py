import os
import joblib
import pandas as pd
import numpy as np
import yfinance as yf
import gc 
from typing import List, Dict, Tuple
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from huggingface_hub import HfApi, hf_hub_download

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
    
    def train_universal_model(self) -> Dict:
        """Trains a single model on multiple top Nifty stocks."""
        print("Starting Universal Model Training...")
        all_X = []
        all_y = []
        
        for symbol in TOP_NIFTY_STOCKS:
            try:
                print(f"Fetching {symbol}...")
                ticker = yf.Ticker(symbol)
                df = ticker.history(period="2y")
                
                if len(df) < 200: continue
                
                # We need to calculate features first (using FeatureEngine logic, 
                # but we need to duplicate/import it or assume data passed in has features.
                # simpler: We will assume main.py calls this with processed data 
                # OR we implement minimal feature eng here. 
                # For this step, let's assume we need to import FeatureEngine from main 
                # BUT that causes circular import.
                # BETTER: We Implement a static feature calc helper here or accept a list of DFs.
                
                # To keep it self-contained, let's just use the main.py pipeline logic 
                # but we will rely on `incremental_update` for the "live" part mostly.
                # Actually, effectively doing "Universal Training" requires the FeatureEngine.
                # Let's import FeatureEngine inside the method to avoid circular import if needed,
                # Or better, let's move FeatureEngine to a utils file later.
                # For now, I will skip the complex feature creation inside this class 
                # and assume the caller passes a combined DataFrame or we address this in Refactor.
                pass 
            except Exception as e:
                print(f"Error {symbol}: {e}")
                
        # ... logic continues ...
        # WAIT: The most robust way is to make `train_universal_model` accept a 
        # combined DataFrame of all stocks processed by main.py.
        # BUT `main.py` is the one calling this.
        return {"status": "Placeholder - Moved logic to main for feature eng access"}

    # Refined Approach: `train_model` accepts prepared X, y
    def train_model(self, X: pd.DataFrame, y: pd.Series, feature_cols: List[str]):
        if len(X) < 100:
            raise ValueError("Insufficient data")
        
        split_idx = int(len(X) * 0.80)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:-1]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:-1]
        
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        self.xgb_model = XGBClassifier(
            n_estimators=300, learning_rate=0.03, max_depth=5,
            min_child_weight=3, subsample=0.8, colsample_bytree=0.8,
            eval_metric='logloss', random_state=42
        )
        self.xgb_model.fit(X_train_scaled, y_train)
        xgb_acc = float(self.xgb_model.score(X_test_scaled, y_test))
        
        self.rf_model = RandomForestClassifier(
            n_estimators=200, max_depth=8, min_samples_split=10,
            min_samples_leaf=5, random_state=42
        )
        self.rf_model.fit(X_train_scaled, y_train)
        rf_acc = float(self.rf_model.score(X_test_scaled, y_test))
        
        self.feature_importance = {k: float(v) for k, v in zip(feature_cols, self.xgb_model.feature_importances_)}
        
        # Save after training
        # Save after training
        self.save_model()
        gc.collect()
        
        return {
            'xgb_accuracy': round(xgb_acc * 100, 2),
            'rf_accuracy': round(rf_acc * 100, 2),
            'ensemble_accuracy': round((xgb_acc + rf_acc) / 2 * 100, 2),
            'top_features': sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    def incremental_update(self, new_data: pd.DataFrame, target_col: str = 'Target_Moderate'):
        """
        Updates the model with new data points (Live Learning).
        Uses XGBoost's `xgb_model` parameter for continuation.
        """
        if self.xgb_model is None:
            return  # Can't update if not trained
            
        X, y, _ = self.prepare_features(new_data, target_col)
        if X.empty or y is None: return

        # Transform features
        # Note: Ideally we update scaler too, but partial_fit is for MinMaxScaler/StandardScaler 
        # if we used that. StandardScaler has partial_fit.
        self.scaler.partial_fit(X) 
        X_scaled = self.scaler.transform(X)
        
        # Update XGBoost (Warm Start)
        self.xgb_model.fit(X_scaled, y, xgb_model=self.xgb_model.get_booster())
        
        # RF doesn't support easy incremental learning in sklearn standard lib
        # We will re-fit RF or just rely on XGB for the "Learning" part
        # Or use `warm_start=True` if initialized that way (limited).
        # For this MVP, we focus on XGBoost learning.
        
        self.save_model()
        self.save_model()
        print("Model updated with live data.")
        gc.collect()

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
            "importance": self.feature_importance
        }
        joblib.dump(payload, path)
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
