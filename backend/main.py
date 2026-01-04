# backend/main.py
import os
import requests
import numpy as np
import pandas as pd
import yfinance as yf
import feedparser
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import warnings
from scipy.signal import argrelextrema
warnings.filterwarnings('ignore')

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

app = FastAPI(
    title="TradeWise - Indian Stock Market AI Platform",
    version="3.0",
    description="Enterprise-grade stock analysis with ML, sentiment analysis, and support/resistance detection"
)

# CORS for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Configuration
HF_API_KEY = os.getenv("HF_API_KEY")
NIFTY_50 = "^NSEI"

# Helper function to convert numpy types
def convert_to_python_type(obj):
    """Convert numpy types to native Python types for JSON serialization"""
    if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_to_python_type(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_python_type(item) for item in obj]
    elif pd.isna(obj):
        return None
    return obj

# ==================== SENTIMENT ENGINE ====================
class SentimentAnalyzer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = InferenceClient(token=api_key) if api_key else None
    
    def analyze_finbert(self, text_list: List[str]) -> Dict:
        """Enhanced FinBERT with confidence tracking"""
        if not text_list or not self.client:
            return {
                "score": 0.0,
                "confidence": 0.0,
                "breakdown": {"positive": 0, "negative": 0, "neutral": 0},
                "sentiment": "Neutral"
            }
        
        try:
            scores = []
            confidences = []
            breakdown = {"positive": 0, "negative": 0, "neutral": 0}
            
            for text in text_list[:5]:
                try:
                    result = self.client.text_classification(
                        text=text,
                        model="ProsusAI/finbert"
                    )
                    
                    headline_score = 0.0
                    max_confidence = 0.0
                    
                    for item in result:
                        label = item['label'].lower()
                        score = float(item['score'])
                        
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
                    continue
            
            if not scores:
                return {
                    "score": 0.0,
                    "confidence": 0.0,
                    "breakdown": breakdown,
                    "sentiment": "Neutral"
                }
            
            avg_score = float(np.mean(scores))
            avg_confidence = float(np.mean(confidences))
            
            return {
                "score": round(avg_score, 3),
                "confidence": round(avg_confidence * 100, 1),
                "breakdown": breakdown,
                "sentiment": "Bullish" if avg_score > 0.2 else "Bearish" if avg_score < -0.2 else "Neutral"
            }
            
        except Exception as e:
            print(f"FinBERT error: {e}")
            return {
                "score": 0.0,
                "confidence": 0.0,
                "breakdown": {"positive": 0, "negative": 0, "neutral": 0},
                "sentiment": "Neutral"
            }

# ==================== SUPPORT/RESISTANCE DETECTOR ====================
class SupportResistanceAnalyzer:
    @staticmethod
    def find_levels(df: pd.DataFrame, window: int = 20) -> Dict:
        """Detect support and resistance levels using local extrema"""
        
        highs = df['High'].values
        lows = df['Low'].values
        close = df['Close'].values
        
        # Find local maxima (resistance) and minima (support)
        resistance_idx = argrelextrema(highs, np.greater, order=window)[0]
        support_idx = argrelextrema(lows, np.less, order=window)[0]
        
        # Get recent levels (last 50 days)
        recent_days = min(50, len(df))
        resistance_levels = highs[resistance_idx[resistance_idx >= len(df) - recent_days]]
        support_levels = lows[support_idx[support_idx >= len(df) - recent_days]]
        
        current_price = float(close[-1])
        
        # Cluster nearby levels
        def cluster_levels(levels, threshold=0.02):
            if len(levels) == 0:
                return []
            
            levels = np.sort(levels)
            clustered = []
            current_cluster = [levels[0]]
            
            for level in levels[1:]:
                if (level - current_cluster[-1]) / current_cluster[-1] < threshold:
                    current_cluster.append(level)
                else:
                    clustered.append(float(np.mean(current_cluster)))
                    current_cluster = [level]
            
            clustered.append(float(np.mean(current_cluster)))
            return clustered
        
        resistance_clustered = cluster_levels(resistance_levels)
        support_clustered = cluster_levels(support_levels)
        
        # Find nearest levels
        nearest_resistance = min([r for r in resistance_clustered if r > current_price], default=None)
        nearest_support = max([s for s in support_clustered if s < current_price], default=None)
        
        # Calculate breakout probability
        atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else (df['High'] - df['Low']).iloc[-20:].mean()
        
        resistance_distance = None
        resistance_breakout_prob = 0.0
        support_distance = None
        support_breakdown_prob = 0.0
        
        if nearest_resistance:
            resistance_distance = float(((nearest_resistance - current_price) / current_price) * 100)
            # Higher probability if close to resistance with high volume and momentum
            distance_factor = max(0, 1 - (resistance_distance / 5))  # Closer = higher
            volume_factor = float(df['Volume'].iloc[-5:].mean() / df['Volume'].iloc[-20:].mean())
            momentum_factor = float((df['Close'].iloc[-1] - df['Close'].iloc[-5]) / df['Close'].iloc[-5])
            
            resistance_breakout_prob = min(95.0, (distance_factor * 40 + 
                                                   min(volume_factor * 30, 30) + 
                                                   max(0, momentum_factor * 100 * 30)))
        
        if nearest_support:
            support_distance = float(((current_price - nearest_support) / current_price) * 100)
            distance_factor = max(0, 1 - (support_distance / 5))
            volume_factor = float(df['Volume'].iloc[-5:].mean() / df['Volume'].iloc[-20:].mean())
            momentum_factor = float((df['Close'].iloc[-5] - df['Close'].iloc[-1]) / df['Close'].iloc[-5])
            
            support_breakdown_prob = min(95.0, (distance_factor * 40 + 
                                                min(volume_factor * 30, 30) + 
                                                max(0, momentum_factor * 100 * 30)))
        
        return {
            "current_price": round(current_price, 2),
            "nearest_resistance": round(nearest_resistance, 2) if nearest_resistance else None,
            "resistance_distance_pct": round(resistance_distance, 2) if resistance_distance else None,
            "resistance_breakout_probability": round(resistance_breakout_prob, 1),
            "nearest_support": round(nearest_support, 2) if nearest_support else None,
            "support_distance_pct": round(support_distance, 2) if support_distance else None,
            "support_breakdown_probability": round(support_breakdown_prob, 1),
            "all_resistance_levels": [round(r, 2) for r in sorted(resistance_clustered, reverse=True)[:5]],
            "all_support_levels": [round(s, 2) for s in sorted(support_clustered, reverse=True)[:5]],
            "trend": "Bullish" if nearest_resistance and resistance_breakout_prob > 60 else "Bearish" if nearest_support and support_breakdown_prob > 60 else "Neutral"
        }

# ==================== FEATURE ENGINE ====================
class FeatureEngine:
    @staticmethod
    def calculate_technical_features(df: pd.DataFrame) -> pd.DataFrame:
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
        
        # ADX
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
        data['Momentum_5'] = data['Close'].pct_change(5)
        data['Momentum_10'] = data['Close'].pct_change(10)
        data['Momentum_20'] = data['Close'].pct_change(20)
        
        data['Volatility_5'] = data['Close'].pct_change().rolling(5).std()
        data['Volatility_20'] = data['Close'].pct_change().rolling(20).std()
        data['Vol_Ratio'] = data['Volatility_5'] / (data['Volatility_20'] + 1e-10)
        
        data['Dist_SMA20'] = (data['Close'] - data['SMA_20']) / data['SMA_20']
        data['Dist_SMA50'] = (data['Close'] - data['SMA_50']) / data['SMA_50']
        data['Dist_SMA200'] = (data['Close'] - data['SMA_200']) / data['SMA_200']
        
        data['Volume_SMA20'] = data['Volume'].rolling(20).mean()
        data['Volume_Ratio'] = data['Volume'] / (data['Volume_SMA20'] + 1)
        
        data['High_Low_Ratio'] = (data['High'] - data['Low']) / data['Close']
        data['Close_Position'] = (data['Close'] - data['Low']) / (data['High'] - data['Low'] + 1e-10)
        
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
        data['Return_1d'] = data['Close'].pct_change(1).shift(-1)
        data['Target_Moderate'] = (data['Return_1d'] > 0.002).astype(int)
        return data

# ==================== ML ENGINE ====================
class MLEngine:
    def __init__(self):
        self.xgb_model = None
        self.rf_model = None
        self.scaler = StandardScaler()
        self.feature_importance = {}
    
    def prepare_features(self, data: pd.DataFrame, target_col: str = 'Target_Moderate'):
        feature_cols = [
            'RSI', 'MACD_Diff', 'ADX', 'Stoch_K', 'BB_Width',
            'Momentum_10', 'Momentum_20', 'Vol_Ratio',
            'Dist_SMA20', 'Dist_SMA50', 'Dist_SMA200',
            'Volume_Ratio', 'Close_Position', 'Trend_Score', 'CMF'
        ]
        
        clean_data = data[feature_cols + [target_col]].dropna()
        X = clean_data[feature_cols]
        y = clean_data[target_col]
        
        return X, y, feature_cols
    
    def train_ensemble(self, data: pd.DataFrame):
        X, y, feature_cols = self.prepare_features(data)
        
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
        
        return {
            'xgb_accuracy': round(xgb_acc * 100, 2),
            'rf_accuracy': round(rf_acc * 100, 2),
            'ensemble_accuracy': round((xgb_acc + rf_acc) / 2 * 100, 2),
            'top_features': sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    def predict(self, latest_data: pd.DataFrame, feature_cols: List[str]):
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

# ==================== RISK MANAGER ====================
class RiskManager:
    @staticmethod
    def calculate_metrics(df: pd.DataFrame):
        returns = df['Close'].pct_change().dropna()
        
        try:
            nifty = yf.Ticker(NIFTY_50)
            nifty_df = nifty.history(period="1y")
            nifty_returns = nifty_df['Close'].pct_change().dropna()
            
            common_dates = returns.index.intersection(nifty_returns.index)
            stock_ret = returns.loc[common_dates]
            market_ret = nifty_returns.loc[common_dates]
            
            covariance = float(np.cov(stock_ret, market_ret)[0][1])
            market_variance = float(np.var(market_ret))
            beta = covariance / market_variance if market_variance != 0 else 1.0
        except:
            beta = 1.0
        
        volatility = float(returns.std() * np.sqrt(252) * 100)
        risk_free_rate = 0.06
        avg_return = float(returns.mean() * 252)
        sharpe = float((avg_return - risk_free_rate) / (returns.std() * np.sqrt(252))) if returns.std() != 0 else 0.0
        
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = float(drawdown.min() * 100)
        
        var_95 = float(np.percentile(returns, 5) * 100)
        
        return {
            'beta': round(beta, 2),
            'volatility_annual': round(volatility, 2),
            'sharpe_ratio': round(sharpe, 2),
            'max_drawdown': round(max_drawdown, 2),
            'var_95': round(var_95, 2)
        }
    
    @staticmethod
    def calculate_position_size(account_size: float, risk_per_trade: float, entry_price: float, stop_loss: float):
        risk_amount = float(account_size * (risk_per_trade / 100))
        risk_per_share = float(abs(entry_price - stop_loss))
        
        if risk_per_share == 0:
            return {'shares': 0, 'position_value': 0.0, 'risk_amount': 0.0}
        
        shares = int(risk_amount / risk_per_share)
        position_value = float(shares * entry_price)
        
        return {
            'shares': shares,
            'position_value': round(position_value, 2),
            'risk_amount': round(risk_amount, 2)
        }

# ==================== PERSONALIZED RECOMMENDATION ENGINE ====================
class PersonalizedRecommendation:
    @staticmethod
    def analyze_user_position(current_price: float, buy_price: float, quantity: int, 
                             stop_loss: float, targets: Dict, risk_metrics: Dict) -> Dict:
        """Generate personalized recommendations based on user's position"""
        
        # Calculate current P&L
        total_investment = float(buy_price * quantity)
        current_value = float(current_price * quantity)
        profit_loss = float(current_value - total_investment)
        profit_loss_pct = float((profit_loss / total_investment) * 100)
        
        # Risk assessment
        distance_from_sl = float(((current_price - stop_loss) / current_price) * 100)
        
        # Generate recommendation
        if profit_loss_pct > 15:
            action = "BOOK_PARTIAL_PROFIT"
            message = f"Strong gains! Consider booking 50% profit and trailing stop-loss to ₹{round(current_price * 0.97, 2)}"
        elif profit_loss_pct > 8:
            action = "HOLD_TRAIL_SL"
            message = f"Good profit! Trail your stop-loss to ₹{round(buy_price * 1.02, 2)} (breakeven + 2%)"
        elif profit_loss_pct > 3:
            action = "HOLD"
            message = "Position in profit. Hold and monitor resistance levels."
        elif profit_loss_pct > -2:
            action = "HOLD"
            message = "Position near entry. Wait for breakout confirmation."
        elif profit_loss_pct > -5:
            action = "MONITOR_CLOSELY"
            message = f"Position in minor loss. Watch support at ₹{stop_loss}. Consider averaging if support holds."
        else:
            action = "EXIT_CONSIDER"
            message = f"Position showing significant loss. Review your thesis. Stop-loss at ₹{stop_loss} is critical."
        
        # Target achievement
        targets_status = {}
        for target_name, target_price in targets.items():
            if current_price >= target_price:
                targets_status[target_name] = "ACHIEVED"
            else:
                distance_pct = float(((target_price - current_price) / current_price) * 100)
                targets_status[target_name] = f"{round(distance_pct, 1)}% away"
        
        return {
            "position_summary": {
                "buy_price": round(buy_price, 2),
                "current_price": round(current_price, 2),
                "quantity": quantity,
                "total_investment": round(total_investment, 2),
                "current_value": round(current_value, 2),
                "profit_loss": round(profit_loss, 2),
                "profit_loss_pct": round(profit_loss_pct, 2),
                "risk_reward_ratio": round(distance_from_sl / abs(profit_loss_pct), 2) if profit_loss_pct != 0 else 0
            },
            "recommendation": {
                "action": action,
                "message": message,
                "confidence": "High" if abs(profit_loss_pct) > 5 else "Medium"
            },
            "targets_status": targets_status,
            "risk_alert": "CRITICAL" if distance_from_sl < 3 else "HIGH" if distance_from_sl < 5 else "MODERATE"
        }

# ==================== MAIN API ENDPOINTS ====================

@app.get("/")
def root():
    return {
        "service": "TradeWise - Indian Stock Market AI Platform",
        "version": "3.0",
        "features": [
            "ML-powered predictions (XGBoost + Random Forest)",
            "FinBERT sentiment analysis",
            "Support/Resistance detection with breakout probability",
            "Personalized trade recommendations",
            "Real-time risk metrics",
            "Position sizing calculator"
        ],
        "endpoints": {
            "analyze": "/analyze/{symbol}",
            "personalized": "/analyze/{symbol}/personalized",
            "quick_quote": "/quote/{symbol}"
        },
        "examples": ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS"]
    }

@app.get("/analyze/{symbol}")
def analyze_stock(symbol: str, account_size: float = 100000, risk_per_trade: float = 2.0):
    """Complete stock analysis with ML, sentiment, and support/resistance"""
    
    try:
        if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
            symbol = f"{symbol}.NS"
        
        ticker = yf.Ticker(symbol)
        info = ticker.info
        df = ticker.history(period="2y")
        
        if df.empty or len(df) < 200:
            raise HTTPException(status_code=404, detail="Insufficient data")
        
        # Feature Engineering
        feature_engine = FeatureEngine()
        df = feature_engine.calculate_technical_features(df)
        df = feature_engine.calculate_alpha_features(df)
        df = feature_engine.create_targets(df)
        
        # ML Predictions
        ml_engine = MLEngine()
        training_results = ml_engine.train_ensemble(df)
        
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
        company_name = info.get('longName', symbol).replace('Limited', '').replace('Ltd', '').strip()
        
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
        
        # Support/Resistance Analysis
        sr_analyzer = SupportResistanceAnalyzer()
        support_resistance = sr_analyzer.find_levels(df)
        
        # Risk Metrics
        risk_manager = RiskManager()
        risk_metrics = risk_manager.calculate_metrics(df)
        
        # Final Scoring
        ml_score = float(predictions['ensemble_probability'])
        sentiment_impact = float(sentiment['score'] * 10)
        
        final_confidence = float(ml_score + sentiment_impact)
        final_confidence = max(0.0, min(100.0, final_confidence))
        
        # Signal Generation
        if final_confidence >= 70 and risk_metrics['sharpe_ratio'] > 0.5:
            signal = "STRONG_BUY"
        elif final_confidence >= 55:
            signal = "BUY"
        elif final_confidence <= 30 and risk_metrics['sharpe_ratio'] < 0:
            signal = "STRONG_SELL"
        elif final_confidence <= 45:
            signal = "SELL"
        else:
            signal = "HOLD"
        
        # Trade Setup
        current_price = float(df['Close'].iloc[-1])
        atr = float(df['ATR'].iloc[-1])
        
        stop_loss = float(current_price - (2 * atr))
        target_1 = float(current_price + (2 * atr))
        target_2 = float(current_price + (3 * atr))
        target_3 = float(current_price + (4 * atr))
        
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
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol.upper(),
            "company_name": company_name,
            "current_price": round(current_price, 2),
            "currency": "INR",
            
            "recommendation": {
                "signal": signal,
                "confidence_score": round(final_confidence, 2),
                "risk_rating": "High" if risk_metrics['volatility_annual'] > 40 else "Medium" if risk_metrics['volatility_annual'] > 25 else "Low"
            },
            
            "ml_analysis": {
                "model": "Ensemble (XGBoost + Random Forest)",
                "ensemble_probability": predictions['ensemble_probability'],
                "xgb_probability": predictions['xgb_probability'],
                "rf_probability": predictions['rf_probability'],
                "model_accuracy": training_results['ensemble_accuracy'],
                "top_features": [{"feature": k, "importance": round(v, 3)} for k, v in training_results['top_features']]
            },
            
            "sentiment_analysis": sentiment,
            
            "technical_analysis": technical_summary,
            
            "support_resistance": support_resistance,
            
            "risk_metrics": risk_metrics,
            
            "trade_setup": {
                "entry_price": round(current_price, 2),
                "stop_loss": round(stop_loss, 2),
                "targets": {
                    "target_1": round(target_1, 2),
                    "target_2": round(target_2, 2),
                    "target_3": round(target_3, 2)
                },
                "risk_reward": f"1:{round((target_1 - current_price) / (current_price - stop_loss), 2)}"
            },
            
            "position_sizing": position_info,
            
            "market_data": {
                "52_week_high": round(float(df['High'].rolling(252).max().iloc[-1]), 2),
                "52_week_low": round(float(df['Low'].rolling(252).min().iloc[-1]), 2),
                "avg_volume_20d": int(df['Volume'].rolling(20).mean().iloc[-1]),
                "current_volume": int(latest_row['Volume'])
            },
            
            "latest_news": news[:5]
        }
        
        return convert_to_python_type(response)
        
    except Exception as e:
        print(f"Analysis Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analyze/{symbol}/personalized")
def personalized_analysis(
    symbol: str,
    buy_price: float,
    quantity: int,
    account_size: float = 100000,
    risk_per_trade: float = 2.0
):
    """Personalized analysis based on user's position"""
    
    try:
        # Get base analysis
        base_analysis = analyze_stock(symbol, account_size, risk_per_trade)
        
        current_price = base_analysis['current_price']
        stop_loss = base_analysis['trade_setup']['stop_loss']
        targets = base_analysis['trade_setup']['targets']
        risk_metrics = base_analysis['risk_metrics']
        
        # Generate personalized recommendation
        personalized_rec = PersonalizedRecommendation.analyze_user_position(
            current_price, buy_price, quantity, stop_loss, targets, risk_metrics
        )
        
        # Merge with base analysis
        base_analysis['personalized_recommendation'] = personalized_rec
        
        return convert_to_python_type(base_analysis)
        
    except Exception as e:
        print(f"Personalized Analysis Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/quote/{symbol}")
def quick_quote(symbol: str):
    """Quick price quote for watchlist"""
    
    try:
        if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
            symbol = f"{symbol}.NS"
        
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="5d")
        
        if df.empty:
            raise HTTPException(status_code=404, detail="Symbol not found")
        
        current = float(df['Close'].iloc[-1])
        previous = float(df['Close'].iloc[-2]) if len(df) > 1 else current
        change = float(current - previous)
        change_pct = float((change / previous) * 100) if previous != 0 else 0.0
        
        return convert_to_python_type({
            "symbol": symbol.upper(),
            "price": round(current, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": int(df['Volume'].iloc[-1]),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)