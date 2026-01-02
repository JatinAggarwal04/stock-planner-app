import os
import requests
import numpy as np
import pandas as pd
import yfinance as yf
import feedparser
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

# Helper function to convert numpy types to Python types
def convert_to_python_type(obj):
    """Convert numpy types to native Python types for JSON serialization"""
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_to_python_type(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_python_type(item) for item in obj]
    return obj

# Technical Analysis
from ta.trend import SMAIndicator, EMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import AverageTrueRange, BollingerBands
from ta.volume import OnBalanceVolumeIndicator, ChaikinMoneyFlowIndicator

# ML Models
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

load_dotenv()

app = FastAPI(title="Indian Stock Market Analyzer Pro", version="2.0")

# --- CONFIGURATION ---
HF_API_KEY = os.getenv("HF_API_KEY")

if not HF_API_KEY:
    print("WARNING: HF_API_KEY missing. Sentiment analysis will be disabled.")

# Indian Market Indices for Beta Calculation
NIFTY_50 = "^NSEI"
SENSEX = "^BSESN"

# --- 1. ENHANCED SENTIMENT ENGINE ---
class SentimentAnalyzer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = InferenceClient(token=api_key) if api_key else None
    
    def analyze_finbert(self, text_list: List[str]) -> Dict:
        """Enhanced FinBERT with confidence tracking"""
        if not text_list or not self.client:
            return {"score": 0, "confidence": 0, "breakdown": {}}
        
        try:
            scores = []
            confidences = []
            breakdown = {"positive": 0, "negative": 0, "neutral": 0}
            
            for text in text_list[:5]:  # Analyze top 5 headlines
                try:
                    result = self.client.text_classification(
                        text=text,
                        model="ProsusAI/finbert"
                    )
                    
                    headline_score = 0
                    max_confidence = 0
                    
                    for item in result:
                        label = item['label'].lower()
                        score = item['score']
                        
                        if score > max_confidence:
                            max_confidence = score
                        
                        if label == 'positive':
                            headline_score += score
                            breakdown['positive'] += 1
                        elif label == 'negative':
                            headline_score -= score
                            breakdown['negative'] += 1
                        else:
                            breakdown['neutral'] += 1
                    
                    scores.append(headline_score)
                    confidences.append(max_confidence)
                    
                except Exception as e:
                    print(f"Headline analysis error: {e}")
                    continue
            
            if not scores:
                return {"score": 0, "confidence": 0, "breakdown": breakdown}
            
            avg_score = np.mean(scores)
            avg_confidence = np.mean(confidences)
            
            return {
                "score": round(avg_score, 3),
                "confidence": round(avg_confidence * 100, 1),
                "breakdown": breakdown,
                "sentiment": "Bullish" if avg_score > 0.2 else "Bearish" if avg_score < -0.2 else "Neutral"
            }
            
        except Exception as e:
            print(f"FinBERT error: {e}")
            return {"score": 0, "confidence": 0, "breakdown": {}}

# --- 2. ADVANCED FEATURE ENGINEERING ---
class FeatureEngine:
    @staticmethod
    def calculate_technical_features(df: pd.DataFrame) -> pd.DataFrame:
        """Calculate institutional-grade technical indicators"""
        data = df.copy()
        
        # Trend Indicators
        data['SMA_20'] = SMAIndicator(close=data['Close'], window=20).sma_indicator()
        data['SMA_50'] = SMAIndicator(close=data['Close'], window=50).sma_indicator()
        data['SMA_200'] = SMAIndicator(close=data['Close'], window=200).sma_indicator()
        data['EMA_12'] = EMAIndicator(close=data['Close'], window=12).ema_indicator()
        data['EMA_26'] = EMAIndicator(close=data['Close'], window=26).ema_indicator()
        
        # MACD
        macd = MACD(close=data['Close'])
        data['MACD'] = macd.macd()
        data['MACD_Signal'] = macd.macd_signal()
        data['MACD_Diff'] = macd.macd_diff()
        
        # Momentum
        data['RSI'] = RSIIndicator(close=data['Close'], window=14).rsi()
        stoch = StochasticOscillator(high=data['High'], low=data['Low'], close=data['Close'])
        data['Stoch_K'] = stoch.stoch()
        data['Stoch_D'] = stoch.stoch_signal()
        
        # ADX (Trend Strength)
        adx = ADXIndicator(high=data['High'], low=data['Low'], close=data['Close'], window=14)
        data['ADX'] = adx.adx()
        
        # Volatility
        data['ATR'] = AverageTrueRange(high=data['High'], low=data['Low'], close=data['Close'], window=14).average_true_range()
        bb = BollingerBands(close=data['Close'], window=20, window_dev=2)
        data['BB_High'] = bb.bollinger_hband()
        data['BB_Low'] = bb.bollinger_lband()
        data['BB_Width'] = (data['BB_High'] - data['BB_Low']) / data['Close']
        
        # Volume Indicators
        data['OBV'] = OnBalanceVolumeIndicator(close=data['Close'], volume=data['Volume']).on_balance_volume()
        data['CMF'] = ChaikinMoneyFlowIndicator(high=data['High'], low=data['Low'], close=data['Close'], volume=data['Volume']).chaikin_money_flow()
        
        return data
    
    @staticmethod
    def calculate_alpha_features(data: pd.DataFrame) -> pd.DataFrame:
        """Calculate proprietary alpha signals"""
        
        # Price Momentum
        data['Momentum_5'] = data['Close'].pct_change(5)
        data['Momentum_10'] = data['Close'].pct_change(10)
        data['Momentum_20'] = data['Close'].pct_change(20)
        
        # Volatility Features
        data['Volatility_5'] = data['Close'].pct_change().rolling(5).std()
        data['Volatility_20'] = data['Close'].pct_change().rolling(20).std()
        data['Vol_Ratio'] = data['Volatility_5'] / (data['Volatility_20'] + 1e-10)
        
        # Mean Reversion Signals
        data['Dist_SMA20'] = (data['Close'] - data['SMA_20']) / data['SMA_20']
        data['Dist_SMA50'] = (data['Close'] - data['SMA_50']) / data['SMA_50']
        data['Dist_SMA200'] = (data['Close'] - data['SMA_200']) / data['SMA_200']
        
        # Volume Analysis
        data['Volume_SMA20'] = data['Volume'].rolling(20).mean()
        data['Volume_Ratio'] = data['Volume'] / (data['Volume_SMA20'] + 1)
        
        # Price Action
        data['High_Low_Ratio'] = (data['High'] - data['Low']) / data['Close']
        data['Close_Position'] = (data['Close'] - data['Low']) / (data['High'] - data['Low'] + 1e-10)
        
        # Trend Strength
        data['Trend_Score'] = np.where(
            (data['Close'] > data['SMA_20']) & (data['SMA_20'] > data['SMA_50']) & (data['SMA_50'] > data['SMA_200']),
            1,
            np.where(
                (data['Close'] < data['SMA_20']) & (data['SMA_20'] < data['SMA_50']) & (data['SMA_50'] < data['SMA_200']),
                -1,
                0
            )
        )
        
        return data
    
    @staticmethod
    def create_targets(data: pd.DataFrame) -> pd.DataFrame:
        """Create multiple prediction targets"""
        
        # Next day return
        data['Return_1d'] = data['Close'].pct_change(1).shift(-1)
        
        # Binary targets with different thresholds
        data['Target_Conservative'] = (data['Return_1d'] > 0.005).astype(int)  # 0.5% threshold
        data['Target_Moderate'] = (data['Return_1d'] > 0.002).astype(int)      # 0.2% threshold
        data['Target_Aggressive'] = (data['Return_1d'] > 0.001).astype(int)    # 0.1% threshold
        
        return data

# --- 3. ENSEMBLE ML ENGINE ---
class MLEngine:
    def __init__(self):
        self.xgb_model = None
        self.rf_model = None
        self.scaler = StandardScaler()
        self.feature_importance = {}
    
    def prepare_features(self, data: pd.DataFrame, target_col: str = 'Target_Moderate'):
        """Prepare features for ML models"""
        
        feature_cols = [
            'RSI', 'MACD_Diff', 'ADX', 'Stoch_K', 'BB_Width',
            'Momentum_10', 'Momentum_20', 'Vol_Ratio',
            'Dist_SMA20', 'Dist_SMA50', 'Dist_SMA200',
            'Volume_Ratio', 'Close_Position', 'Trend_Score', 'CMF'
        ]
        
        # Remove rows with NaN
        clean_data = data[feature_cols + [target_col]].dropna()
        
        X = clean_data[feature_cols]
        y = clean_data[target_col]
        
        return X, y, feature_cols
    
    def train_ensemble(self, data: pd.DataFrame):
        """Train ensemble of models"""
        
        X, y, feature_cols = self.prepare_features(data)
        
        if len(X) < 100:
            raise ValueError("Insufficient data for training (need at least 100 samples)")
        
        # Time-series split (no shuffling)
        split_idx = int(len(X) * 0.80)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:-1]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:-1]
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # XGBoost
        self.xgb_model = XGBClassifier(
            n_estimators=300,
            learning_rate=0.03,
            max_depth=5,
            min_child_weight=3,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric='logloss',
            random_state=42
        )
        self.xgb_model.fit(X_train_scaled, y_train)
        xgb_acc = self.xgb_model.score(X_test_scaled, y_test)
        
        # Random Forest
        self.rf_model = RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42
        )
        self.rf_model.fit(X_train_scaled, y_train)
        rf_acc = self.rf_model.score(X_test_scaled, y_test)
        
        # Feature importance (from XGBoost)
        self.feature_importance = dict(zip(feature_cols, self.xgb_model.feature_importances_))
        
        return {
            'xgb_accuracy': round(xgb_acc * 100, 2),
            'rf_accuracy': round(rf_acc * 100, 2),
            'ensemble_accuracy': round((xgb_acc + rf_acc) / 2 * 100, 2),
            'top_features': sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    def predict(self, latest_data: pd.DataFrame, feature_cols: List[str]):
        """Ensemble prediction"""
        
        X = latest_data[feature_cols]
        X_scaled = self.scaler.transform(X)
        
        # Get probabilities from both models
        xgb_prob = self.xgb_model.predict_proba(X_scaled)[0][1]
        rf_prob = self.rf_model.predict_proba(X_scaled)[0][1]
        
        # Ensemble (weighted average, XGB gets more weight)
        ensemble_prob = (xgb_prob * 0.6) + (rf_prob * 0.4)
        
        return {
            'xgb_probability': round(xgb_prob * 100, 2),
            'rf_probability': round(rf_prob * 100, 2),
            'ensemble_probability': round(ensemble_prob * 100, 2)
        }

# --- 4. RISK MANAGEMENT ---
class RiskManager:
    @staticmethod
    def calculate_metrics(df: pd.DataFrame, symbol: str):
        """Calculate risk metrics"""
        
        returns = df['Close'].pct_change().dropna()
        
        # Fetch Nifty 50 for beta calculation
        try:
            nifty = yf.Ticker(NIFTY_50)
            nifty_df = nifty.history(period="1y")
            nifty_returns = nifty_df['Close'].pct_change().dropna()
            
            # Align dates
            common_dates = returns.index.intersection(nifty_returns.index)
            stock_ret = returns.loc[common_dates]
            market_ret = nifty_returns.loc[common_dates]
            
            # Beta calculation
            covariance = np.cov(stock_ret, market_ret)[0][1]
            market_variance = np.var(market_ret)
            beta = covariance / market_variance if market_variance != 0 else 1.0
        except:
            beta = 1.0
        
        # Volatility (annualized)
        volatility = returns.std() * np.sqrt(252) * 100
        
        # Sharpe Ratio (assuming 6% risk-free rate for India)
        risk_free_rate = 0.06
        avg_return = returns.mean() * 252
        sharpe = (avg_return - risk_free_rate) / (returns.std() * np.sqrt(252)) if returns.std() != 0 else 0
        
        # Max Drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min() * 100
        
        # VaR (Value at Risk) - 95% confidence
        var_95 = np.percentile(returns, 5) * 100
        
        return {
            'beta': float(round(beta, 2)),
            'volatility_annual': float(round(volatility, 2)),
            'sharpe_ratio': float(round(sharpe, 2)),
            'max_drawdown': float(round(max_drawdown, 2)),
            'var_95': float(round(var_95, 2))
        }
    
    @staticmethod
    def calculate_position_size(account_size: float, risk_per_trade: float, entry_price: float, stop_loss: float):
        """Kelly Criterion based position sizing"""
        
        risk_amount = account_size * (risk_per_trade / 100)
        risk_per_share = abs(entry_price - stop_loss)
        
        if risk_per_share == 0:
            return 0
        
        shares = risk_amount / risk_per_share
        position_value = shares * entry_price
        
        return {
            'shares': int(shares),
            'position_value': float(round(position_value, 2)),
            'risk_amount': float(round(risk_amount, 2))
        }

# --- MAIN API ENDPOINT ---
@app.get("/analyze/{symbol}")
def analyze_stock(symbol: str, account_size: float = 100000, risk_per_trade: float = 2.0):
    """
    Comprehensive Indian stock analysis
    
    Parameters:
    - symbol: Stock symbol (e.g., RELIANCE.NS, TCS.NS, INFY.NS)
    - account_size: Trading account size in INR (default: 100000)
    - risk_per_trade: Risk per trade in % (default: 2%)
    """
    
    try:
        # Ensure NSE suffix for Indian stocks
        if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
            symbol = f"{symbol}.NS"
        
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Fetch 2 years of data
        df = ticker.history(period="2y")
        if df.empty or len(df) < 200:
            raise HTTPException(status_code=404, detail="Insufficient data for analysis")
        
        # Feature Engineering
        feature_engine = FeatureEngine()
        df = feature_engine.calculate_technical_features(df)
        df = feature_engine.calculate_alpha_features(df)
        df = feature_engine.create_targets(df)
        
        # Train ML Models
        ml_engine = MLEngine()
        training_results = ml_engine.train_ensemble(df)
        
        # Current prediction
        feature_cols = [
            'RSI', 'MACD_Diff', 'ADX', 'Stoch_K', 'BB_Width',
            'Momentum_10', 'Momentum_20', 'Vol_Ratio',
            'Dist_SMA20', 'Dist_SMA50', 'Dist_SMA200',
            'Volume_Ratio', 'Close_Position', 'Trend_Score', 'CMF'
        ]
        latest_features = df[feature_cols].iloc[[-1]]
        predictions = ml_engine.predict(latest_features, feature_cols)
        
        # Sentiment Analysis
        sentiment_analyzer = SentimentAnalyzer(HF_API_KEY)
        company_name = info.get('longName', symbol).replace('Limited', '').strip()
        
        # Fetch news
        encoded_name = company_name.replace(" ", "+")
        rss_url = f"https://news.google.com/rss/search?q={encoded_name}+stock&hl=en-IN&gl=IN&ceid=IN:en"
        try:
            feed = feedparser.parse(rss_url)
            news = [{"title": x.title, "link": x.link, "published": x.published} for x in feed.entries[:5]]
            headlines = [x['title'] for x in news]
        except:
            news = []
            headlines = []
        
        sentiment = sentiment_analyzer.analyze_finbert(headlines)
        
        # Risk Metrics
        risk_manager = RiskManager()
        risk_metrics = risk_manager.calculate_metrics(df, symbol)
        
        # Final Scoring Algorithm
        ml_score = predictions['ensemble_probability']
        sentiment_impact = sentiment['score'] * 10  # -10 to +10 impact
        
        final_confidence = ml_score + sentiment_impact
        final_confidence = max(0, min(100, final_confidence))
        
        # Signal Generation
        if final_confidence >= 70 and risk_metrics['sharpe_ratio'] > 0.5:
            signal = "STRONG BUY"
        elif final_confidence >= 55:
            signal = "BUY"
        elif final_confidence <= 30 and risk_metrics['sharpe_ratio'] < 0:
            signal = "STRONG SELL"
        elif final_confidence <= 45:
            signal = "SELL"
        else:
            signal = "HOLD"
        
        # Trade Setup
        current_price = df['Close'].iloc[-1]
        atr = df['ATR'].iloc[-1]
        
        stop_loss = current_price - (2 * atr)
        target_1 = current_price + (2 * atr)
        target_2 = current_price + (3 * atr)
        target_3 = current_price + (4 * atr)
        
        # Position sizing
        position_info = risk_manager.calculate_position_size(
            account_size, risk_per_trade, current_price, stop_loss
        )
        
        # Technical Summary
        latest_row = df.iloc[-1]
        technical_summary = {
            'RSI': float(round(latest_row['RSI'], 2)),
            'MACD_Signal': 'Bullish' if latest_row['MACD_Diff'] > 0 else 'Bearish',
            'Trend_Strength_ADX': float(round(latest_row['ADX'], 2)),
            'Price_vs_SMA200': float(round(latest_row['Dist_SMA200'] * 100, 2)),
            'Volume_Status': 'High' if latest_row['Volume_Ratio'] > 1.2 else 'Normal' if latest_row['Volume_Ratio'] > 0.8 else 'Low'
        }
        
        # Convert all numpy types to Python types before returning
        response_data = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol.upper(),
            "company_name": company_name,
            "current_price": float(round(current_price, 2)),
            "currency": "INR",
            
            "recommendation": {
                "signal": signal,
                "confidence_score": float(round(final_confidence, 2)),
                "risk_rating": "High" if risk_metrics['volatility_annual'] > 40 else "Medium" if risk_metrics['volatility_annual'] > 25 else "Low"
            },
            
            "ml_analysis": {
                "model": "Ensemble (XGBoost + Random Forest)",
                "ensemble_probability": float(predictions['ensemble_probability']),
                "xgb_probability": float(predictions['xgb_probability']),
                "rf_probability": float(predictions['rf_probability']),
                "model_accuracy": float(training_results['ensemble_accuracy']),
                "top_features": [{"feature": k, "importance": float(round(v, 3))} for k, v in training_results['top_features']]
            },
            
            "sentiment_analysis": {
                "score": float(sentiment['score']),
                "sentiment": sentiment['sentiment'],
                "confidence": float(sentiment['confidence']),
                "impact": float(round(sentiment_impact, 2)),
                "breakdown": sentiment['breakdown']
            },
            
            "technical_analysis": technical_summary,
            
            "risk_metrics": risk_metrics,
            
            "trade_setup": {
                "entry_price": float(round(current_price, 2)),
                "stop_loss": float(round(stop_loss, 2)),
                "targets": {
                    "target_1": float(round(target_1, 2)),
                    "target_2": float(round(target_2, 2)),
                    "target_3": float(round(target_3, 2))
                },
                "risk_reward": f"1:{round((target_1 - current_price) / (current_price - stop_loss), 2)}"
            },
            
            "position_sizing": position_info,
            
            "market_data": {
                "52_week_high": float(round(df['High'].rolling(252).max().iloc[-1], 2)),
                "52_week_low": float(round(df['Low'].rolling(252).min().iloc[-1], 2)),
                "avg_volume_20d": int(df['Volume'].rolling(20).mean().iloc[-1]),
                "current_volume": int(latest_row['Volume'])
            },
            
            "latest_news": news[:3]
        }
        
        return convert_to_python_type(response_data)
        
    except Exception as e:
        print(f"Analysis Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {
        "service": "Indian Stock Market Analyzer Pro",
        "version": "2.0",
        "usage": "GET /analyze/{SYMBOL}?account_size=100000&risk_per_trade=2",
        "examples": ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "TATAMOTORS.NS"]
    }