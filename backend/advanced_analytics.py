import pandas as pd
import numpy as np

def calculate_pressure_index(df: pd.DataFrame, period: int = 20) -> dict:
    """
    Calculates Buying vs Selling Pressure using Chaikin Money Flow (CMF) logic.
    Scores range from 0 (Heavy Selling) to 100 (Heavy Buying).
    """
    try:
        # Avoid division by zero
        range_padding = 0.0001
        
        # 1. Money Flow Multiplier = [(Close - Low) - (High - Close)] / (High - Low)
        # Ranges from -1 to 1. 
        # 1 = Close is High (Buying), -1 = Close is Low (Selling)
        df['MFM'] = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low'] + range_padding)
        
        # 2. Money Flow Volume
        df['MFV'] = df['MFM'] * df['Volume']
        
        # 3. CMF = Sum(MFV, n) / Sum(Vol, n)
        cmf = df['MFV'].rolling(window=period).sum() / df['Volume'].rolling(window=period).sum()
        
        current_cmf = cmf.iloc[-1]
        
        # Normalize CMF (-0.5 to 0.5 typical range) to 0-100 score
        # CMF > 0 is Buying, < 0 is Selling
        score = 50 + (current_cmf * 100)
        score = max(0, min(100, score)) # Clamp
        
        label = "Neutral"
        if score > 60: label = "Buying Pressure"
        if score > 80: label = "Strong Buying"
        if score < 40: label = "Selling Pressure"
        if score < 20: label = "Strong Selling"
        
        return {
            "score": round(score, 2),
            "label": label,
            "raw_cmf": round(current_cmf, 3)
        }
    except Exception as e:
        print(f"Error calculating pressure: {e}")
        return {"score": 50, "label": "Neutral (Error)", "raw_cmf": 0}

def calculate_breakout_probability(df: pd.DataFrame, resistance_level: float) -> dict:
    """
    Predicts probability of crossing resistance based on:
    1. Volume Trend (Is volume rising on approach?)
    2. Test Count (How many times tested?)
    3. Momentum Headroom (Is RSI < 70?)
    """
    try:
        current_price = df['Close'].iloc[-1]
        
        # Only meaningful if close to resistance (within 5%)
        distance = (resistance_level - current_price) / current_price
        
        if distance > 0.05:
            return {
                "probability": 0,
                "reason": "Price too far from resistance to predict breakout."
            }
        
        score = 0
        reasons = []
        
        # 1. Volume Trend (Last 5 days)
        # Linear regression slope of volume
        recent_vol = df['Volume'].tail(5).values
        x = np.arange(len(recent_vol))
        slope, _ = np.polyfit(x, recent_vol, 1)
        
        if slope > 0:
            score += 30
            reasons.append("Rising Volume (Demand increasing)")
        else:
            reasons.append("Falling Volume (Lack of conviction)")
            
        # 2. Test Count (Look back 60 days)
        # Count candles with High > (Resistance * 0.98)
        threshold = resistance_level * 0.98
        recent_highs = df['High'].tail(60)
        tests = (recent_highs > threshold).sum()
        
        if tests >= 3:
            score += 20
            reasons.append(f"Resistance Weaken by {tests} Tests")
        elif tests == 1:
             reasons.append("First Test (Resistance usually strong)")
        
        # 3. Momentum (RSI)
        # Requires calculating RS/RSI first, assuming rudimentary calc here for speed if not passed
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 0.0001)
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        if 50 < rsi < 70:
            score += 20
            reasons.append("Healthy Momentum (RSI 50-70, Room to run)")
        elif rsi > 70:
            score -= 10
            reasons.append("Overbought (RSI > 70, Pullback likely)")
            
        # 4. Price Proximity Proximity
        if distance < 0.01: # Extremely close
            score += 10
        
        # Base Probability
        probability = 20 + score # Start with 20% base chance
        probability = max(5, min(95, probability))
        
        return {
            "probability": round(probability, 1),
            "reasons": reasons,
            "test_count": int(tests)
        }
    except Exception as e:
        print(f"Error calculating breakout: {e}")
        return {"probability": 50, "reasons": ["Error in calculation"], "test_count": 0}
