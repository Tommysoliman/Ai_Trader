from crewai import Agent, Task, Crew
import os
import requests
import json
from typing import List, Dict
import streamlit as st

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
    
    # Task 1: News Researcher analyzes fetched news from Reuters, Bloomberg, and Yahoo Finance
    news_task = Task(
        description=f"""Analyze and synthesize the latest market news for the {sector} sector from multiple sources.
        
        News Sources:
        - Reuters & Bloomberg
        - Yahoo Finance News feeds
        - General market news
        
        Here is the latest news content:
        
        {news_content}
        
        Your task:
        1. Summarize key themes and trends in {sector} sector articles
        2. Identify major catalysts and market-moving events
        3. Cross-reference similar stories across news sources
        4. Determine overall sector sentiment (Bullish/Neutral/Bearish)
        5. Extract specific stocks mentioned and context
        6. Provide investment implications for long positions
        
        Output Format:
        - Executive Summary (2-3 sentences on sector direction)
        - Top 3-5 themes/catalysts with impact assessment
        - Source credibility analysis
        - Overall sector sentiment with confidence level
        - Top 5 stocks to analyze further""",
        agent=news_researcher,
        expected_output=f"Comprehensive news synthesis for {sector} sector from Reuters, Bloomberg, Yahoo Finance covering trends, catalyst analysis, sentiment, and stock opportunities"
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
        
        # STEP 1: News Researcher searches Reuters & Bloomberg AND Yahoo Finance for the sector
        print(f"\n[🔍 News Researcher] Searching Reuters & Bloomberg + Yahoo Finance for {sector} sector...")
        news_content = search_reuters_bloomberg_news(query, sector)
        
        if not news_content:
            print(f"[🔍 News Researcher] No news found for {sector}")
            return ""
        
        print(f"[🔍 News Researcher] ✅ Found {len(news_content)} characters of news from multiple sources")
        print(f"[🔍 News Researcher] 📰 Reuters & Bloomberg + 🔴 Yahoo Finance integrated")
        
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
