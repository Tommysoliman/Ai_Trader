"""
Custom CrewAI tools for live data access during agent reasoning.
Uses BaseTool (crewai 1.x pattern) instead of @tool decorator.
- SearchFinancialNewsTool: DuckDuckGo search for recent news
- GetStockDataTool: Yahoo Finance price + indicators
"""

import sys
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Type

# Ensure trading_system is on the path when this module is imported standalone
_TS = Path(__file__).parent.parent
if str(_TS) not in sys.path:
    sys.path.insert(0, str(_TS))

from crewai.tools import BaseTool


class _SearchQuery(BaseModel):
    query: str = Field(description="Search query for financial news, e.g. 'NVDA earnings 2024'")


class SearchFinancialNewsTool(BaseTool):
    name: str = "Search Financial News"
    description: str = (
        "Search DuckDuckGo for recent financial news, earnings, analyst ratings, "
        "or any market event related to a stock, sector, or topic. "
        "Use this to find current catalysts, headlines, and sentiment signals. "
        "Input: a search query such as 'NVDA earnings 2024' or 'Fed interest rate decision'."
    )
    args_schema: Type[BaseModel] = _SearchQuery

    def _run(self, query: str) -> str:
        try:
            from utils.duckduckgo_news import get_searcher
            searcher = get_searcher()
            articles = searcher.search_news(query, num_results=8)
            return searcher.format_context_for_agent(articles, max_chars=3000)
        except Exception as e:
            return f"News search failed: {str(e)}"


class _TickerInput(BaseModel):
    ticker: str = Field(description="Stock ticker symbol, e.g. 'NVDA', 'AAPL', 'TSLA'")


class GetStockDataTool(BaseTool):
    name: str = "Get Stock Market Data"
    description: str = (
        "Fetch live technical indicator data for a stock ticker from Yahoo Finance. "
        "Returns current price, RSI, MACD signal, ATR, SMA-200, SMA-50, "
        "whether price is above the 200-day SMA, and recent price change. "
        "Use this to validate technical setup before recommending a trade. "
        "Input: a ticker symbol such as 'NVDA', 'AAPL', or 'TSLA'."
    )
    args_schema: Type[BaseModel] = _TickerInput

    def _run(self, ticker: str) -> str:
        try:
            from analysis.indicators import IndicatorCalculator
            calc = IndicatorCalculator()
            data = calc.calculate_all_indicators(ticker.strip().upper())
            if data is None:
                return f"Could not fetch data for {ticker}. Check the ticker symbol."

            above = "ABOVE" if data["above_200sma"] else "BELOW"
            return (
                f"=== {ticker.upper()} Technical Data ===\n"
                f"Price:        ${data['current_price']}\n"
                f"Change:       {data['price_change_pct']:+.2f}%\n"
                f"RSI(14):      {data['rsi']}\n"
                f"MACD Signal:  {data['macd_cross'].upper()}\n"
                f"ATR(14):      ${data['atr']}\n"
                f"SMA-200:      ${data['sma_200']}\n"
                f"SMA-50:       ${data['sma_50']}\n"
                f"vs 200 SMA:   {above}\n"
                f"Volume:       {data['latest_volume']:,}\n"
                f"RSI Bullish:  {data['rsi_bullish_condition']}\n"
                f"RSI Bearish:  {data['rsi_bearish_condition']}\n"
            )
        except Exception as e:
            return f"Data fetch failed for {ticker}: {str(e)}"


# Instantiated tool objects — imported by agents.py
search_financial_news = SearchFinancialNewsTool()
get_stock_data = GetStockDataTool()
