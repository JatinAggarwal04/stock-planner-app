import os
import json
import logging
from typing import List, Dict, Any, Optional
import yfinance as yf
from dotenv import load_dotenv
from groq import Groq

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(override=True)

# Try loading fallback .envs
if not os.getenv("GROQ_API_KEY"):
    frontend_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', '.env')
    if os.path.exists(frontend_env):
        load_dotenv(frontend_env)
    root_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(root_env):
        load_dotenv(root_env)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    logger.warning("GROQ_API_KEY not found in environment variables!")

class TradeWiseAgent:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model_name = "llama-3.3-70b-versatile" 
        
        # Load Knowledge Base
        self.kb = self._load_knowledge_base()
        
        # Define Tools Schema (OpenAI Compatible)
        self.tools_schema = [
            {
                "type": "function",
                "function": {
                    "name": "get_stock_price",
                    "description": "Get the current live price and today's change for a given stock symbol.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "The stock symbol (e.g., RELIANCE.NS, TATAMOTORS.NS)."}
                        },
                        "required": ["symbol"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_technical_analysis",
                    "description": "Get comprehensive technical analysis (RSI, Moving Averages, Signals, Trend) for a stock.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "The stock symbol to analyze."}
                        },
                        "required": ["symbol"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_trading_plan",
                    "description": "Get the quantitative trading plan including Intraday Pivots, Swing Targets, and Long Term forecasts.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "The stock symbol to get the plan for."}
                        },
                        "required": ["symbol"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_news_analysis",
                    "description": "Get latest news headlines and AI sentiment analysis (Bullish/Bearish) for a stock.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "The stock symbol to analyze."}
                        },
                        "required": ["symbol"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_knowledge_base",
                    "description": "Search the proprietary knowledge base for definitions of financial terms or proprietary metrics.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "The term to search for (e.g., 'CPR', 'Impact Score')."}
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
        
        # Tool Implementation Map
        self.available_tools = {
            "get_stock_price": self.get_stock_price,
            "get_technical_analysis": self.get_technical_analysis,
            "get_trading_plan": self.get_trading_plan,
            "get_news_analysis": self.get_news_analysis,
            "search_knowledge_base": self.search_knowledge_base
        }
        
        # System Prompt
        self.system_prompt = """You are TradeWise AI, an advanced financial agent.
        
        Your Capabilities:
        1. Access real-time market data, technical analysis, and NEWS via tools.
        2. Explain proprietary indicators from your Knowledge Base.
        
        Protocol:
        - FORMATTING: Use Markdown. `###` for headers. **Tables** for data. **Bold** for signals.
        - ALWAYS use `get_stock_price` for current price queries.
        - ALWAYS use `get_technical_analysis` or `get_trading_plan` for analysis.
        - ALWAYS use `search_knowledge_base` for questions about terms like "CPR", "Impact Score", "Swing Targets".
        - RISK: If stops are deep (>7%), recommend 'Capital Protection Rule'.
        - Do NOT hallucinate data.
        
        Disclaimer: State "This is not financial advice."
        """
        
        # Chat History (Simple limitation: 1 turn memory for now to save tokens/simplify)
        # In a real app, you'd store this in a DB or Redis.
        self.history = {}

    def _load_knowledge_base(self):
        try:
            with open("knowledge_base.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    # --- Tool Implementations ---
    def get_stock_price(self, symbol: str):
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1d')
            if data.empty: return json.dumps({"error": "Stock data not found"})
            
            row = data.iloc[-1]
            return json.dumps({
                "symbol": symbol,
                "price": round(row['Close'], 2),
                "change": round(row['Close'] - row['Open'], 2),
                "pct_change": round(((row['Close'] - row['Open']) / row['Open']) * 100, 2)
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    def get_technical_analysis(self, symbol: str):
        try:
            from main import analyze_stock
            analysis = analyze_stock(symbol)
            # Minify for context window
            summary = {
                "signal": analysis.get("recommendation", {}).get("signal"),
                "rsi": analysis.get("technical_analysis", {}).get("rsi"),
                "trend": analysis.get("technical_analysis", {}).get("trend"),
                "support": analysis.get("support_resistance", {}).get("nearest_support"),
                "resistance": analysis.get("support_resistance", {}).get("nearest_resistance")
            }
            return json.dumps(summary)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def get_trading_plan(self, symbol: str):
        try:
            from main import analyze_stock
            analysis = analyze_stock(symbol)
            return json.dumps(analysis.get("trading_plan", {"error": "No plan"}))
        except Exception as e:
            return json.dumps({"error": str(e)})
            
    def get_news_analysis(self, symbol: str):
        try:
            from main import fetch_stock_news
            data = fetch_stock_news(symbol)
            news = data.get('news', [])
            headlines = [n['title'] for n in news[:3]]
            return json.dumps({
                "sentiment": data.get('sentiment', {}).get('sentiment', 'Neutral'),
                "headlines": headlines
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    def search_knowledge_base(self, query: str):
        query = query.lower()
        results = [f"{k}: {v}" for k, v in self.kb.items() if query in k.lower() or query in v.lower()]
        return "\n".join(results[:3]) if results else "No definition found."

    # --- Chat Logic ---
    async def chat(self, user_id: str, message: str, context: Dict = None):
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Inject Context into System Prompt or First User Message
        if context and "symbol" in context:
            ctx_msg = f"""
            Active Stock: {context.get('symbol')}
            Price: {context.get('current_price')}
            Position: {'YES' if context.get('has_position') else 'NO'}
            User Avg: {context.get('buy_price')}
            """
            if context.get('personalized_recommendation'):
                 rec = context.get('personalized_recommendation')
                 ctx_msg += f"\nRisk Alert: {rec.get('risk_alert')}\nRec Action: {rec.get('recommendation', {}).get('action')}"
            
            messages.append({"role": "system", "content": f"Context Data:\n{ctx_msg}"})

        # Add User Message
        messages.append({"role": "user", "content": message})
        
        try:
            # 1. Initial Call
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=self.tools_schema,
                tool_choice="auto",
                max_tokens=1024
            )
            
            response_message = completion.choices[0].message
            tool_calls = response_message.tool_calls
            
            # 2. Handle Tool Calls
            if tool_calls:
                messages.append(response_message) # Extend conversation with assistant's tool request
                
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_to_call = self.available_tools.get(function_name)
                    function_args = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"Invoking Tool: {function_name} with {function_args}")
                    
                    if function_to_call:
                        function_response = function_to_call(**function_args)
                        
                        messages.append(
                            {
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": function_name,
                                "content": str(function_response),
                            }
                        )
                
                # 3. Final Response with Tool Outputs
                second_response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages
                )
                return second_response.choices[0].message.content
            
            return response_message.content

        except Exception as e:
            logger.error(f"Groq Chat Error: {e}")
            return f"Error: {str(e)}. Please check your API usage or key."

agent = TradeWiseAgent()
