import os
import re
import json
import math
import asyncio
import logging
from typing import List, Dict, Any, Optional
import yfinance as yf
from dotenv import load_dotenv
from groq import AsyncGroq

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(override=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    logger.warning("GROQ_API_KEY not found in environment variables!")

class TradeWiseAgent:
    def __init__(self):
        # Without a key the rest of the API still runs; chat just reports it's unavailable
        self.client = AsyncGroq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
        self.model_name = "openai/gpt-oss-120b" 
        
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

    def _load_knowledge_base(self):
        try:
            with open("knowledge_base.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    # --- Tool Implementations ---
    async def get_stock_price(self, symbol: str):
        return await asyncio.to_thread(self._get_stock_price, symbol)

    def _get_stock_price(self, symbol: str):
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

    async def get_technical_analysis(self, symbol: str):
        try:
            from main import analyze_stock
            analysis = await analyze_stock(symbol)
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

    async def get_trading_plan(self, symbol: str):
        try:
            from main import analyze_stock
            analysis = await analyze_stock(symbol)
            return json.dumps(analysis.get("trading_plan", {"error": "No plan"}))
        except Exception as e:
            return json.dumps({"error": str(e)})
            
    async def get_news_analysis(self, symbol: str):
        try:
            from main import fetch_stock_news
            data = await fetch_stock_news(symbol)
            news = data.get('news', [])
            headlines = [n['title'] for n in news[:3]]
            return json.dumps({
                "sentiment": data.get('sentiment', {}).get('sentiment', 'Neutral'),
                "headlines": headlines
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    async def search_knowledge_base(self, query: str):
        query = query.lower()
        results = [f"{k}: {v}" for k, v in self.kb.items() if query in k.lower() or query in v.lower()]
        return "\n".join(results[:3]) if results else "No definition found."

    # --- Chat Logic ---
    @staticmethod
    def _context_message(context: Optional[Dict]) -> Optional[str]:
        """Build the context block from whitelisted, type-checked fields only.
        The context comes from the browser, so free text must never reach the system prompt."""
        if not isinstance(context, dict):
            return None
        symbol = context.get('symbol')
        if not isinstance(symbol, str) or not re.fullmatch(r"[A-Za-z0-9.^&-]{1,20}", symbol):
            return None

        def number(value):
            try:
                value = float(value)
            except (TypeError, ValueError):
                return None
            return round(value, 2) if math.isfinite(value) else None

        ctx_msg = (
            f"Active Stock: {symbol.upper()}\n"
            f"Price: {number(context.get('current_price'))}\n"
            f"Position: {'YES' if context.get('has_position') is True else 'NO'}\n"
            f"User Avg: {number(context.get('buy_price'))}"
        )
        rec = context.get('personalized_recommendation')
        if isinstance(rec, dict):
            risk_alert = rec.get('risk_alert')
            action = (rec.get('recommendation') or {}).get('action') if isinstance(rec.get('recommendation'), dict) else None
            if risk_alert in ("CRITICAL", "HIGH", "MODERATE"):
                ctx_msg += f"\nRisk Alert: {risk_alert}"
            if isinstance(action, str) and re.fullmatch(r"[A-Z_]{1,30}", action):
                ctx_msg += f"\nRec Action: {action}"
        return ctx_msg

    async def chat(self, message: str, context: Dict = None):
        if self.client is None:
            return "Sorry, the assistant is unavailable right now. Please try again later."

        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Inject Context into System Prompt
        ctx_msg = self._context_message(context)
        if ctx_msg:
            messages.append({"role": "system", "content": f"Context Data:\n{ctx_msg}"})

        # Add User Message
        messages.append({"role": "user", "content": message})
        
        try:
            # 1. Initial Call
            completion = await self.client.chat.completions.create(
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
                # Send back only the fields Groq accepts on input; the response object also carries
                # output-only fields (reasoning, annotations, executed_tools) that make the follow-up call fail
                messages.append({
                    "role": "assistant",
                    "content": response_message.content or "",
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {"name": tool_call.function.name, "arguments": tool_call.function.arguments},
                        }
                        for tool_call in tool_calls
                    ],
                })
                
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_to_call = self.available_tools.get(function_name)
                    function_args = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"Invoking Tool: {function_name} with {function_args}")
                    
                    if function_to_call:
                        try:
                            function_response = await function_to_call(**function_args)
                        except TypeError as e:  # Model sent unexpected arguments
                            function_response = json.dumps({"error": str(e)})
                        
                        messages.append(
                            {
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": function_name,
                                "content": str(function_response),
                            }
                        )
                
                # 3. Final Response with Tool Outputs
                second_response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages
                )
                return second_response.choices[0].message.content
            
            return response_message.content

        except Exception as e:
            logger.error(f"Groq Chat Error: {e}")
            return "Sorry, the assistant is unavailable right now. Please try again later."

agent = TradeWiseAgent()
