import os
import requests
import numpy as np
import pandas as pd
import yfinance as yf
import feedparser
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

# Technical Analysis
from ta.trend import SMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange, BollingerBands

# The "Pro" Math Model
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split

load_dotenv()

app = FastAPI()

# --- CONFIGURATION ---
HF_API_URL = "https://api-inference.huggingface.co/models/ProsusAI/finbert"
HF_API_KEY = os.getenv("HF_API_KEY")

if not HF_API_KEY:
    print("WARNING: HF_API_KEY is missing in .env file. Sentiment analysis will fail.")

# --- 1. PRO NLP ENGINE (FinBERT) ---
def get_finbert_sentiment(text_list):
    """
    Sends news headlines to Hugging Face FinBERT model.
    Returns a score: -1 (Negative) to +1 (Positive).
    """
    if not text_list:
        return 0

    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    # We combine headlines to save API calls (Free tier limits)
    # But for accuracy, analyzing them individually is better. 
    # Let's send the top 3 headlines individually.
    
    total_score = 0
    count = 0

    for text in text_list[:3]:
        try:
            payload = {"inputs": text}
            response = requests.post(HF_API_URL, headers=headers, json=payload)
            data = response.json()
            
            # Error handling for model loading
            if isinstance(data, dict) and "error" in data:
                print(f"HF Error: {data['error']}")
                continue # Skip this headline

            # FinBERT returns a list of scores for [[Positive, Negative, Neutral]]
            # We need to parse this. Structure: [[{'label': 'positive', 'score': 0.9}, ...]]
            
            # Flatten the response
            scores = data[0] 
            
            # Calculate a composite score
            # We treat 'neutral' as 0, 'positive' as +1, 'negative' as -1
            headline_score = 0
            for item in scores:
                if item['label'] == 'positive': headline_score += item['score']
                if item['label'] == 'negative': headline_score -= item['score']
            
            total_score += headline_score
            count += 1
            
        except Exception as e:
            print(f"Sentiment Error: {e}")
            continue

    if count == 0: return 0
    return total_score / count

# --- 2. DATA PIPELINE ---
def get_clean_name(ticker_obj, symbol):
    try:
        full_name = ticker_obj.info.get('longName', symbol)
        return full_name.replace("Limited", "").replace("Ltd", "").replace("Inc", "").strip()
    except:
        return symbol

def get_stock_news(query_name):
    # Fetch news
    encoded_name = query_name.replace(" ", "+")
    rss_url = f"https://news.google.com/rss/search?q={encoded_name}+stock+news&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        feed = feedparser.parse(rss_url)
        return [{"title": x.title, "link": x.link, "published": x.published} for x in feed.entries[:5]]
    except:
        return []

def prepare_ml_data(df):
    data = df.copy()
    
    # Advanced Features
    data['RSI'] = RSIIndicator(close=data['Close'], window=14).rsi()
    data['MACD_Diff'] = MACD(close=data['Close']).macd_diff()
    data['SMA_200'] = SMAIndicator(close=data['Close'], window=200).sma_indicator()
    data['ATR'] = AverageTrueRange(high=data['High'], low=data['Low'], close=data['Close'], window=14).average_true_range()
    
    # Log Returns (Better for ML than raw prices)
    data['Log_Ret'] = np.log(data['Close'] / data['Close'].shift(1))
    
    # Volatility Ratio
    data['Vol_Ratio'] = data['Log_Ret'].rolling(5).std() / data['Log_Ret'].rolling(20).std()
    
    # Distance from Moving Average (Mean Reversion)
    data['Dist_SMA200'] = (data['Close'] - data['SMA_200']) / data['SMA_200']
    
    # Target: 1 if Next Day Return > 0.2% (Filter out noise), else 0
    data['Target'] = (data['Close'].shift(-1) > data['Close'] * 1.002).astype(int)
    
    return data.dropna()

# --- 3. PRO MATH ENGINE (XGBoost) ---
def train_xgboost(data):
    features = ['RSI', 'MACD_Diff', 'Vol_Ratio', 'Dist_SMA200', 'Log_Ret']
    X = data[features]
    y = data['Target']
    
    # Train/Test Split (Time Series aware: Don't shuffle!)
    split = int(len(X) * 0.85)
    X_train, X_test = X.iloc[:split], X.iloc[split:-1] # Drop last row (no target)
    y_train, y_test = y.iloc[:split], y.iloc[split:-1]
    
    # Initialize XGBoost (The "Pro" Model)
    # Scale_pos_weight helps if uptrends/downtrends are imbalanced
    model = XGBClassifier(
        n_estimators=200, 
        learning_rate=0.05, 
        max_depth=4, 
        eval_metric="logloss",
        use_label_encoder=False
    )
    
    model.fit(X_train, y_train)
    
    # Get current accuracy on the recent data (Validation)
    accuracy = model.score(X_test, y_test)
    
    return model, features, accuracy

# --- API ENDPOINTS ---
@app.get("/analyze/{symbol}")
def analyze_stock(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        company_name = get_clean_name(ticker, symbol)
        
        # We need more data for XGBoost to learn patterns
        df = ticker.history(period="2y")
        if df.empty: raise HTTPException(status_code=404, detail="No data")

        # 1. Run Data Pipeline
        data = prepare_ml_data(df)
        
        # 2. Train XGBoost Live
        model, features, backtest_acc = train_xgboost(data)
        
        # 3. Predict Today
        latest_features = data[features].iloc[[-1]]
        prob_up = model.predict_proba(latest_features)[0][1] # Probability of going Up
        
        # 4. Run FinBERT (Sentiment)
        news = get_stock_news(company_name)
        # Extract headlines for FinBERT
        headlines = [item['title'] for item in news]
        sentiment_score = get_finbert_sentiment(headlines) # -1 to 1
        
        # 5. Hybrid Decision Engine
        # Base confidence from the Math Model
        final_score = prob_up * 100 
        
        # Apply FinBERT Impact (Stronger weight than VADER)
        # FinBERT is accurate, so we trust it more (+/- 15%)
        sentiment_impact = sentiment_score * 15 
        final_score += sentiment_impact
        
        final_score = max(0, min(100, final_score))
        
        signal = "HOLD"
        if final_score > 70: signal = "BUY"
        if final_score < 30: signal = "SELL"
        
        latest_price = df['Close'].iloc[-1]
        atr = data['ATR'].iloc[-1]

        return {
            "symbol": symbol.upper(),
            "company_name": company_name,
            "current_price": round(latest_price, 2),
            "signal": signal,
            "confidence_score": round(final_score, 1),
            "ml_analysis": {
                "model": "XGBoost (Gradient Boosting)",
                "probability_up": f"{round(prob_up * 100, 1)}%",
                "model_accuracy_last_3mo": f"{round(backtest_acc * 100, 1)}%"
            },
            "sentiment_analysis": {
                "model": "FinBERT (Hugging Face)",
                "score": round(sentiment_score, 2), # -1 to 1
                "impact_on_score": f"{round(sentiment_impact, 1)} pts"
            },
            "trade_setup": {
                "stop_loss": round(latest_price - (2 * atr), 2),
                "target": round(latest_price + (3 * atr), 2)
            },
            "latest_news": news[:3]
        }

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))