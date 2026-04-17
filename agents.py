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
    goal="Synthesize news research and provide strategic insights for trading decisions",
    backstory="""You are an experienced News Analysis Manager with 20 years of expertise in the US market. 
    You lead a team of researchers and are responsible for translating raw market news into actionable 
    trading insights. Your strategic vision helps identify how macro trends affect specific stocks, 
    especially in identifying short opportunities. You have navigated multiple market cycles and 
    understand both fundamental and technical implications of news events.""",
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

def search_reuters_bloomberg_news(query: str, sector: str = "") -> str:
    """Search latest US market news from Reuters and Bloomberg sources"""
    try:
        # Try to get NewsAPI key from Streamlit secrets or environment
        try:
            api_key = st.secrets["NEWSAPI_KEY"]
        except:
            api_key = os.getenv("NEWSAPI_KEY")
        
        if not api_key:
            return f"API Key not found. Unable to search news for: {query}"
        
        # Search Reuters and Bloomberg specifically
        sources = "reuters,bloomberg"
        url = f"https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "sources": sources,
            "apiKey": api_key,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": 10
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("status") == "ok" and data.get("articles"):
            articles = data.get("articles", [])
            news_summary = f"Found {len(articles)} articles from Reuters and Bloomberg for '{query}':\n\n"
            
            for idx, article in enumerate(articles[:5], 1):
                title = article.get("title", "")
                source = article.get("source", {}).get("name", "Unknown")
                description = article.get("description", "")
                news_summary += f"{idx}. [{source}] {title}\n"
                news_summary += f"   {description[:150]}...\n\n"
            
            return news_summary
        else:
            return f"No articles found from Reuters/Bloomberg for: {query}. Status: {data.get('status')}"
    except Exception as e:
        return f"Error searching news: {str(e)}"

def get_stock_data(ticker: str) -> str:
    """Get technical and fundamental data for a stock"""
    # In production, this would use Alpha Vantage, Finnhub, or similar
    return f"Stock data for {ticker}. [In production, connects to live market data]"

def analyze_sentiment() -> str:
    """Analyze overall market sentiment and volatility indicators"""
    return "Market sentiment analysis: [VIX, put/call ratios, insider selling, etc.]"

def cfd_recommendation(ticker: str) -> str:
    """Analyze and recommend short CFD positions"""
    return f"Short CFD recommendation for {ticker}: [Risk/Reward analysis]"

# ==================== TASKS ====================

def create_sector_analysis_tasks(sector: str, query: str) -> List[Task]:
    """Create sector-specific tasks that chain news research -> stock analysis -> portfolio recommendations"""
    
    # Task 1: News Researcher finds sector news
    news_task = Task(
        description=f"""Search and analyze the latest market news from Reuters and Bloomberg for the {sector} sector.
        
        Search Query: {query}
        
        Functions:
        - Use search_reuters_bloomberg_news() to find recent articles from Reuters and Bloomberg
        - Return 5-10 most relevant articles with titles, sources, and key themes
        - Identify bullish themes, growth catalysts, and positive developments
        - Provide sentiment summary for the {sector} sector
        
        Output Format:
        - List of top news articles by relevance
        - Overall sector sentiment (Bullish/Neutral/Bearish)
        - Key investment themes and catalysts
        - Stocks likely to benefit from current news environment""",
        agent=news_researcher,
        expected_output=f"Detailed news analysis for {sector} sector with 5-10 Reuters/Bloomberg articles, sentiment, and investment themes"
    )
    
    # Task 2: Stock Analyst analyzes stocks based on news insights
    stock_task = Task(
        description=f"""Based on the news research and current market data, analyze {sector} stocks for LONG opportunities.
        
        Focus Areas:
        1. Stocks benefiting from positive news themes identified by the News Researcher
        2. Technical strength (higher highs, support breakouts, positive momentum)
        3. Fundamental improvements (earnings growth, revenue expansion, margin expansion)
        4. Valuation attractiveness relative to growth prospects
        5. Sector leaders with competitive advantages
        
        For each stock, provide:
        - Current price and key technical levels
        - Entry points and resistance levels
        - Catalyst timeline (earnings, product launches, regulatory approvals)
        - Confidence score (1-10)
        
        Recommend 3-5 best long candidates in {sector} sector.""",
        agent=stock_researcher,
        expected_output="5 high-quality long stock candidates in {sector} sector with technical analysis, catalysts, and confidence scores"
    )
    
    # Task 3: Portfolio Manager creates long CFD recommendations
    portfolio_task = Task(
        description=f"""Based on News Researcher insights and Stock Analyst recommendations, create a {sector} LONG CFD portfolio.
        
        For each of the top 3-5 stock recommendations:
        1. Determine optimal CFD entry positions with leverage (1.5x - 3x)
        2. Set stop-loss levels (2-3% below entry for risk management)
        3. Define profit targets at key resistance levels
        4. Calculate position size based on 1-2% risk per trade
        5. Estimate risk-reward ratio for each position
        6. Suggest portfolio allocation across the sector
        
        Consider:
        - Correlation between positions
        - Sector diversification
        - Liquidity for CFD trading
        - Volatility for leverage sizing
        
        Final Output: Ready-to-trade long CFD positions with entry, stop, targets, and sizing""",
        agent=stock_manager,
        expected_output=f"Top 3-5 long CFD positions in {sector} sector with entry prices, stops, targets, position sizing, and risk-reward analysis"
    )
    
    return [news_task, stock_task, portfolio_task]

def run_sector_analysis(sector: str) -> str:
    """Run multi-agent analysis workflow for a specific sector"""
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
        
        # Create sector-specific tasks
        tasks = create_sector_analysis_tasks(sector, query)
        
        # Create crew with the three main agents (news -> stock -> portfolio)
        crew = Crew(
            agents=[news_researcher, stock_researcher, stock_manager],
            tasks=tasks,
            verbose=True,
            memory=True
        )
        
        # Execute the workflow
        result = crew.kickoff(inputs={"sector": sector, "query": query})
        
        # Convert result to string if needed
        return str(result) if result else "Analysis failed to produce output"
    except Exception as e:
        return f"Analysis incomplete: {str(e)}. Please check agent configuration."

# ==================== CREW SETUP ====================

def create_crew():
    """Create legacy crew for backward compatibility"""
    # Using the new sector-specific approach, default to Technology
    return None

def run_analysis():
    """Run the complete analysis workflow - use run_sector_analysis instead"""
    return run_sector_analysis("Technology")
