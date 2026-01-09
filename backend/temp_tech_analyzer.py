class TechnicalAnalyzer:
    @staticmethod
    def analyze_long_term_view(df: pd.DataFrame) -> Dict:
        """Rule-based analysis for Long Term view (Trend)"""
        
        # Calculate Indicators if not present (Safety check)
        if 'SMA_200' not in df.columns:
            df['SMA_200'] = ta.trend.sma_indicator(df['Close'], window=200)
        if 'SMA_50' not in df.columns:
            df['SMA_50'] = ta.trend.sma_indicator(df['Close'], window=50)
        if 'ADX' not in df.columns:
            df['ADX'] = ta.trend.adx(df['High'], df['Low'], df['Close'], window=14)
            
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
