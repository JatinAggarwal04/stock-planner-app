import os
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool
from typing import List, Dict, Any
import pandas as pd
import os
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool
from typing import List, Dict, Any
import pandas as pd
import yfinance as yf
import json
from dotenv import load_dotenv

load_dotenv(override=True) # Load backend .env

# Try loading frontend .env or root .env if keys are missing
if not os.getenv("GEMINI_API_KEY") and not os.getenv("VITE_GEMINI_API_KEY"):
    # Try Frontend
    frontend_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', '.env')
    if os.path.exists(frontend_env):
        print(f"Loading fallback .env: {frontend_env}")
        load_dotenv(frontend_env)
        
    # Try Root
    root_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(root_env):
        print(f"Loading fallback .env: {root_env}")
        load_dotenv(root_env)

# Configure API Key
GENAI_API_KEY = os.getenv("VITE_GEMINI_API_KEY")
if GENAI_API_KEY:
    genai.configure(api_key=GENAI_API_KEY)
else:
    print("WARNING: Gemini API Key not found in environment variables!")

class TradeWiseAgent:
    def __init__(self):
        self.model_name = "gemini-2.5-flash-lite"
        
        # Load Knowledge Base
        self.kb = self._load_knowledge_base()
        
        # Define Tools
        self.tools = [
            self.get_stock_price,
            self.get_technical_analysis,
            self.get_trading_plan,
            self.get_news_analysis,
            self.search_knowledge_base
        ]
        
        # Initialize Model with Tools
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            tools=self.tools,
            system_instruction="""You are TradeWise AI, an advanced financial agent.
            
            Your Capability:
            1. You have DIRECT ACCESS to real-time market data, technical analysis, and NEWS via tools.
            2. You have a Knowledge Base for explaining proprietary indicators (Impact Score, Swing Targets).
            
            Protocol:
            - FORMATTING: Use Markdown for all responses.
              - Use `###` for section headers.
              - Use **Tables** for Price Levels, Targets, and Stops.
              - Use **Bold** for signal/action (e.g., **BUY**, **EXIT**).
              - Use bullet points for lists.
            - ALWAYS use the `get_stock_price` tool if a user asks for current price.
            - ALWAYS use `get_technical_analysis` or `get_trading_plan` for analysis questions.
            - ALWAYS use `get_news_analysis` if asked about "News", "Sentiment", or "Events".
            - ALWAYS use `search_knowledge_base` if asked "What is <Term>?" or "How is <Metric> calculated?".
            - RISK MANAGEMENT: If technical stop is too deep (>7%), recommend the '7% Capital Protection Rule' or '5% Conservative Stop'.
            - Do NOT hallucinate data. If a tool fails, admit it.
            - Provide concise, actionable answers.
            
            Disclaimer: Always state "This is not financial advice."
            """
        )
        
        # Active Chats (In-memory for now, can move to Redis/DB later)
        self.chats = {} 

    def _load_knowledge_base(self):
        try:
            with open("knowledge_base.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    # --- Tool Implementations (with Docstrings for Auto-Schema) ---

    def get_stock_price(self, symbol: str):
        """
        Get the current live price and today's change for a given stock symbol.
        
        Args:
            symbol: The stock symbol (e.g., RELIANCE.NS, TATAMOTORS.NS).
        """
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1d')
            if data.empty:
                return {"error": "Stock data not found"}
            
            current = data['Close'].iloc[-1]
            open_price = data['Open'].iloc[-1]
            change = current - open_price
            pct_change = (change / open_price) * 100
            
            return {
                "symbol": symbol,
                "current_price": round(current, 2),
                "change": round(change, 2),
                "change_pct": round(pct_change, 2)
            }
        except Exception as e:
            return {"error": str(e)}

    def get_technical_analysis(self, symbol: str):
        """
        Get comprehensive technical analysis (RSI, Moving Averages, Signals, Trend) for a stock.
        
        Args:
            symbol: The stock symbol to analyze.
        """
        try:
            # Local import to avoid circular dependency
            from main import analyze_stock
            
            # Using default parameters for analysis
            analysis = analyze_stock(symbol)
            # Filter/Summarize large response for the LLM context if needed
            # For now sending full dict but LLM might get overwhelmed. 
            # Ideally we pick key fields.
            return {
                "signal": analysis.get("recommendation", {}).get("signal"),
                "rsi": analysis.get("technical_indicators", {}).get("rsi"),
                "trend": analysis.get("trend"),
                "support_resistance": analysis.get("support_resistance")
            }
        except Exception as e:
            return {"error": str(e)}

    def get_trading_plan(self, symbol: str):
        """
        Get the quantitative trading plan including Intraday Pivots, Swing Targets, and Long Term forecasts.
        
        Args:
            symbol: The stock symbol to get the plan for.
        """
        try:
            from main import analyze_stock
            analysis = analyze_stock(symbol)
            if "trading_plan" in analysis:
                return analysis["trading_plan"]
            return {"error": "No trading plan generated"}
        except Exception as e:
            return {"error": str(e)}

    def get_news_analysis(self, symbol: str):
        """
        Get latest news headlines and AI sentiment analysis (Bullish/Bearish) for a stock.
        
        Args:
            symbol: The stock symbol to analyze (e.g., RELIANCE.NS).
        """
        try:
            from main import fetch_stock_news
            
            # Fetch news
            data = fetch_stock_news(symbol)
            news = data.get('news', [])
            sentiment = data.get('sentiment', {})
            
            # Summarize for Agent
            headlines = [f"- {n['title']}" for n in news[:3]]
            summary = {
                "sentiment_label": sentiment.get('sentiment', 'Neutral'),
                "sentiment_score": sentiment.get('score', 0),
                "top_headlines": headlines
            }
            return summary
        except Exception as e:
            return {"error": f"Failed to fetch news: {str(e)}"}

    def search_knowledge_base(self, query: str):
        """
        Search the proprietary knowledge base for definitions of financial terms or calculation methods used in this app.
        
        Args:
            query: The term or concept to search for (e.g., 'CPR', 'Swing Target', 'Impact Score').
        """
        # Simple keyword matching for retrieval
        query = query.lower()
        results = []
        for key, value in self.kb.items():
            if query in key.lower() or query in value.lower():
                results.append(f"{key}: {value}")
        
        if not results:
            return "No specific definition found in knowledge base. Answer with general knowledge."
        
        return "\n".join(results[:3]) # Return top 3 matches


    # --- Chat Interface ---

    async def chat(self, user_id: str, message: str, context: Dict = None):
        if user_id not in self.chats:
            self.chats[user_id] = self.model.start_chat(enable_automatic_function_calling=True)
        
        chat_session = self.chats[user_id]
        
        # Inject Context if provided
        final_message = message
        if context and "symbol" in context:
            # Format context into a prompt preamble
            context_str = f"""
[SYSTEM CONTEXT]
Active Stock: {context.get('symbol')}
Price: {context.get('current_price')}
Position: {'YES' if context.get('has_position') else 'NO'}
Avg Price: {context.get('buy_price')}
Qty: {context.get('quantity')}
Technical Signal: {context.get('signal')}
"""
            # Add Personality/Action context
            if context.get('personalized_recommendation'):
                 rec = context.get('personalized_recommendation')
                 user_stops = rec.get('user_stops', {})
                 context_str += f"""
RISK ALERT: {rec.get('risk_alert')}
RECOMMENDED ACTION: {rec.get('recommendation', {}).get('action')}
ADVICE: {rec.get('recommendation', {}).get('message')}
USER SPECIFIC STOPS (Based on Buy Price):
- Capital Protection (7%): {user_stops.get('capital_protection_7pct')}
- Conservative (5%): {user_stops.get('conservative_5pct')}
- Aggressive (10%): {user_stops.get('aggressive_10pct')}
"""
            context_str += "[/SYSTEM CONTEXT]\nUser Question: "
            final_message = context_str + message
            
        # Send message with automatic tool handling
        try:
            response = await chat_session.send_message_async(final_message)
            return response.text
        except Exception as e:
            # Handle potential model errors (quota, block, etc.)
            return f"I encountered an error: {str(e)}"

# Singleton Instance
agent = TradeWiseAgent()
