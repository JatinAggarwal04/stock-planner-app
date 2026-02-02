# backend/main.py
import os
import requests
import numpy as np
import pandas as pd
import yfinance as yf
import feedparser
import gc
from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from huggingface_hub import AsyncInferenceClient
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import warnings
import asyncio
import functools
from async_lru import alru_cache
from concurrent.futures import ThreadPoolExecutor
from scipy.signal import argrelextrema
from advanced_analytics import calculate_pressure_index, calculate_breakout_probability
from ml_engine import MLEngine, TOP_NIFTY_STOCKS
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
    allow_origins=["*"],  # Allow all origins for Vercel/Render integration
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
# ==================== SENTIMENT ENGINE ====================
class SentimentAnalyzer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Use Async client
        self.client = AsyncInferenceClient(token=api_key) if api_key else None
    
    async def analyze_finbert(self, text_list: List[str]) -> Dict:
        """Enhanced FinBERT with confidence tracking (Async)"""
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
            
            # Process only top 5 headlines
            for text in text_list[:5]:
                try:
                    # Async Inference Call
                    result = await self.client.text_classification(
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
# ==================== ML ENGINE (Refactored to ml_engine.py) ====================

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

    @staticmethod
    def calculate_stop_levels(entry_price: float, atr: float, signal: str = "BUY"):
        """Calculates Capital Protection (7%), Conservative (5%), and Aggressive (10%) stops."""
        levels = {}
        if signal == "BUY":
            levels['capital_protection_7pct'] = round(entry_price * 0.93, 2)
            levels['conservative_5pct'] = round(entry_price * 0.95, 2)
            levels['aggressive_10pct'] = round(entry_price * 0.90, 2)
            levels['technical_2x_atr'] = round(entry_price - (2 * atr), 2)
        else: # SELL
            levels['capital_protection_7pct'] = round(entry_price * 1.07, 2)
            levels['conservative_5pct'] = round(entry_price * 1.05, 2)
            levels['aggressive_10pct'] = round(entry_price * 1.10, 2)
            levels['technical_2x_atr'] = round(entry_price + (2 * atr), 2)
        return levels

# ==================== TRADING PLAN GENERATOR (QUANT ENGINE) ====================
class TradingPlanGenerator:
    @staticmethod
    def calculate_intraday_levels(df: pd.DataFrame) -> Dict:
        """Calculate Pivot Points and CPR for Intraday Trading (Zerodha/Kite Standard)
        
        Uses PREVIOUS day's OHLC data as per industry standard.
        """
        # Use PREVIOUS day's candle for pivot calculation (Industry Standard)
        if len(df) < 2:
            return {"error": "Insufficient data for pivot calculation"}
        
        prev_candle = df.iloc[-2]  # Previous trading session
        
        high = float(prev_candle['High'])
        low = float(prev_candle['Low'])
        close = float(prev_candle['Close'])
        
        # Standard Pivot Point
        pivot = (high + low + close) / 3
        
        # Central Pivot Range (CPR)
        bc = (high + low) / 2  # Bottom Central Pivot
        tc = (pivot - bc) + pivot  # Top Central Pivot
        
        # Standard Pivot Levels (Zerodha/Kite Formula)
        r1 = (2 * pivot) - low
        s1 = (2 * pivot) - high
        r2 = pivot + (high - low)
        s2 = pivot - (high - low)
        r3 = high + 2 * (pivot - low)
        s3 = low - 2 * (high - pivot)
        
        # CPR Width Analysis (for trend strength)
        cpr_width = abs(tc - bc)
        cpr_width_pct = (cpr_width / pivot) * 100
        cpr_type = "Narrow" if cpr_width_pct < 0.5 else "Wide"
        
        current_price = float(df['Close'].iloc[-1])
        
        return {
            "strategy": "Intraday Pivot Points (Standard)",
            "cpr": {
                "top_central_pivot": round(tc, 2),
                "pivot": round(pivot, 2),
                "bottom_central_pivot": round(bc, 2),
                "width_pct": round(cpr_width_pct, 2),
                "type": cpr_type
            },
            "resistance": {
                "R1": round(r1, 2),
                "R2": round(r2, 2),
                "R3": round(r3, 2)
            },
            "support": {
                "S1": round(s1, 2),
                "S2": round(s2, 2),
                "S3": round(s3, 2)
            },
            "current_price": round(current_price, 2),
            "previous_day": {
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close, 2)
            },
            "message": f"Pivot: ₹{round(pivot, 2)} | CPR: {cpr_type}. R1: ₹{round(r1, 2)}, S1: ₹{round(s1, 2)}"
        }

    @staticmethod
    def calculate_swing_targets(df: pd.DataFrame, current_price: float, trend: str) -> Dict:
        """Calculate ATR-based targets and Weekly Pivots for Swing Trading (few days to weeks)
        
        Zerodha uses weekly HLC for 30m/1hr timeframes.
        """
        atr = float(df['ATR'].iloc[-1]) if 'ATR' in df.columns else float(df['High'].iloc[-1] - df['Low'].iloc[-1])
        
        # ATR-based Stop Loss and Targets
        stop_loss_dist = 1.5 * atr
        target_1_dist = 1.5 * atr
        target_2_dist = 3.0 * atr
        
        if trend == "Bearish":
            stop_loss = current_price + stop_loss_dist
            target_1 = current_price - target_1_dist
            target_2 = current_price - target_2_dist
            rec_type = "SHORT"
        else:
            stop_loss = current_price - stop_loss_dist
            target_1 = current_price + target_1_dist
            target_2 = current_price + target_2_dist
            rec_type = "LONG"
        
        # Weekly Pivot Calculation (Last 5 trading days)
        weekly_data = df.tail(5)
        weekly_high = float(weekly_data['High'].max())
        weekly_low = float(weekly_data['Low'].min())
        weekly_close = float(df['Close'].iloc[-1])  # Latest close
        
        weekly_pivot = (weekly_high + weekly_low + weekly_close) / 3
        weekly_r1 = (2 * weekly_pivot) - weekly_low
        weekly_s1 = (2 * weekly_pivot) - weekly_high
        weekly_r2 = weekly_pivot + (weekly_high - weekly_low)
        weekly_s2 = weekly_pivot - (weekly_high - weekly_low)
            
        return {
            "strategy": "Swing Trading (ATR + Weekly Pivots)",
            "recommendation": rec_type,
            "entry_price": round(current_price, 2),
            "stop_loss": round(stop_loss, 2),
            "target_1": round(target_1, 2),
            "target_2": round(target_2, 2),
            "risk_reward": "1:2",
            "atr": round(atr, 2),
            "weekly_pivots": {
                "pivot": round(weekly_pivot, 2),
                "R1": round(weekly_r1, 2),
                "R2": round(weekly_r2, 2),
                "S1": round(weekly_s1, 2),
                "S2": round(weekly_s2, 2),
                "weekly_high": round(weekly_high, 2),
                "weekly_low": round(weekly_low, 2)
            }
        }

    @staticmethod
    def calculate_long_term_targets(current_price: float, volatility_annual: float, df: pd.DataFrame = None) -> Dict:
        """Calculate statistical targets and Monthly Pivots for long term holding (months)
        
        Zerodha uses monthly HLC for daily timeframe pivots.
        """
        # Statistical projection based on Normal Distribution (1 Standard Deviation)
        # Target = Current * (1 + (Vol * sqrt(time)))
        
        # 3 Months (0.25 year)
        target_3m_up = current_price * (1 + (volatility_annual/100 * np.sqrt(0.25)))
        target_3m_down = current_price * (1 - (volatility_annual/100 * np.sqrt(0.25)))
        
        # 6 Months (0.5 year)
        target_6m_up = current_price * (1 + (volatility_annual/100 * np.sqrt(0.50)))
        
        # 12 Months (1 year)
        target_1y_up = current_price * (1 + (volatility_annual/100))
        
        result = {
            "strategy": "Long Term Investment (Monthly Pivots)",
            "statistical_targets": {
                "3_month_upside": round(target_3m_up, 2),
                "3_month_downside": round(target_3m_down, 2),
                "6_month_upside": round(target_6m_up, 2),
                "1_year_upside": round(target_1y_up, 2)
            },
            "note": "Targets based on 1-SD historical volatility probability."
        }
        
        # Monthly Pivot Calculation (if df is provided)
        if df is not None and len(df) >= 22:  # ~22 trading days in a month
            monthly_data = df.tail(22)
            monthly_high = float(monthly_data['High'].max())
            monthly_low = float(monthly_data['Low'].min())
            monthly_close = float(df['Close'].iloc[-1])
            
            monthly_pivot = (monthly_high + monthly_low + monthly_close) / 3
            monthly_r1 = (2 * monthly_pivot) - monthly_low
            monthly_s1 = (2 * monthly_pivot) - monthly_high
            
            # 52-Week High/Low
            year_data = df.tail(252) if len(df) >= 252 else df
            week52_high = float(year_data['High'].max())
            week52_low = float(year_data['Low'].min())
            
            result["monthly_pivots"] = {
                "pivot": round(monthly_pivot, 2),
                "R1": round(monthly_r1, 2),
                "S1": round(monthly_s1, 2),
                "monthly_high": round(monthly_high, 2),
                "monthly_low": round(monthly_low, 2)
            }
            result["52_week"] = {
                "high": round(week52_high, 2),
                "low": round(week52_low, 2),
                "current_vs_high_pct": round(((current_price - week52_high) / week52_high) * 100, 2),
                "current_vs_low_pct": round(((current_price - week52_low) / week52_low) * 100, 2)
            }
        
        return result

# ==================== PERSONALIZED RECOMMENDATION ENGINE ====================
class PersonalizedRecommendation:
    @staticmethod
    def analyze_user_position(current_price: float, buy_price: float, quantity: int, 
                             stop_loss: float, targets: Dict, risk_metrics: Dict, trading_plan: Dict) -> Dict:
        """Generate personalized recommendations based on user's position"""
        
        # Calculate current P&L
        total_investment = float(buy_price * quantity)
        current_value = float(current_price * quantity)
        profit_loss = float(current_value - total_investment)
        profit_loss_pct = float((profit_loss / total_investment) * 100)
        
        # Risk assessment
        distance_from_sl = float(((current_price - stop_loss) / current_price) * 100)
        
        # Generate recommendation
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
        elif profit_loss_pct <= -7:
             action = "EXIT_IMMEDIATELY"
             message = "Unrealized loss > 7%. Capital Protection Rule triggered. Recommended exit to preserve capital."
        else:
            action = "EXIT_CONSIDER"
            message = f"Position showing significant loss. Review your thesis. Stop-loss at ₹{stop_loss} is critical."
        
        # Calculate User Specific Stops (Based on Buy Price)
        atr = trading_plan.get('swing', {}).get('atr', current_price * 0.02)
        user_stops = RiskManager.calculate_stop_levels(buy_price, atr, "BUY") # Assuming Long for user position

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
            "user_stops": user_stops,  # New Field based on Buy Price
            "targets_status": targets_status,
            "risk_alert": "CRITICAL" if distance_from_sl < 3 else "HIGH" if distance_from_sl < 5 else "MODERATE",
            "trading_plan": trading_plan  # Include the plan in the response
        }

# ==================== TECHNICAL ANALYZER (RULE BASED) ====================
class TechnicalAnalyzer:
    @staticmethod
    def analyze_long_term_view(df: pd.DataFrame) -> Dict:
        """Rule-based analysis for Long Term view (Trend)"""
        
        # Calculate Indicators if not present (Safety check)
        if 'SMA_200' not in df.columns:
            df['SMA_200'] = SMAIndicator(close=df['Close'], window=200).sma_indicator()
        if 'SMA_50' not in df.columns:
            df['SMA_50'] = SMAIndicator(close=df['Close'], window=50).sma_indicator()
        if 'ADX' not in df.columns:
            df['ADX'] = ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=14).adx()
            
        current_price = float(df['Close'].iloc[-1])
        sma_200 = float(df['SMA_200'].iloc[-1]) if not pd.isna(df['SMA_200'].iloc[-1]) else current_price
        sma_50 = float(df['SMA_50'].iloc[-1]) if not pd.isna(df['SMA_50'].iloc[-1]) else current_price
        adx = float(df['ADX'].iloc[-1]) if not pd.isna(df['ADX'].iloc[-1]) else 0.0
        
        # 1. Trend Determination
        if current_price > sma_200:
            trend = "Bullish"
            confidence = 60
            reasons = ["Price Above 200 SMA"]
        else:
            trend = "Bearish"
            confidence = 60
            reasons = ["Price Below 200 SMA"]
            
        # 2. Golden Cross / Death Cross Check
        is_golden_cross = sma_50 > sma_200
        
        if trend == "Bullish" and is_golden_cross:
            confidence += 20
            reasons.append("Golden Cross (50 SMA > 200 SMA)")
        elif trend == "Bearish" and not is_golden_cross:
            confidence += 20
            reasons.append("Death Cross (50 SMA < 200 SMA)")
            
        # 3. ADX Strength
        if adx > 25:
            confidence += 10
            reasons.append(f"Strong Trend (ADX {int(adx)})")
        elif adx < 20:
            confidence -= 10
            reasons.append("Weak Trend")
            
        confidence = min(100, max(0, confidence))
        
        return {
            "signal": trend,
            "confidence": int(confidence),
            "reasons": reasons,
            "indicators": {
                "sma_200": round(sma_200, 2),
                "adx": round(adx, 2),
                "is_golden_cross": bool(is_golden_cross)
            }
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
            "Position sizing calculator",
            "Algorithmic Trading Plans (Intraday/Swing/Long Term)"
        ],
        "endpoints": {
            "analyze": "/analyze/{symbol}",
            "personalized": "/analyze/{symbol}/personalized",
            "quick_quote": "/quote/{symbol}"
        },
        "examples": ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS"]
    }

@alru_cache(maxsize=100, ttl=3600)  # Cache for 1 hour
async def fetch_stock_news(symbol: str, max_items: int = 5):
    """Fetches latest news and performs sentiment analysis (Async + Cached)."""
    try:
        loop = asyncio.get_event_loop()
        
        # Determine company name (Blocking, so run in executor or just use symbol for speed)
        # Using symbol for search is faster and safer for generic searches
        import urllib.parse
        search_query = urllib.parse.quote(f"{symbol} stock news India when:7d")
        rss_url = f"https://news.google.com/rss/search?q={search_query}&hl=en-IN&gl=IN&ceid=IN:en"
        
        # Async Feed Fetch using Executor
        feed = await loop.run_in_executor(None, feedparser.parse, rss_url)
        
        news = [{"title": x.title, "link": x.link, "published": x.published} for x in feed.entries[:max_items]]
        headlines = [x['title'] for x in news]
        
        if not headlines:
             return {"news": [], "sentiment": {"score": 0, "sentiment": "Neutral", "label": "Neutral"}}

        # Sentiment Analysis (Async)
        sentiment_analyzer = SentimentAnalyzer(HF_API_KEY)
        sentiment = await sentiment_analyzer.analyze_finbert(headlines)
        
        return {
            "news": news,
            "sentiment": sentiment
        }
    except Exception as e:
        print(f"News fetch error: {e}")
        return {"news": [], "sentiment": {"score": 0, "sentiment": "Neutral", "label": "Neutral"}}

@app.get("/analyze/{symbol}")
async def analyze_stock(symbol: str, account_size: float = 100000, risk_per_trade: float = 2.0):
    """Hybrid Analysis: ML for Short Term, Rules for Long Term + Sentiment"""
    
    try:
        if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
            symbol = f"{symbol}.NS"
        
        loop = asyncio.get_event_loop()
        
        # PARALLEL EXECUTION: Fetch History & News concurrently
        async def fetch_history():
            ticker = yf.Ticker(symbol)
            # Run heavy pandas/network op in thread pool
            return await loop.run_in_executor(None, lambda: ticker.history(period="2y"))

        async def fetch_info():
             ticker = yf.Ticker(symbol)
             return await loop.run_in_executor(None, lambda: ticker.info)

        # Execute parallel tasks
        df_task = fetch_history()
        info_task = fetch_info()
        news_task = fetch_stock_news(symbol)
        
        # Wait for all
        df, info, news_data = await asyncio.gather(df_task, info_task, news_task)
        
        if df.empty or len(df) < 200:
            raise HTTPException(status_code=404, detail="Insufficient data")
        
        # Feature Engineering (CPU Bound - fast enough for main thread usually, but safe to offload if needed)
        feature_engine = FeatureEngine()
        df = feature_engine.calculate_technical_features(df)
        df = feature_engine.calculate_alpha_features(df)
        df = feature_engine.create_targets(df)
        
        # 1. ML Prediction & Live Learning (Universal Model)
        ml_engine = MLEngine()
        
        feature_cols = [
            'RSI', 'MACD_Diff', 'ADX', 'Stoch_K', 'BB_Width',
            'Momentum_10', 'Momentum_20', 'Vol_Ratio',
            'Dist_SMA20', 'Dist_SMA50', 'Dist_SMA200',
            'Volume_Ratio', 'Close_Position', 'Trend_Score', 'CMF'
        ]
        
        latest_features = df.iloc[[-1]]
        ml_predictions = ml_engine.predict(latest_features, feature_cols)
        
        if ml_predictions:
            # Model exists: Predict -> Live Learn
            ml_prob = ml_predictions['ensemble_probability']
            ml_stats = {"ensemble_accuracy": "Universal Model", "top_features": []}
            
            # LIVE LEARNING: Update with recent data
            try:
                # We update with recent history to reinforce patterns
                ml_engine.incremental_update(df.tail(100))
            except Exception as e:
                print(f"Live Learning Error: {e}")
        else:
            # Bootstrap: Train on this stock if no model exists
            print("Bootstrapping Universal Model...")
            X, y, _ = ml_engine.prepare_features(df)
            ml_stats = ml_engine.train_model(X, y, feature_cols)
            ml_predictions = ml_engine.predict(latest_features, feature_cols)
            ml_prob = ml_predictions['ensemble_probability']

        st_signal = "Bullish" if ml_prob > 60 else "Bearish" if ml_prob < 40 else "Neutral"
        st_confidence = ml_prob if st_signal == "Bullish" else (100 - ml_prob) if st_signal == "Bearish" else 50
        st_reasons = ["AI Model Prediction"] + [f"{k}: {v:.2f}" for k, v in ml_stats.get('top_features', [])]

        # 2. Rule Based Analysis (Long Term)
        tech_analyzer = TechnicalAnalyzer()
        lt_view = tech_analyzer.analyze_long_term_view(df)
        
        # 3. Sentiment Analysis
        # 3. Sentiment Analysis (Refactored)
        news = news_data['news']
        sentiment = news_data['sentiment']
        
        # 4. Support/Resistance & Risk
        sr_analyzer = SupportResistanceAnalyzer()
        support_resistance = sr_analyzer.find_levels(df)
        risk_manager = RiskManager()
        risk_metrics = risk_manager.calculate_metrics(df)
        
        # 5. Final Aggregation (Factoring in Sentiment)
        # Normalize Sentiment
        sent_prob = 50.0
        sent_score = sentiment.get('score', 0)
        if sentiment.get('sentiment') == 'Bullish':
             sent_prob = 50 + (sent_score * 50)
        elif sentiment.get('sentiment') == 'Bearish':
             sent_prob = 50 - (sent_score * 50)
        
        # Normalize Long Term
        lt_prob = lt_view['confidence'] if lt_view['signal'] == 'Bullish' else (100 - lt_view['confidence']) if lt_view['signal'] == 'Bearish' else 50
        
        # WEIGHTED FORMULA: ML (50%) + Trend (30%) + Sentiment (20%)
        final_score = (ml_prob * 0.5) + (lt_prob * 0.3) + (sent_prob * 0.2)
        final_signal = "BUY" if final_score > 60 else "SELL" if final_score < 40 else "HOLD"
        
        # Update Short Term confidence with sentiment influence
        st_confidence = (st_confidence * 0.8) + (sent_prob * 0.2)

        # Trade Setup
        current_price = float(df['Close'].iloc[-1])
        atr = float(df['ATR'].iloc[-1]) if 'ATR' in df.columns else float(df['Close'].iloc[-1] * 0.02)
        
        stop_loss = float(current_price - (2 * atr))
        target_1 = float(current_price + (2 * atr))
        target_2 = float(current_price + (3 * atr))
        target_3 = float(current_price + (4 * atr))
        
        position_info = risk_manager.calculate_position_size(
            account_size, risk_per_trade, current_price, stop_loss
        )

        # 6. Generate Trading Plan (Intraday, Swing, Long Term)
        # Re-using df since it has 2 years data
        intraday_plan = TradingPlanGenerator.calculate_intraday_levels(df)
        swing_plan = TradingPlanGenerator.calculate_swing_targets(
            df, 
            current_price, 
            "Bullish" if final_signal == 'BUY' else "Bearish"
        )
        long_term_plan = TradingPlanGenerator.calculate_long_term_targets(
            current_price,
            risk_metrics['volatility_annual'],
            df  # Pass df for monthly pivots
        )
        
        trading_plan = {
            "intraday": intraday_plan,
            "swing": swing_plan,
            "long_term": long_term_plan
        }
        
        # 7. Advanced Algorithmic Analysis (Industry Grade)
        pressure_index = calculate_pressure_index(df)
        
        # Determine meaningful resistance to test (using R1 from Intraday)
        r1_level = intraday_plan.get('resistance', {}).get('R1', 0)
        breakout_prob = calculate_breakout_probability(df, r1_level)

        gc.collect()

        return convert_to_python_type({
            "symbol": symbol,
            "company_name": info.get('longName', symbol),
            "current_price": round(current_price, 2),
            "advanced_metrics": {
                "pressure_index": pressure_index,
                "breakout_probability": breakout_prob
            },
            "recommendation": {
                "signal": final_signal,
                "confidence_score": round(final_score, 1),
                "summary": f"Hybrid signal based on ML ({st_signal}), Trend ({lt_view['signal']}), and Sentiment ({sentiment['sentiment']}).",
                "views": {
                    "short_term": {
                        "signal": st_signal,
                        "confidence": round(st_confidence, 1),
                        "reasons": st_reasons + [f"Sentiment Impact: {int(sent_prob)}%"],
                        "indicators": {
                            "rsi": round(df['RSI'].iloc[-1], 2),
                            "ml_score": ml_prob,
                            "macd_diff": round(df['MACD_Diff'].iloc[-1], 2)
                        }
                    },
                    "long_term": lt_view
                }
            },
            
            "ml_analysis": {
                "model_accuracy": ml_stats['ensemble_accuracy'] if ml_stats else 0,
                "top_features": ml_stats['top_features'] if ml_stats else []
            },

            "technical_analysis": { # Legacy structure
                 "rsi": df['RSI'].iloc[-1],
                 "macd": "Bullish",
                 "trend": lt_view['signal'],
                 "adx": lt_view['indicators']['adx']
            },
            "support_resistance": support_resistance,
            "risk_metrics": risk_metrics,
            "sentiment_analysis": sentiment,
            "latest_news": news,
            
            "trading_plan": trading_plan,  # New Field
            
            "trade_setup": {
                "entry_price": round(current_price, 2),
                "stop_loss": round(stop_loss, 2),
                "alternative_stops": risk_manager.calculate_stop_levels(
                    current_price, 
                    atr, 
                    "BUY" if final_signal == "BUY" else "SELL"
                ),
                "targets": {
                    "target_1": round(target_1, 2),
                    "target_2": round(target_2, 2),
                    "target_3": round(target_3, 2)
                },
                "risk_reward": f"1:{round((target_1 - current_price) / (current_price - stop_loss), 2)}"
            },
            "position_sizing": position_info,
            "market_data": {
                "52_week_high": round(float(df['High'].rolling(252).max().iloc[-1]) if len(df) >= 252 else float(df['High'].max()), 2),
                "52_week_low": round(float(df['Low'].rolling(252).min().iloc[-1]) if len(df) >= 252 else float(df['Low'].min()), 2),
                "avg_volume_20d": int(df['Volume'].rolling(20).mean().iloc[-1]),
                "current_volume": int(df['Volume'].iloc[-1]),
                "today_open": round(float(df['Open'].iloc[-1]), 2),
                "today_high": round(float(df['High'].iloc[-1]), 2),
                "today_low": round(float(df['Low'].iloc[-1]), 2),
                "market_cap": info.get('marketCap', 0),
                "pe_ratio": round(info.get('trailingPE', 0), 2)
            }
        })

    except Exception as e:
        print(f"Analysis Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analyze/{symbol}/personalized")
async def personalized_analysis(
    symbol: str,
    buy_price: float,
    quantity: int,
    account_size: float = 100000,
    risk_per_trade: float = 2.0
):
    """Personalized analysis based on user's position"""
    
    try:
        # Get base analysis
        base_analysis = await analyze_stock(symbol, account_size, risk_per_trade)
        
        # Need historical data for Trading Plan
        loop = asyncio.get_event_loop()
        stock = yf.Ticker(symbol)
        df_hist = await loop.run_in_executor(None, lambda: stock.history(period="1y"))
        
        # Calculate Trading Plans
        intraday_plan = TradingPlanGenerator.calculate_intraday_levels(df_hist)
        swing_plan = TradingPlanGenerator.calculate_swing_targets(
            df_hist, 
            base_analysis['current_price'], 
            "Bullish" if base_analysis['recommendation']['signal'] == 'BUY' else "Bearish"
        )
        long_term_plan = TradingPlanGenerator.calculate_long_term_targets(
            base_analysis['current_price'],
            base_analysis['risk_metrics']['volatility_annual'],
            df_hist  # Pass df for monthly pivots
        )
        
        trading_plan = {
            "intraday": intraday_plan,
            "swing": swing_plan,
            "long_term": long_term_plan
        }
        
        current_price = base_analysis['current_price']
        stop_loss = base_analysis['trade_setup']['stop_loss']
        targets = base_analysis['trade_setup']['targets']
        risk_metrics = base_analysis['risk_metrics']
        
        # Generate personalized recommendation
        personalized_rec = PersonalizedRecommendation.analyze_user_position(
            current_price, buy_price, quantity, stop_loss, targets, risk_metrics, trading_plan
        )
        
        # Merge with base analysis
        base_analysis['personalized_recommendation'] = personalized_rec
        
        return convert_to_python_type(base_analysis)
        
    except Exception as e:
        print(f"Personalized Analysis Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
def search_stocks(query: str):
    """Search for stocks using Yahoo Finance API"""
    try:
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(
            url, 
            params={
                'q': query,
                'quotesCount': 20, 
                'newsCount': 0,
                'enableFuzzyQuery': False,
                'quotesQueryId': 'tss_match_phrase_query'
            },
            headers=headers
        )
        
        data = response.json()
        
        if 'quotes' not in data:
            return []
            
        results = []
        for quote in data['quotes']:
            symbol = quote.get('symbol', '')
            
            # Filter for Indian stocks (NSE/BSE)
            if symbol.endswith('.NS') or symbol.endswith('.BO'):
                results.append({
                    "symbol": symbol,
                    "name": quote.get('longname') or quote.get('shortname') or symbol,
                    "exchange": "NSE" if symbol.endswith('.NS') else "BSE",
                    "type": quote.get('quoteType', 'EQUITY')
                })
                
        return results[:10]  # Return top 10 relevant results
        
    except Exception as e:
        print(f"Search API Error: {e}")
        # Return empty list instead of error for smooth UI
        return []

@app.get("/history/{symbol}")
def get_stock_history(symbol: str, period: str = "1mo"):
    """
    Get historical price data and corporate actions.
    Period map:
    1D -> 1d (interval 5m)
    1W -> 5d (interval 15m)
    1M -> 1mo (interval 1d)
    3M -> 3mo (interval 1d)
    1Y -> 1y (interval 1d)
    5Y -> 5y (interval 1wk)
    All -> max (interval 1mo)
    """
    try:
        if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
            symbol = f"{symbol}.NS"
            
        # Map frontend period to yfinance args
        yf_params = {
            "1D": {"period": "1d", "interval": "5m"},
            "1W": {"period": "5d", "interval": "15m"},
            "1M": {"period": "1mo", "interval": "1d"},
            "3M": {"period": "3mo", "interval": "1d"},
            "1Y": {"period": "1y", "interval": "1d"},
            "5Y": {"period": "5y", "interval": "1wk"},
            "All": {"period": "max", "interval": "1mo"},
        }
        
        params = yf_params.get(period, {"period": "1mo", "interval": "1d"})
        
        ticker = yf.Ticker(symbol)
        history = ticker.history(**params)
        
        if history.empty:
            return {"data": [], "events": [], "meta": {}}
            
        # Extract data points
        data = []
        # Reset index to get Date/Datetime as column
        history = history.reset_index()
        
        for _, row in history.iterrows():
            # Handle different date formats (Date vs Datetime)
            date_val = row.iloc[0]
            if isinstance(date_val, pd.Timestamp):
                timestamp = int(date_val.timestamp())
            else:
                timestamp = int(datetime.combine(date_val, datetime.min.time()).timestamp())
                
            data.append({
                "time": timestamp,
                "open": round(float(row['Open']), 2),
                "high": round(float(row['High']), 2),
                "low": round(float(row['Low']), 2),
                "close": round(float(row['Close']), 2),
                "volume": int(row['Volume'])
            })
            
        # Extract corporate actions
        events = []
        try:
            # Fetch actions (dividends, splits)
            # Note: yfinance .actions usually returns a dataframe with Date index, Dividends, Stock Splits
            actions = ticker.actions
            if not actions.empty:
                # Filter actions to be within the history range
                start_date = history.iloc[0].iloc[0]
                
                # Ensure start_date is timezone-naive
                if hasattr(start_date, 'tzinfo') and start_date.tzinfo is not None:
                    start_date = start_date.tz_localize(None)
                
                # Ensure actions index is timezone-naive
                if actions.index.tz is not None:
                    actions.index = actions.index.tz_localize(None)
                
                # Filter
                mask = actions.index >= start_date
                relevant_actions = actions.loc[mask]
                
                for date, row in relevant_actions.iterrows():
                    timestamp = int(date.timestamp())
                    
                    if row['Dividends'] > 0:
                        events.append({
                            "time": timestamp,
                            "type": "DIVIDEND",
                            "value": float(row['Dividends']),
                            "description": f"Dividend: ₹{float(row['Dividends'])}"
                        })
                    
                    if row['Stock Splits'] > 0:
                        events.append({
                            "time": timestamp,
                            "type": "SPLIT",
                            "value": float(row['Stock Splits']),
                            "description": f"Split: {float(row['Stock Splits'])}:1" # Usually representation might need adjustment
                        })
                        
        except Exception as e:
            print(f"Events fetching error: {e}")
            # Continue without events if this fails
            pass
            
        # Meta info for price change calculation
        # Meta info for price change calculation
        # Try to fetch previous close
        prev_close = None
        try:
            prev_close = ticker.info.get('previousClose')
        except:
            pass
            
        meta = {
            "symbol": symbol,
            "period": period,
            "currency": "INR",
            "previous_close": prev_close
        }
        
        # Determine previous close for accurate % change
        if period == "1D":
            # For 1D, we need the actual previous day's close
            try:
                prev_close = float(ticker.info.get('previousClose', data[0]['open']))
                meta['previous_close'] = prev_close
            except:
                meta['previous_close'] = data[0]['open'] 
        else:
            # For other periods, the comparison is usually first candle open or close
            meta['previous_close'] = data[0]['open']
            
        return convert_to_python_type({
            "data": data,
            "events": events,
            "meta": meta
        })
        
    except Exception as e:
        print(f"History API Error: {e}")
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

# ==================== AGENTIC CHAT ENDPOINT ====================
from pydantic import BaseModel
from agent_service import agent  # Import the agent instance

class ChatRequest(BaseModel):
    user_id: str
    message: str
    context: Optional[Dict] = None

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Agentic Chat Endpoint
    - Uses Gemini 2.0 Flash + Tools (GetPrice, GetAnalysis, RAG)
    - Maintains conversational context via agent_service
    """
    try:
        response = await agent.chat(
            user_id=request.user_id,
            message=request.message,
            context=request.context
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/train-universal")
def train_universal_model(background_tasks: BackgroundTasks):
    """Triggers training on Top Nifty Stocks in background."""
    def _train_job():
        print("Starting batch training...")
        ml_engine = MLEngine()
        all_X = []
        all_y = []
        
        feature_engine = FeatureEngine()
        
        for symbol in TOP_NIFTY_STOCKS:
            try:
                print(f"Fetching {symbol}...")
                ticker = yf.Ticker(symbol)
                df = ticker.history(period="2y")
                if len(df) < 200: continue
                
                # Apply same feature engineering pipeline
                df = feature_engine.calculate_technical_features(df)
                df = feature_engine.calculate_alpha_features(df)
                df = feature_engine.create_targets(df)
                
                X, y, cols = ml_engine.prepare_features(df)
                if not X.empty and y is not None:
                    all_X.append(X)
                    all_y.append(y)
            except Exception as e:
                print(f"Skipping {symbol}: {e}")
                
        if all_X:
            combined_X = pd.concat(all_X)
            combined_y = pd.concat(all_y)
            ml_engine.train_model(combined_X, combined_y, cols)
            print("Universal Model Trained & Saved.")
        else:
            print("No data collected for training.")
            
    background_tasks.add_task(_train_job)
    return {"status": "Training started in background"}

@app.post("/admin/push-model")
def push_model_to_hub(repo_id: str, token: str = None):
    """Push the trained Universal Model to Hugging Face Hub."""
    if not token:
        token = os.getenv("HF_TOKEN")
    
    if not token:
         raise HTTPException(status_code=400, detail="HF_TOKEN not found in env or request.")
         
    ml_engine = MLEngine()
    success = ml_engine.push_to_hub(repo_id, token)
    if success:
        return {"success": True, "message": f"Model pushed to {repo_id}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to push model.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)