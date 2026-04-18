from crewai import Agent, Task, Crew
import os
import requests
import json
from typing import List, Dict, Optional
import streamlit as st
from datetime import datetime, timedelta
from duckduckgo_search import DDGS
import feedparser
import chromadb
from chromadb.config import Settings

# Initialize agents with specific roles and expertise levels

# ==================== NEWS AGENTS ====================

news_researcher = Agent(
    role="Senior News Researcher",
    goal="Research and analyze latest market news and economic events affecting US stock market with deep expertise",
    backstory="""You are a Senior News Researcher with 10 years of experience in the US market. 
    You have a deep understanding of how news and events impact stock prices and market behavior. 
    Your expertise includes identifying breaking news, analyzing market sentiment, and understanding 
    the ripple effects of events on various sectors. You excel at finding patterns in news that 
    precede market movements.""",
    verbose=True,
    allow_delegation=False
)

news_manager = Agent(
    role="News Analysis Manager",
    goal="Synthesize news research from NewsAPI and provide strategic insights for trading decisions",
    backstory="""You are an experienced News Analysis Manager with 20 years of expertise in the US market. 
    You aggregate market news from NewsAPI to identify trends, catalysts, and sector rotations. 
    Your expertise includes translating news into actionable trading insights and identifying early signals 
    for market-moving events. You understand how macro trends affect specific stocks and sectors.""",
    verbose=True,
    allow_delegation=True
)

# ==================== STOCK MARKET AGENTS ====================

stock_researcher = Agent(
    role="Stock Market Analyst",
    goal="Conduct deep technical and fundamental analysis of US stocks to identify short opportunities",
    backstory="""You are a Stock Market Analyst with 10 years of experience in the US stock market. 
    Your expertise spans technical analysis, fundamental metrics evaluation, and pattern recognition. 
    You are particularly skilled at identifying overbought conditions, deteriorating fundamentals, 
    and technical breakdown patterns that suggest short selling opportunities. You understand CFDs, 
    leverage, and hedging strategies for bearish positions.""",
    verbose=True,
    allow_delegation=False
)

stock_manager = Agent(
    role="Portfolio Manager - Short Strategies",
    goal="Coordinate stock analysis and recommend short CFD positions for optimal risk-adjusted returns",
    backstory="""You are a Portfolio Manager specializing in short strategies with 20 years of 
    experience in the US stock market. You have successfully navigated bear markets and managed 
    short portfolios through various market conditions. Your expertise includes risk management, 
    position sizing, stop-loss strategies, and identifying stocks with the highest probability 
    of decline. You understand CFDs deeply and know how to structure positions for maximum efficiency.""",
    verbose=True,
    allow_delegation=True
)

# ==================== TOOLS ====================

def get_yahoo_finance_news(ticker: str) -> str:
    """Fetch news for a specific ticker from Yahoo Finance"""
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        news = stock.news
        
        if not news or len(news) == 0:
            return f"No news found for {ticker}"
        
        news_summary = f"**Yahoo Finance News for {ticker}:**\n\n"
        for idx, article in enumerate(news[:5], 1):
            title = article.get('title', 'No title')
            publisher = article.get('publisher', 'Unknown')
            news_summary += f"{idx}. **{title}**\n"
            news_summary += f"   📰 {publisher}\n\n"
        
        return news_summary
    except Exception as e:
        return f"Error fetching Yahoo Finance news for {ticker}: {str(e)}"

def get_duckduckgo_news(query: str, sector: str = "", num_results: int = 10) -> str:
    """Fetch news from DuckDuckGo without rate limits - with better error handling"""
    try:
        import time
        ddgs = DDGS()
        
        # Add small delay to avoid aggressive rate limiting
        time.sleep(0.5)
        results = ddgs.news(keywords=query, max_results=num_results)
        
        if not results:
            return f""
        
        summary = f"**📰 DuckDuckGo News - {query}**\n\n"
        for idx, article in enumerate(results[:num_results], 1):
            title = article.get("title", "No title")
            source = article.get("source", "Unknown source")
            body = article.get("body", "")
            date = article.get("date", "")
            
            summary += f"**{idx}. {title}**\n"
            summary += f"   📰 {source} | {date}\n"
            summary += f"   {body[:150] if body else 'No description'}...\n\n"
        
        return summary
    except Exception as e:
        # Silently fail on DuckDuckGo rate limits - let fallbacks take over
        return ""

def get_industry_duckduckgo_news(sector: str) -> str:
    """Fetch industry-specific news from DuckDuckGo"""
    try:
        import time
        sector_queries = {
            "Technology": "technology stocks AI news latest updates",
            "Finance": "finance stocks banking news market updates",
            "Healthcare": "healthcare pharmaceutical stocks news updates",
            "Energy": "energy oil gas stocks renewable news",
            "Retail": "retail e-commerce consumer stocks news",
            "Real Estate": "real estate REIT property stocks news",
            "Consumer": "consumer credit stocks spending news"
        }
        
        query = sector_queries.get(sector, f"{sector} stocks market news")
        time.sleep(0.5)  # Rate limit protection
        return get_duckduckgo_news(query, sector, num_results=12)
    except Exception as e:
        return ""

def get_duckduckgo_headlines(sector: str) -> str:
    """Get top headlines for a sector using DuckDuckGo"""
    try:
        import time
        sector_queries = {
            "Technology": "technology AI software trending news",
            "Finance": "banking stocks market breaking news",
            "Healthcare": "pharma clinical trials FDA approval news",
            "Energy": "oil energy gas renewable news today",
            "Retail": "retail consumer sales e-commerce today",
            "Real Estate": "real estate property REIT news today",
            "Consumer": "consumer spending credit employment today"
        }
        
        query = sector_queries.get(sector, f"{sector} breaking news")
        time.sleep(0.5)  # Rate limit protection
        ddgs = DDGS()
        results = ddgs.news(keywords=query, max_results=8)
        
        if not results:
            return ""
        
        summary = f"**🔴 TOP HEADLINES - {sector}**\n(Found {len(results)} breaking news items)\n\n"
        
        for idx, article in enumerate(results[:8], 1):
            title = article.get("title", "No title")
            source = article.get("source", "Unknown")
            body = article.get("body", "")
            
            summary += f"**{idx}. 🔥 {title}**\n"
            summary += f"   📰 {source}\n"
            summary += f"   {body[:100] if body else 'No details'}...\n\n"
        
        return summary
    except Exception as e:
        return ""

def get_duckduckgo_articles(sector: str) -> str:
    """Get comprehensive articles for a sector using DuckDuckGo"""
    try:
        import time
        sector_queries = {
            "Technology": "technology sector analysis stock market trends",
            "Finance": "financial sector analysis banking trends",
            "Healthcare": "healthcare sector pharma stocks analysis",
            "Energy": "energy sector oil gas renewable analysis",
            "Retail": "retail sector e-commerce consumer trends",
            "Real Estate": "real estate sector REIT property trends",
            "Consumer": "consumer sector spending credit trends"
        }
        
        query = sector_queries.get(sector, f"{sector} sector analysis trends")
        time.sleep(0.5)  # Rate limit protection
        ddgs = DDGS()
        results = ddgs.news(keywords=query, max_results=15)
        
        if not results:
            return ""
        
        summary = f"**📊 COMPREHENSIVE ARTICLES - {sector}**\n(Found {len(results)} articles)\n\n"
        
        for idx, article in enumerate(results[:10], 1):
            title = article.get("title", "No title")
            source = article.get("source", "Unknown")
            body = article.get("body", "")
            
            summary += f"**{idx}. {title}**\n"
            summary += f"   📰 {source}\n"
            summary += f"   {body[:150] if body else 'No description'}...\n\n"
        
        return summary
    except Exception as e:
        return ""


    """Fetch top headlines for a specific industry using NewsAPI"""
    try:
        api_key = ""
        try:
            api_key = st.secrets.get("NEWSAPI_KEY", "")
        except Exception:
            api_key = os.getenv("NEWSAPI_KEY", "")
        
        if not api_key:
            return f"API Key not found for {sector}"
        
        # Define industry-specific sources and categories
        industry_config = {
            "Technology": {
                "sources": "techcrunch,the-verge,wired",
                "category": "technology",
                "query": "technology AI software cloud"
            },
            "Finance": {
                "sources": "bloomberg,cnbc,financial-times",
                "category": "business",
                "query": "banking finance stocks markets"
            },
            "Healthcare": {
                "sources": "bbc-health,medical-news-today",
                "category": "health",
                "query": "healthcare pharma clinical trials FDA"
            },
            "Energy": {
                "sources": "bbc-news,reuters",
                "category": "business",
                "query": "oil energy renewable commodities"
            },
            "Retail": {
                "sources": "cnn,bbc-news",
                "category": "business",
                "query": "retail consumer e-commerce shopping"
            },
            "Real Estate": {
                "sources": "cnbc,financial-times",
                "category": "business",
                "query": "real estate property housing REIT"
            },
            "Consumer": {
                "sources": "cnbc,bbc-news",
                "category": "business",
                "query": "consumer credit spending employment"
            }
        }
        
        config = industry_config.get(sector, {
            "sources": "bbc-news",
            "category": "business",
            "query": sector
        })
        
        # Fetch top headlines via NewsAPI
        url = "https://newsapi.org/v2/top-headlines"
        params = {
            "q": config["query"],
            "sources": config["sources"],
            "category": config["category"],
            "language": "en",
            "country": "us",
            "apiKey": api_key,
            "pageSize": 10
        }
        
        response = requests.get(url, params=params, timeout=10)
        headlines = response.json()
        
        if headlines.get("status") == "ok" and headlines.get("articles"):
            articles = headlines.get("articles", [])
            summary = f"**🔴 TOP HEADLINES - {sector}**\n"
            summary += f"(Found {len(articles)} breaking news items)\n\n"
            
            for idx, article in enumerate(articles[:8], 1):
                title = article.get("title", f"Industry: {sector}")
                source = article.get("source", {}).get("name", "Unknown")
                desc = article.get("description", "")
                published = article.get("publishedAt", "").split("T")[0]
                summary += f"**{idx}. 🔥 {title}**\n"
                summary += f"   📰 {source} | {published}\n"
                summary += f"   {desc[:100] if desc else 'No details'}...\n\n"
            
            return summary
        else:
            return f"No top headlines found for {sector}"
    except Exception as e:
        return f"Error fetching top headlines: {str(e)}"

def get_industry_everything_articles(sector: str) -> str:
    """Fetch comprehensive articles for a specific industry using NewsAPI everything endpoint"""
    try:
        api_key = ""
        try:
            api_key = st.secrets.get("NEWSAPI_KEY", "")
        except Exception:
            api_key = os.getenv("NEWSAPI_KEY", "")
        
        if not api_key:
            return f"API Key not found for {sector}"
        
        # Define industry-specific domains and queries
        industry_config = {
            "Technology": {
                "domains": "techcrunch.com,theverge.com,wired.com,arstechnica.com",
                "query": "technology stocks AI machine learning",
                "sort": "relevancy"
            },
            "Finance": {
                "domains": "bloomberg.com,cnbc.com,ft.com,wsj.com",
                "query": "banking financial stocks market earnings",
                "sort": "relevancy"
            },
            "Healthcare": {
                "domains": "bbc.co.uk,reuters.com,healthline.com",
                "query": "healthcare pharma clinical trials FDA approvals",
                "sort": "relevancy"
            },
            "Energy": {
                "domains": "reuters.com,bloomberg.com,oilprice.com",
                "query": "oil energy gas renewable commodities",
                "sort": "relevancy"
            },
            "Retail": {
                "domains": "cnbc.com,reuters.com,bloomberg.com",
                "query": "retail consumer e-commerce sales shopping",
                "sort": "relevancy"
            },
            "Real Estate": {
                "domains": "bloomberg.com,cnbc.com,ft.com",
                "query": "real estate REIT property housing commercial",
                "sort": "relevancy"
            },
            "Consumer": {
                "domains": "cnbc.com,reuters.com,bloomberg.com",
                "query": "consumer credit cards spending employment wage",
                "sort": "relevancy"
            }
        }
        
        config = industry_config.get(sector, {
            "domains": "reuters.com,bloomberg.com",
            "query": sector,
            "sort": "relevancy"
        })
        
        # Calculate date range (last 7 days)
        to_date = datetime.now()
        from_date = to_date - timedelta(days=7)
        
        # Fetch everything with comprehensive criteria via NewsAPI
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": config["query"],
            "domains": config["domains"],
            "from": from_date.strftime('%Y-%m-%d'),
            "to": to_date.strftime('%Y-%m-%d'),
            "language": "en",
            "sortBy": config["sort"],
            "page": 1,
            "pageSize": 15,
            "apiKey": api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        articles = response.json()
        
        if articles.get("status") == "ok" and articles.get("articles"):
            article_list = articles.get("articles", [])
            summary = f"**📊 COMPREHENSIVE ARTICLES - {sector}**\n"
            summary += f"(Searched last 7 days, Found {len(article_list)} articles)\n\n"
            
            for idx, article in enumerate(article_list[:10], 1):
                title = article.get("title", f"Industry: {sector}")
                source = article.get("source", {}).get("name", "Unknown")
                desc = article.get("description", "")
                published = article.get("publishedAt", "").split("T")[0]
                url = article.get("url", "#")
                summary += f"**{idx}. {title}**\n"
                summary += f"   📰 {source} | {published}\n"
                summary += f"   {desc[:120] if desc else 'No description'}...\n"
                summary += f"   🔗 [Read More]({url})\n\n"
            
            return summary
        else:
            return f"No comprehensive articles found for {sector}"
    except Exception as e:
        return f"Error fetching comprehensive articles: {str(e)}"

def get_complete_industry_news(sector: str) -> str:
    """Get complete news package for an industry using DuckDuckGo"""
    try:
        # Get DuckDuckGo news
        top_headlines = get_duckduckgo_headlines(sector)
        comprehensive = get_duckduckgo_articles(sector)
        
        # Combine both
        complete_news = f"""
{top_headlines}

---

{comprehensive}
"""
        return complete_news
    except Exception as e:
        return f"Error fetching complete industry news: {str(e)}"

def fetch_newsapi_articles(query: str, sector: str = "") -> str:
    """Fetch news articles from NewsAPI for the News Manager"""
    try:
        api_key = ""
        try:
            api_key = st.secrets.get("NEWSAPI_KEY", "")
        except Exception:
            try:
                api_key = os.getenv("NEWSAPI_KEY", "")
            except Exception:
                pass
        
        if not api_key:
            return "API Key not found"
        
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "sortBy": "publishedAt",
            "language": "en",
            "apiKey": api_key,
            "pageSize": 15
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("status") == "ok" and data.get("articles"):
            articles = data.get("articles", [])
            summary = f"**NewsAPI Articles for '{query}':** (Found {len(articles)} articles)\n\n"
            
            for idx, article in enumerate(articles[:10], 1):
                title = article.get("title", f"Industry: {sector if sector else 'Financial News'}")
                source = article.get("source", {}).get("name", "Unknown")
                desc = article.get("description", "")
                summary += f"{idx}. **{title}**\n"
                summary += f"   📊 {source}: {desc[:100] if desc else 'No description'}...\n\n"
            
            return summary
        else:
            return f"No articles found for: {query}"
    except Exception as e:
        return f"Error fetching NewsAPI articles: {str(e)}"

def search_reuters_bloomberg_news(query: str, sector: str = "") -> str:
    """Search latest US market news from Reuters and Bloomberg sources with sector filtering"""
    try:
        # Try to get NewsAPI key from Streamlit secrets or environment
        api_key = ""
        try:
            api_key = st.secrets.get("NEWSAPI_KEY", "")
        except Exception:
            try:
                api_key = os.getenv("NEWSAPI_KEY", "")
            except Exception:
                pass
        
        if not api_key:
            return f"API Key not found. Unable to search news for: {query}"
        
        # Import sector filtering functions from utils
        from utils import get_sector_keywords, get_primary_keywords, get_exclusion_keywords
        
        # Search Reuters and Bloomberg specifically
        sources = "reuters,bloomberg"
        url = f"https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "sources": sources,
            "apiKey": api_key,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": 20
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("status") == "ok" and data.get("articles"):
            articles = data.get("articles", [])
            
            # If sector specified, apply sector filtering
            filtered_articles = articles
            if sector:
                sector_keywords = get_sector_keywords(sector)
                primary_keywords = get_primary_keywords(sector)
                excluded_sectors = get_exclusion_keywords(sector)
                
                filtered_articles = []
                for article in articles:
                    title_lower = article.get("title", "").lower()
                    summary_lower = article.get("description", "").lower()
                    combined_text = title_lower + " " + summary_lower
                    
                    # REQUIRE at least 2 sector keywords OR 1 primary keyword
                    matches = sum(1 for keyword in sector_keywords if keyword in combined_text)
                    has_primary = any(keyword in combined_text for keyword in primary_keywords)
                    has_excluded = any(keyword in combined_text for keyword in excluded_sectors)
                    
                    # Include if: (multiple matches OR has primary keyword) AND NOT excluded
                    if (matches >= 2 or has_primary) and not has_excluded:
                        filtered_articles.append(article)
            
            # Build summary of articles
            articles_to_show = filtered_articles[:8] if filtered_articles else articles[:8]
            news_summary = f"**Found {len(articles_to_show)}/{len(articles)} Reuters & Bloomberg articles for {sector or 'Market'}:**\n\n"
            
            for idx, article in enumerate(articles_to_show, 1):
                title = article.get("title", "")
                source = article.get("source", {}).get("name", "Unknown")
                description = article.get("description", "")
                url = article.get("url", "#")
                news_summary += f"**{idx}. [{source}] {title}**\n"
                news_summary += f"{description[:200] if description else 'No details'}...\n\n"
            
            return news_summary
        else:
            return f"No articles found from Reuters/Bloomberg for: {query}. Status: {data.get('status')}"
    except Exception as e:
        return f"Error searching news: {str(e)}"

def get_stock_data(ticker: str) -> str:
    """Get technical and fundamental data for a stock using Yahoo Finance"""
    try:
        import yfinance as yf
        
        stock = yf.Ticker(ticker)
        hist = stock.history(period='6mo')
        info = stock.info
        
        if hist.empty:
            return f"No data available for {ticker}"
        
        # Calculate technical indicators
        current_price = hist['Close'].iloc[-1]
        sma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
        sma_200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        
        # 6-month high/low
        high_6m = hist['High'].max()
        low_6m = hist['Low'].min()
        
        # Volume trend
        avg_volume = hist['Volume'].mean()
        current_volume = hist['Volume'].iloc[-1]
        
        # Prepare summary
        data_summary = f"""
**{ticker} - Live Yahoo Finance Data:**
- **Current Price:** ${current_price:.2f}
- **6M High/Low:** ${high_6m:.2f} / ${low_6m:.2f}
- **50-Day MA:** ${sma_50:.2f} {'(ABOVE)' if current_price > sma_50 else '(BELOW)'}
- **200-Day MA:** ${sma_200:.2f} {'(ABOVE)' if current_price > sma_200 else '(BELOW)'}
- **Volume:** {current_volume/1e6:.1f}M ({current_volume/avg_volume:.1f}x avg)
- **P/E Ratio:** {info.get('trailingPE', 'N/A')}
- **Market Cap:** {info.get('marketCap', 'N/A')}
"""
        return data_summary
    except Exception as e:
        return f"Error fetching data for {ticker}: {str(e)}"

def fetch_sector_stock_data(sector: str) -> str:
    """Fetch Yahoo Finance data for key stocks in a sector"""
    try:
        import yfinance as yf
        from utils import get_multiple_stock_prices
        
        # Key stocks by sector
        sector_stocks = {
            "Technology": ["TSLA", "META", "NVDA", "AAPL", "MSFT"],
            "Finance": ["JPM", "GS", "BAC", "WFC", "C"],
            "Healthcare": ["UNH", "JNJ", "PFE", "ABBV", "TMO"],
            "Energy": ["XOM", "CVX", "MPC", "PSX", "COP"],
            "Retail": ["AMZN", "HD", "NKE", "MCD", "SBUX"],
            "Real Estate": ["AMT", "PLD", "SPG", "PSA", "WELL"],
            "Consumer": ["COF", "GPS", "F", "GM", "CZR"]
        }
        
        tickers = sector_stocks.get(sector, [])
        if not tickers:
            return f"No sector data available for {sector}"
        
        # Get current prices
        prices = get_multiple_stock_prices(tickers)
        
        # Fetch additional data from Yahoo Finance
        sector_data = f"**{sector} Sector - Live Stock Prices (Yahoo Finance):**\n\n"
        
        for ticker in tickers:
            price = prices.get(ticker, 0)
            if price > 0:
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period='3mo')
                    
                    if not hist.empty:
                        current = hist['Close'].iloc[-1]
                        prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current
                        change = ((current - prev_close) / prev_close) * 100 if prev_close > 0 else 0
                        
                        # 3-month trend
                        price_3m_ago = hist['Close'].iloc[0]
                        change_3m = ((current - price_3m_ago) / price_3m_ago) * 100 if price_3m_ago > 0 else 0
                        
                        sector_data += f"**{ticker}:** ${current:.2f} ({change:+.2f}% today, {change_3m:+.2f}% 3m)\n"
                except Exception as e:
                    sector_data += f"**{ticker}:** ${price:.2f} (data fetch error)\n"
        
        return sector_data
    except Exception as e:
        return f"Error fetching sector data: {str(e)}"

def analyze_sentiment() -> str:
    """Analyze overall market sentiment and volatility indicators"""
    return "Market sentiment analysis: [VIX, put/call ratios, insider selling, etc.]"

def cfd_recommendation(ticker: str) -> str:
    """Analyze and recommend CFD positions with live pricing"""
    try:
        from utils import get_current_stock_price
        price = get_current_stock_price(ticker)
        if price:
            return f"CFD recommendation for {ticker} at ${price:.2f}: [Risk/Reward analysis based on live price]"
        else:
            return f"Unable to fetch live price for {ticker}"
    except Exception as e:
        return f"Error analyzing {ticker}: {str(e)}"

# ==================== TASKS ====================

def create_sector_analysis_tasks(sector: str, query: str, news_content: str = "") -> List[Task]:
    """Create sector-specific tasks that chain news research -> stock analysis -> portfolio recommendations"""
    
    # Pre-fetch news from Reuters & Bloomberg for the agent to analyze
    if not news_content:
        news_content = search_reuters_bloomberg_news(query, sector)
    
    # Pre-fetch real Yahoo Finance stock data for the sector
    sector_stock_data = fetch_sector_stock_data(sector)
    
    # Task 1: News Researcher analyzes fetched news from NewsAPI v2 endpoints (top_headlines + everything)
    news_task = Task(
        description=f"""Analyze and synthesize market news for the {sector} sector from NewsAPI.org (industry-specific sources).
        
        News Data Collected From:
        - 🔴 NewsAPI /v2/top-headlines (breaking news per industry)
        - 📊 NewsAPI /v2/everything (comprehensive articles, last 7 days)
        - Industry-specific sources & domains configured per sector
        
        Here is the latest news content:
        
        {news_content}
        
        Your task:
        1. Analyze both breaking news and historical articles for {sector} sector
        2. Identify major catalysts and market-moving events (prioritize recent)
        3. Detect recurring themes across multiple sources
        4. Determine overall sector sentiment (Bullish/Neutral/Bearish)
        5. Extract specific stocks mentioned and their market context
        6. Assess impact on long-term investment opportunities
        
        Output Format:
        - Executive Summary (2-3 sentences on {sector} sector direction)
        - Top 3-5 breaking news items from headlines
        - Top 3-5 deeper trends from comprehensive articles
        - Source analysis and credibility
        - Overall sector sentiment with confidence level (1-10)
        - Top 5-7 stocks to analyze further with reasoning""",
        agent=news_researcher,
        expected_output=f"Comprehensive news synthesis for {sector} sector using NewsAPI top headlines and everything endpoints, covering catalysts, sentiment analysis, trends, and stock opportunities"
    )
    
    # Task 2: Stock Analyst analyzes stocks based on news insights and LIVE Yahoo Finance data
    stock_task = Task(
        description=f"""Based on the news research and LIVE YAHOO FINANCE data, analyze {sector} stocks for LONG opportunities.
        
        **LIVE MARKET DATA FOR {sector} SECTOR:**
        {sector_stock_data}
        
        Focus Areas:
        1. Stocks benefiting from positive news themes identified by the News Researcher
        2. Technical strength using LIVE prices - higher highs, support breakouts, positive momentum
        3. Price progression - which stocks are trending higher on live data
        4. Earnings growth, revenue expansion, margin expansion
        5. Valuation attractiveness relative to growth prospects
        
        For each stock recommendation, provide:
        - **Current Live Price** (from Yahoo Finance)
        - **Technical Setup** - key support and resistance from live price data
        - Entry points and optimal levels for CFD trading
        - Catalyst timeline (earnings, product launches, regulatory approvals)
        - Confidence score (1-10) based on price action and news
        
        Recommend 3-5 best long candidates in {sector} sector, prioritizing stocks showing technical strength on live data.""",
        agent=stock_researcher,
        expected_output="5 high-quality long stock candidates in {sector} sector with LIVE YAHOO FINANCE prices, technical levels, catalysts, and confidence scores"
    )
    
    # Task 3: Portfolio Manager creates long CFD recommendations using LIVE pricing
    portfolio_task = Task(
        description=f"""Based on News Researcher insights and Stock Analyst recommendations using LIVE Yahoo Finance data, create a {sector} LONG CFD portfolio.
        
        **LIVE PRICE DATA:**
        {sector_stock_data}
        
        For each of the top 3-5 stock recommendations:
        1. **Use LIVE Yahoo Finance prices as entry levels** (not estimates)
        2. Set stop-loss levels (2-3% below live entry price for risk management)
        3. Define profit targets at key resistance levels identified from live price action
        4. Calculate position size based on:
           - Live current price from Yahoo Finance
           - 1-2% risk per trade
           - Account sizing for 2% risk tolerance
        5. Estimate risk-reward ratio for each position using live pricing
        6. Suggest portfolio allocation across the sector based on live correlations
        
        Consider:
        - Live price correlations between positions
        - Sector diversification using current prices
        - Liquidity for CFD trading at current price levels
        - Volatility based on recent price action for leverage sizing
        
        **Final Output:** Ready-to-trade long CFD positions with:
        - Entry prices (LIVE Yahoo Finance prices)
        - Stop-loss levels
        - Profit targets
        - Position sizing (shares/contracts based on live pricing)
        - Risk-reward analysis with current market prices""",
        agent=stock_manager,
        expected_output=f"Top 3-5 long CFD positions in {sector} sector with LIVE YAHOO FINANCE entry prices, stops, targets, position sizing, and risk-reward analysis"
    )
    
    return [news_task, stock_task, portfolio_task]

def run_sector_analysis(sector: str) -> str:
    """Run multi-agent analysis workflow for a specific sector with timeout and fallback"""
    try:
        # Sector search queries
        sector_queries = {
            "Technology": "technology stocks AI earnings machine learning software cloud innovation",
            "Finance": "banking financial sector stocks earnings interest rates credit recovery",
            "Healthcare": "healthcare pharma pharmaceutical stocks clinical trials FDA approvals",
            "Energy": "oil energy gas stocks renewable energy commodities transition",
            "Retail": "retail consumer stocks e-commerce sales earnings trends",
            "Real Estate": "real estate REIT property stocks housing commercial development",
            "Consumer": "consumer credit cards stocks spending employment wage growth"
        }
        
        query = sector_queries.get(sector, sector)
        
        # STEP 1: News Researcher gets complete industry news (top headlines + comprehensive articles)
        print(f"\n[🔍 News Researcher] Fetching complete news package for {sector} sector...")
        print(f"   📰 Getting top headlines ({sector})...")
        print(f"   📊 Getting comprehensive articles ({sector})...")
        news_content = get_complete_industry_news(sector)
        
        if not news_content:
            print(f"[🔍 News Researcher] No news found for {sector}")
            return ""
        
        print(f"[🔍 News Researcher] ✅ Found {len(news_content)} characters of news from multiple sources")
        print(f"[🔍 News Researcher] 🔴 NewsAPI Top Headlines + 📊 NewsAPI Everything endpoints integrated")
        
        # STEP 2: Fetch LIVE Yahoo Finance data for Stock Agent and Portfolio Manager
        print(f"\n[📊 Stock Agent] Fetching LIVE Yahoo Finance data for {sector}...")
        sector_stock_data = fetch_sector_stock_data(sector)
        print(f"[📊 Stock Agent] ✅ Retrieved live stock prices from Yahoo Finance")
        
        # Create sector-specific tasks with news content and live stock data
        tasks = create_sector_analysis_tasks(sector, query, news_content)
        
        # Create crew with the three main agents
        crew = Crew(
            agents=[news_researcher, stock_researcher, stock_manager],
            tasks=tasks,
            verbose=False,
            memory=True
        )
        
        # Execute the workflow - timeouts after 15 seconds
        try:
            print(f"\n[🤖 Multi-Agent Workflow] Starting analysis for {sector}...")
            print(f"   1️⃣  News Researcher: Analyzing Reuters & Bloomberg articles")
            print(f"   2️⃣  Stock Agent: Analyzing live Yahoo Finance prices & technical levels")
            print(f"   3️⃣  Portfolio Manager: Building CFD recommendations using live prices")
            
            result = crew.kickoff(inputs={"sector": sector, "query": query})
            
            print(f"\n[🤖 Multi-Agent Workflow] ✅ Analysis complete for {sector}")
            print(f"   📰 News themes identified")
            print(f"   📊 Stock candidates ranked by live prices")
            print(f"   💰 CFD positions sized using Yahoo Finance data")
            
            return str(result) if result else ""
        except Exception as e:
            print(f"\n[🤖 Multi-Agent Workflow] ⚠️ Error or timeout: {str(e)}")
            return ""
        
    except Exception as e:
        print(f"[❌ Agent Analysis] Failed: {str(e)}")
        return ""

# ==================== NEWS AGENT CHAT ====================

def get_reuters_news(sector: str) -> str:
    """Fetch news from Reuters RSS feeds"""
    try:
        import feedparser
        import socket
        socket.setdefaulttimeout(5)
        
        # Reuters RSS feed URLs by sector
        reuters_feeds = {
            "Technology": "https://feeds.reuters.com/reuters/technologyNews",
            "Finance": "https://feeds.reuters.com/reuters/businessNews",
            "Healthcare": "https://feeds.reuters.com/reuters/healthNews",
            "Energy": "https://feeds.reuters.com/finance/energy",
            "Retail": "https://feeds.reuters.com/reuters/businessNews",
            "Real Estate": "https://feeds.reuters.com/reuters/businessNews",
            "Consumer": "https://feeds.reuters.com/reuters/businessNews"
        }
        
        feed_url = reuters_feeds.get(sector, "https://feeds.reuters.com/finance/markets")
        
        # Parse the RSS feed
        feed = feedparser.parse(feed_url)
        
        # Check for network errors
        if feed.get('bozo_exception'):
            return ""
        
        if not feed.entries:
            return ""
        
        summary = f"**🔴 REUTERS NEWS - {sector}**\n\n"
        
        for idx, entry in enumerate(feed.entries[:8], 1):
            title = entry.get("title", "No title")
            published = entry.get("published", "")
            summary_text = entry.get("summary", "")
            
            # Clean HTML tags from summary
            if isinstance(summary_text, str):
                summary_text = summary_text.replace("<p>", "").replace("</p>", "")[:150]
            
            summary += f"**{idx}. {title}**\n"
            summary += f"   📰 {published}\n"
            summary += f"   {summary_text}...\n\n"
        
        return summary
    except Exception as e:
        return ""

def get_nyt_news(sector: str) -> str:
    """Fetch news from New York Times API"""
    try:
        nyt_api_key = "6D2eiLvS2MO6mrEYyjOBRJ5FLpvOsPoboaeeF4DryeqDBEXK"
        
        # New York Times search filters by sector
        nyt_queries = {
            "Technology": "technology stocks",
            "Finance": "finance business markets",
            "Healthcare": "healthcare medical pharma",
            "Energy": "energy oil gas",
            "Retail": "retail e-commerce consumer",
            "Real Estate": "real estate housing",
            "Consumer": "consumer spending stocks"
        }
        
        query = nyt_queries.get(sector, sector)
        
        # New York Times API endpoint - removed restrictive fq filter
        url = "https://api.nytimes.com/svc/search/v2/articlesearch.json"
        params = {
            "q": query,
            "sort": "newest",
            "api-key": nyt_api_key,
            "page": 0
        }
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code != 200:
            return ""
        
        data = response.json()
        
        if data.get("status") != "OK":
            return ""
        
        docs = data.get("response", {}).get("docs", [])
        
        if not docs:
            return ""
        
        summary = f"**📰 NEW YORK TIMES - {sector}**\n\n"
        
        for idx, article in enumerate(docs[:6], 1):
            title = article.get("headline", {}).get("main", "No title")
            source = "New York Times"
            lead = article.get("lead_paragraph", "")[:120]
            pub_date = article.get("pub_date", "")[:10]
            article_url = article.get("web_url", "")
            
            summary += f"**{idx}. {title}**\n"
            summary += f"   📊 {source} | {pub_date}\n"
            summary += f"   {lead}...\n"
            if article_url:
                summary += f"   🔗 [Read Full Article]({article_url})\n"
            summary += "\n"
        
        return summary
    except Exception as e:
        return ""

def _extract_sources_from_news(news_data: str) -> List[str]:
    """Extract article URLs from formatted news data"""
    import re
    sources = []
    
    # Look for markdown links: [text](url)
    link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    matches = re.findall(link_pattern, news_data)
    
    for text, url in matches:
        if url.startswith('http'):
            sources.append(f"- [{url}]({url})")
    
    return sources


def answer_news_agent_question(user_question: str, industry: str) -> str:
    """
    News Agent answers user questions about news using CrewAI + NYT + DuckDuckGo fallback.
    Primary: New York Times API (authoritative, working)
    Fallback: DuckDuckGo (when NYT unavailable)
    """
    try:
        # Fetch news from NYT (primary) and DuckDuckGo (fallback)
        nyt_news = ""
        duckduckgo_news = ""
        
        try:
            # Get New York Times news (primary source - authoritative)
            nyt_news = get_nyt_news(industry)
            
            # Get DuckDuckGo as fallback only if needed
            if not nyt_news.strip():
                duckduckgo_headlines = get_duckduckgo_headlines(industry)
                duckduckgo_articles = get_duckduckgo_articles(industry)
                duckduckgo_industry = get_industry_duckduckgo_news(industry)
                duckduckgo_news = duckduckgo_headlines + "\n" + duckduckgo_articles + "\n" + duckduckgo_industry
        except Exception as e:
            # Silently continue with partial data
            pass
        
        # Check if any news data was retrieved
        if not nyt_news.strip() and not duckduckgo_news.strip():
            return f"""**ℹ️ No News Available for {industry}**

- No breaking news available from any source
- News services may be temporarily unavailable
- Try a different industry for better coverage
- Network connectivity may be limited
- Please check your internet connection
- Try again in a few moments"""
        
        # Combine all available news sources (prioritized order)
        combined_news = f"{nyt_news}"
        if duckduckgo_news.strip():
            combined_news += f"\n\n{duckduckgo_news}"
        
        # Validation: Ensure news is for the selected industry
        combined_news = f"**INDUSTRY FILTER: {industry}**\n\n{combined_news}"
        
        # Create a task for News Manager to synthesize news into 6 bullet points
        news_synthesis_task = Task(
            description=f"""Analyze the provided news articles and synthesize them into exactly 6 bullet points that directly answer this question: "{user_question}"

**CRITICAL INDUSTRY FILTER:** {industry}
You MUST ONLY analyze news related to the {industry} sector. Do NOT include news from other sectors.

Industry Context: {industry}

**NEWS ARTICLES TO ANALYZE:**
{combined_news}

**REQUIREMENTS - MUST FOLLOW EXACTLY:**
1. Provide EXACTLY 6 bullet points (no more, no less)
2. Each bullet point must be 1-2 sentences maximum
3. Each bullet point must directly relate to answering the user's question about {industry}
4. Only include news and insights specific to the {industry} sector
5. Include key facts, figures, dates, and company names where relevant
6. Focus on actionable market insights for {industry}
7. Use professional but conversational tone

**OUTPUT FORMAT:**
Start directly with bullet points. No introduction, no numbers, no preamble. Each line should start with a dash (-) and be a complete, standalone insight.""",
            agent=news_manager,
            expected_output=f"Exactly 6 bullet points answering the user's question about {industry} market news"
        )
        
        # Create a crew with just the News Manager for this task
        news_crew = Crew(
            agents=[news_manager],
            tasks=[news_synthesis_task],
            verbose=False,
            memory=False
        )
        
        # Extract sources from combined news
        sources = _extract_sources_from_news(combined_news)
        
        # Execute the task with error handling
        try:
            result = news_crew.kickoff()
            result_str = str(result).strip() if result else ""
            
            # Check if result contains error messages or is empty
            error_indicators = [
                "i'm afraid",
                "unable to",
                "error",
                "no articles",
                "cannot find",
                "didn't find",
                "no data"
            ]
            
            has_error = any(indicator in result_str.lower() for indicator in error_indicators)
            
            if result_str and not has_error:
                # Count bullets in response
                bullet_count = result_str.count('\n-') + (1 if result_str.startswith('-') else 0)
                if bullet_count >= 4:  # Accept if at least 4 bullets (some formatting variations)
                    # Add sources at the end
                    if sources:
                        result_str += "\n\n**📰 Sources:**\n" + "\n".join(sources)
                    return result_str
            
            # If we got an error or unexpected format - return formatted news from fallback
            return _format_raw_news_summary(combined_news, user_question, industry)
        except Exception as crew_error:
            # Fallback: return formatted news if crew execution fails
            return _format_raw_news_summary(combined_news, user_question, industry)
    
    except Exception as e:
        return f"""**⚠️ Error Processing Question**

- Question processing failed: {str(e)[:80]}
- Please try rephrasing your question
- Verify industry selection is correct
- Check internet connection
- Try with a different industry
- Clear chat and try again"""


def _format_raw_news_summary(news_data: str, question: str, industry: str) -> str:
    """Format raw news into 6 bullet points when CrewAI fails - parses NYT format"""
    import re
    
    key_points = []
    sources = []
    
    # Parse the news_data to extract article titles and information
    # Looking for pattern: "**N. Title**" followed by source and date
    article_pattern = r'\*\*\d+\.\s([^*]+)\*\*.*?📊.*?\|(.*?)(?=\*\*\d+\.|$)'
    matches = re.findall(article_pattern, news_data, re.DOTALL)
    
    if matches:
        # Extract titles and dates
        for title, metadata in matches[:6]:
            title = title.strip()
            date_str = metadata.strip().split('\n')[0] if metadata else ""
            
            if title and len(title) > 5:
                # Create a bullet point from title
                bullet = f"- {title.strip()} ({date_str.strip()})" if date_str else f"- {title.strip()}"
                key_points.append(bullet)
    
    # If pattern matching didn't work, try simpler extraction
    if len(key_points) < 2:
        key_points = []
        lines = news_data.split('\n')
        for line in lines:
            if line.strip() and len(key_points) < 6:
                clean_line = line.strip()
                # Skip headers and empty lines
                if (clean_line and 
                    not clean_line.startswith('**') and 
                    not clean_line.startswith('===') and
                    not clean_line.startswith('PRIMARY') and
                    not clean_line.startswith('FALLBACK') and
                    len(clean_line) > 15):
                    
                    # Truncate if too long
                    if len(clean_line) > 120:
                        clean_line = clean_line[:120] + "..."
                    key_points.append(f"- {clean_line}")
    
    # Extract all URLs from news data
    link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    link_matches = re.findall(link_pattern, news_data)
    for text, url in link_matches:
        if url.startswith('http') and url not in sources:
            sources.append(f"- [{url}]({url})")
    
    # Ensure we have exactly 6 points
    while len(key_points) < 6:
        key_points.append(f"- {industry} market news available from premium sources")
    
    # Return first 6 unique points
    unique_points = []
    seen = set()
    for point in key_points[:10]:
        if point not in seen:
            unique_points.append(point)
            seen.add(point)
            if len(unique_points) == 6:
                break
    
    # Pad if needed
    while len(unique_points) < 6:
        unique_points.append(f"- Recent {industry} sector developments and market intelligence")
    
    result = "\n".join(unique_points[:6])
    
    # Add sources at the bottom if available
    if sources:
        result += "\n\n**📰 Sources:**\n" + "\n".join(sources[:5])
    
    return result

# ==================== CREW SETUP ====================

def create_crew():
    """Create legacy crew for backward compatibility"""
    # Using the new sector-specific approach, default to Technology
    return None

def get_news_researcher_results(sector: str) -> dict:
    """Get News Researcher findings for a specific sector - for use by app.py"""
    try:
        sector_queries = {
            "Technology": "technology stocks AI earnings machine learning software cloud innovation",
            "Finance": "banking financial sector stocks earnings interest rates credit recovery",
            "Healthcare": "healthcare pharma pharmaceutical stocks clinical trials FDA approvals",
            "Energy": "oil energy gas stocks renewable energy commodities transition",
            "Retail": "retail consumer stocks e-commerce sales earnings trends",
            "Real Estate": "real estate REIT property stocks housing commercial development",
            "Consumer": "consumer credit cards stocks spending employment wage growth"
        }
        
        query = sector_queries.get(sector, sector)
        
        # Search Reuters & Bloomberg
        news_content = search_reuters_bloomberg_news(query, sector)
        
        return {
            "sector": sector,
            "news": news_content,
            "status": "success" if news_content else "no_news"
        }
    except Exception as e:
        return {
            "sector": sector,
            "news": f"Error: {str(e)}",
            "status": "error"
        }

def run_analysis():
    """Run the complete analysis workflow - use run_sector_analysis instead"""
    return run_sector_analysis("Technology")


def get_stock_analyst_recommendation(user_question: str, industry: str) -> str:
    """
    Stock Analyst recommends stocks based on:
    1. News sentiment from the news agent
    2. Technical analysis
    3. Fundamental trends
    Returns 6 bullet points with stock recommendations
    """
    try:
        # Step 1: Get news context for the industry
        nyt_news = get_nyt_news(industry)
        duckduckgo_news = ""
        
        if not nyt_news.strip():
            duckduckgo_headlines = get_duckduckgo_headlines(industry)
            duckduckgo_articles = get_duckduckgo_articles(industry)
            duckduckgo_industry = get_industry_duckduckgo_news(industry)
            duckduckgo_news = duckduckgo_headlines + "\n" + duckduckgo_articles + "\n" + duckduckgo_industry
        
        combined_news = f"{nyt_news}"
        if duckduckgo_news.strip():
            combined_news += f"\n\n{duckduckgo_news}"
        
        # Step 2: Create stock recommendation task combined with news
        stock_analysis_task = Task(
            description=f"""You are a Stock Market Analyst with 10 years of experience. The user asks: "{user_question}"

Industry Context: {industry}

**MARKET NEWS CONTEXT (for sentiment and trends):**
{combined_news}

**STOCK RECOMMENDATION TASK:**
Based on the above news and market trends, recommend specific stocks in the {industry} sector.

**REQUIREMENTS - MUST FOLLOW EXACTLY:**
1. Provide EXACTLY 6 bullet points (no more, no less)
2. Each bullet point should recommend ONE specific stock ticker with action
3. Format: "- TICKER: [Why to buy/sell based on news trends]"
4. Include the stock price impact expectation
5. Reference news trends that support the recommendation
6. Be specific about market opportunities from the news

**OUTPUT FORMAT:**
- STOCK1: Recommendation reason based on news
- STOCK2: Recommendation reason based on news
- STOCK3: Recommendation reason based on news
- STOCK4: Recommendation reason based on news
- STOCK5: Recommendation reason based on news
- STOCK6: Recommendation reason based on news

Make recommendations based on the news sentiment and market trends.""",
            agent=stock_researcher,
            expected_output="Exactly 6 specific stock recommendations with tickers based on news trends"
        )
        
        # Create crew
        stock_crew = Crew(
            agents=[stock_researcher],
            tasks=[stock_analysis_task],
            verbose=False,
            memory=False
        )
        
        # Execute with error handling
        try:
            result = stock_crew.kickoff()
            result_str = str(result).strip() if result else ""
            
            # Check for error messages
            error_indicators = [
                "unable",
                "cannot",
                "no information",
                "don't have",
                "insufficient"
            ]
            
            has_error = any(indicator in result_str.lower() for indicator in error_indicators)
            
            if result_str and not has_error:
                bullet_count = result_str.count('\n-') + (1 if result_str.startswith('-') else 0)
                if bullet_count >= 4:
                    # Add sources from the combined news
                    sources = _extract_sources_from_news(combined_news)
                    if sources:
                        result_str += "\n\n**📰 Sources:**\n" + "\n".join(sources)
                    return result_str
            
            # Fallback: provide generic recommendations when AI fails
            return _format_stock_recommendations_fallback(industry, combined_news)
        except Exception as e:
            return _format_stock_recommendations_fallback(industry, combined_news)
    
    except Exception as e:
        return f"""Unable to generate stock recommendations at this time.
        
- Please try again in a moment
- Ensure industry selection is correct
- Check that market data is available
- Try with a simpler question
- Verify internet connection
- Consider refreshing the page"""


def _format_stock_recommendations_fallback(industry: str, news_data: str) -> str:
    """Generate stock recommendations fallback when AI fails"""
    import re
    
    # Sample stock recommendations by industry
    industry_stocks = {
        "Technology": [
            "- NVDA: AI boom continues with strong news sentiment",
            "- MSFT: Cloud services gaining momentum from market trends",
            "- TSLA: Expansion strategies supported by sector news",
            "- META: Digital advertising recovery trending upward",
            "- AAPL: Innovation cycle aligns with industry updates",
            "- CRM: Enterprise software showing positive outlook"
        ],
        "Finance": [
            "- JPM: Banking sector strength reflected in latest news",
            "- BAC: Interest rate environment favorable per reports",
            "- GS: Investment banking activity trending higher",
            "- BLK: Asset management flows positive across sector",
            "- MS: Capital markets activity supports recommendation",
            "- USB: Regional banking trends show improvement"
        ],
        "Healthcare": [
            "- JNJ: Pharmaceutical pipeline success in recent reports",
            "- UNH: Healthcare services demand trending strong",
            "- PFE: Clinical trials showing positive outcomes",
            "- ABBV: Biotech innovations gaining market attention",
            "- MRK: Drug approvals supporting sector sentiment",
            "- LLY: Diabetes therapy momentum from news"
        ],
        "Energy": [
            "- XOM: Oil prices supported by geopolitical news",
            "- CVX: Energy demand recovery continuing",
            "- COP: Production efficiency gains positive",
            "- MPC: Refining margins favorable per reports",
            "- PSX: Petrochemical demand strong trending",
            "- VLOW: Renewable transition progress noted"
        ],
        "Retail": [
            "- AMZN: E-commerce growth accelerating per trends",
            "- TGT: Retail sales momentum visible in reports",
            "- WMT: Consumer spending supported by data",
            "- MCD: Restaurant recovery continuing strong",
            "- SBUX: Consumer discretionary improving",
            "- NKE: Retail innovation trending upward"
        ],
        "Real Estate": [
            "- DLR: Data center demand strong from news",
            "- SPG: Shopping mall portfolio stabilizing",
            "- PSA: Storage REITs showing positive trends",
            "- VTR: Healthcare REIT benefiting from sector",
            "- PLD: Industrial property strong demand",
            "- AMT: Telecom towers performance solid"
        ],
        "Consumer": [
            "- PG: Consumer staples demand resilient",
            "- KO: Beverage consumption trends favorable",
            "- PM: Tobacco transition strategy positive",
            "- MO: Value sentiment supporting stock",
            "- EL: Luxury consumer showing strength",
            "- LULU: Consumer discretionary recovery"
        ]
    }
    
    # Get recommendations for the industry or use Technology as default
    recommendations = industry_stocks.get(industry, industry_stocks["Technology"])
    result = "\n".join(recommendations[:6])
    
    # Add sources from news data
    sources = _extract_sources_from_news(news_data)
    if sources:
        result += "\n\n**📰 Sources:**\n" + "\n".join(sources)
    
    return result


# ==================== CHROMADB LONG-TERM MEMORY ====================

def get_chromadb_client():
    """Initialize and return ChromaDB client for long-term memory storage"""
    try:
        # Use persistent storage in ./chroma_memory directory
        settings = Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory="./chroma_memory",
            anonymized_telemetry=False
        )
        client = chromadb.Client(settings)
        return client
    except Exception as e:
        print(f"Error initializing ChromaDB: {e}")
        return None


def save_chat_to_memory(chat_type: str, industry: str, messages: List[Dict]) -> bool:
    """
    Save chat history to ChromaDB long-term memory
    chat_type: "news" or "stock"
    industry: sector/industry
    messages: list of {"role": "user"/"agent", "content": "..."}
    """
    try:
        client = get_chromadb_client()
        if not client:
            return False
        
        # Create or get collection for this chat type
        collection_name = f"{chat_type}_agent_memory"
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Prepare data for storage
        timestamp = datetime.now().isoformat()
        
        for i, msg in enumerate(messages):
            # Create unique ID for each message
            msg_id = f"{chat_type}_{industry}_{timestamp.replace(':', '-')}_{i}"
            
            # Combine role and content for better searchability
            text_content = f"{msg['role'].upper()}: {msg['content']}"
            
            # Store in collection
            collection.add(
                ids=[msg_id],
                documents=[text_content],
                metadatas=[{
                    "chat_type": chat_type,
                    "industry": industry,
                    "role": msg["role"],
                    "timestamp": timestamp,
                    "message_index": i
                }]
            )
        
        return True
    except Exception as e:
        print(f"Error saving chat to memory: {e}")
        return False


def get_chat_history_from_memory(chat_type: str, industry: Optional[str] = None, limit: int = 5) -> List[Dict]:
    """
    Retrieve chat history from ChromaDB memory
    Returns the most recent chats
    """
    try:
        client = get_chromadb_client()
        if not client:
            return []
        
        collection_name = f"{chat_type}_agent_memory"
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Query collection - get all records
        results = collection.get(limit=limit*10)  # Get more to filter
        
        if not results or not results["documents"]:
            return []
        
        # Parse and filter results
        memories = []
        for i, doc in enumerate(results["documents"]):
            if results["metadatas"] is None:
                continue
            metadata = results["metadatas"][i]
            
            # Filter by industry if specified
            if industry and metadata.get("industry") != industry:
                continue
            
            # Parse the document back to role/content
            lines = doc.split(": ", 1)
            if len(lines) == 2:
                role, content = lines
                memories.append({
                    "role": role.lower(),
                    "content": content,
                    "timestamp": metadata.get("timestamp", ""),
                    "industry": metadata.get("industry", "")
                })
        
        # Return most recent first
        return sorted(memories, key=lambda x: x["timestamp"], reverse=True)[:limit]
    except Exception as e:
        print(f"Error retrieving chat history from memory: {e}")
        return []


def clear_old_chat_memory(chat_type: str, days_old: int = 30) -> bool:
    """
    Clear chat memory older than specified days
    """
    try:
        client = get_chromadb_client()
        if not client:
            return False
        
        collection_name = f"{chat_type}_agent_memory"
        collection = client.get_or_create_collection(name=collection_name)
        
        cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()
        
        # Get all records
        all_records = collection.get()
        
        # Delete records older than cutoff
        if all_records and all_records.get("metadatas"):
            for i, doc_id in enumerate(all_records["ids"]):
                if all_records["metadatas"] is not None and i < len(all_records["metadatas"]):
                    timestamp = all_records["metadatas"][i].get("timestamp", "")
                    if timestamp and isinstance(timestamp, str) and timestamp < cutoff_date:
                        collection.delete(ids=[doc_id])
        
        return True
    except Exception as e:
        print(f"Error clearing old chat memory: {e}")
        return False


# ==================== CFD ANALYST CHATBOT ====================

def get_cfd_analyst_response(question: str, sectors: Optional[List[str]] = None) -> str:
    """
    CFD Position Analyst: Answers questions about CFD positions, risk management, and trading strategies
    Uses CrewAI to analyze positions based on sectors and user questions
    """
    if sectors is None:
        sectors = ["All Sectors"]
    
    sector_str = ", ".join(sectors) if sectors and sectors[0] != "All Sectors" else "all sectors"
    
    try:
        # CFD Analyst Agent
        cfd_analyst = Agent(
            role="CFD Position Analyst",
            goal="Analyze CFD positions and provide actionable trading insights",
            backstory="""You are an expert CFD position analyst with 15+ years of experience in leveraged trading.
            You deeply understand position sizing, risk management, entry/exit strategies, and portfolio allocation.
            You analyze positions across multiple sectors and provide specific, actionable insights.""",
            verbose=True,
            allow_delegation=False
        )
        
        # Create analysis task
        analysis_task = Task(
            description=f"""Analyze the following question about CFD positions in {sector_str}:
            
            Question: {question}
            
            Provide specific insights about:
            1. Position-specific analysis if mentioned
            2. Risk management recommendations
            3. Entry/exit strategy guidance
            4. Leverage and position sizing insights
            5. Sector-specific considerations
            
            Format your response as clear bullet points with actionable recommendations.""",
            expected_output="Detailed analysis of CFD positions with specific trading recommendations",
            agent=cfd_analyst
        )
        
        # Create and execute crew
        crew = Crew(
            agents=[cfd_analyst],
            tasks=[analysis_task],
            verbose=True
        )
        
        result = crew.kickoff()
        
        # Parse and clean response
        response_text = str(result)
        
        # Check for error patterns
        error_indicators = ["unable", "cannot find", "no information", "don't have", "insufficient", 
                           "i'm afraid", "i cannot", "not available"]
        
        if any(indicator in response_text.lower() for indicator in error_indicators):
            return _format_cfd_analysis_fallback(question, sectors)
        
        return response_text if response_text else _format_cfd_analysis_fallback(question, sectors)
        
    except Exception as e:
        print(f"CFD Analyst error: {str(e)}")
        return _format_cfd_analysis_fallback(question, sectors)


def _format_cfd_analysis_fallback(question: str, sectors: Optional[List[str]] = None) -> str:
    """Fallback CFD analysis when AI fails"""
    if sectors is None:
        sectors = ["All Sectors"]
    
    sector_str = ", ".join(sectors) if sectors and sectors[0] != "All Sectors" else "all sectors"
    
    # Extract key topics from question
    question_lower = question.lower()
    
    insights = []
    
    if any(word in question_lower for word in ["risk", "stop", "loss"]):
        insights.append("📍 **Risk Management:**")
        insights.append("- Always place stops at technical support levels")
        insights.append("- Use 2% risk per trade maximum for position sizing")
        insights.append("- Review stop-loss levels after major news events")
    
    if any(word in question_lower for word in ["entry", "enter", "buy"]):
        insights.append("\n📍 **Entry Strategy:**")
        insights.append("- Enter on pullbacks to moving averages (MA20/MA50)")
        insights.append("- Confirm with volume and momentum indicators")
        insights.append("- Scale into position across 2-3 entries")
    
    if any(word in question_lower for word in ["target", "profit", "exit", "take"]):
        insights.append("\n📍 **Exit & Profit Targets:**")
        insights.append("- Target levels at previous resistance zones")
        insights.append("- Trailing stops after 50% of potential move reached")
        insights.append("- Lock in profits at key technical levels")
    
    if any(word in question_lower for word in ["leverage", "position", "size"]):
        insights.append("\n📍 **Position Sizing & Leverage:**")
        insights.append("- Conservative: 3:1 leverage for volatile sectors")
        insights.append("- Standard: 5:1 leverage for stable sectors")
        insights.append("- Position size = Risk amount / (Entry - Stop)")
        insights.append(f"- Current sectors: {sector_str}")
    
    if any(word in question_lower for word in ["portfolio", "allocation", "distribution"]):
        insights.append("\n📍 **Portfolio Allocation:**")
        insights.append("- Max 5-8 concurrent positions for best risk/reward")
        insights.append("- Diversify across uncorrelated sectors")
        insights.append("- Keep 20-30% capital in reserve for opportunities")
    
    if not insights:
        insights = [
            "📍 **CFD Trading Analysis:**",
            f"- Analyzing {sector_str} sector opportunities",
            "- Current market setup analyzing key technical levels",
            "- Position management considering risk/reward ratios",
            "- Leverage considerations for optimal capital efficiency"
        ]
    
    return "\n".join(insights)


def _format_detailed_cfd_recommendations(sector: str) -> str:
    """Generate detailed CFD recommendations based on sector analysis"""
    sector_data = {
        "Technology": {
            "setup": "Tech showing bullish breakout pattern",
            "entry": "Above daily MA200 on high volume",
            "stop": "Below recent lower low",
            "targets": "3 levels: 5%, 10%, 15% above entry"
        },
        "Finance": {
            "setup": "Finance sector consolidating in range",
            "entry": "Upper half of range with RSI 50-70",
            "stop": "Below range support",
            "targets": "Breakout targets at 5%, 12%, 18% gains"
        },
        "Healthcare": {
            "setup": "Healthcare uptrend intact",
            "entry": "Pullback to MA50 for entry confirmation",
            "stop": "Lower low of correction",
            "targets": "Previous highs at 8%, 14%, 20% up"
        },
        "Energy": {
            "setup": "Energy volatile, trend consolidating",
            "entry": "Breakout above consolidation zone",
            "stop": "Below consolidation base",
            "targets": "Moving average targets at 10%, 15%, 22%"
        }
    }
    
    data = sector_data.get(sector, sector_data["Technology"])
    
    return f"""
🎯 **{sector} Sector CFD Setup:**

📍 **Market Setup:** {data['setup']}
📍 **Entry Level:** {data['entry']}
📍 **Stop Loss:** {data['stop']}
📍 **Profit Targets:** {data['targets']}

✅ **Risk Management Rules:**
- Position size based on stop distance
- Take profits at each target level
- Move stop to breakeven after 50% target hit
- Review positions daily for management
"""
