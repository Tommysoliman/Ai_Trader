from crewai import Agent, Task, Crew, tool
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

@tool("News Database - Reuters and Bloomberg")
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

@tool("Stock Data")
def get_stock_data(ticker: str) -> str:
    """Get technical and fundamental data for a stock"""
    # In production, this would use Alpha Vantage, Finnhub, or similar
    return f"Stock data for {ticker}. [In production, connects to live market data]"

@tool("Market Sentiment")
def analyze_sentiment() -> str:
    """Analyze overall market sentiment and volatility indicators"""
    return "Market sentiment analysis: [VIX, put/call ratios, insider selling, etc.]"

@tool("CFD Analysis")
def cfd_recommendation(ticker: str) -> str:
    """Analyze and recommend short CFD positions"""
    return f"Short CFD recommendation for {ticker}: [Risk/Reward analysis]"

# ==================== TASKS ====================

def create_sector_news_research_task(sector: str, query: str) -> Task:
    """Create a sector-specific news research task"""
    return Task(
        description=f"""Search and analyze the latest market news from Reuters and Bloomberg for the {sector} sector.
        
        Search query: {query}
        
        Use the 'News Database - Reuters and Bloomberg' tool to find:
        1. Recent announcements and earnings updates
        2. Regulatory changes or policy updates affecting {sector}
        3. Industry trends and competitive developments
        4. Company-specific news from major players
        5. Performance analysis and outlook changes
        
        Provide a comprehensive summary of {sector} sector news with specific articles from Reuters and Bloomberg.""",
        agent=news_researcher,
        expected_output=f"5-10 news articles from Reuters and Bloomberg about {sector} sector with titles, sources, and summaries"
    )

def create_tasks():
    """Create tasks for the crew"""
    
    news_research_task = Task(
        description="""Research and analyze the latest market-moving news from the US market using Reuters and Bloomberg sources.
        Focus on:
        1. Major economic indicators and announcements
        2. Corporate earnings misses or warnings
        3. Sector-specific negative developments
        4. Geopolitical events affecting markets
        5. Fed policy decisions and statements
        
        Use the 'News Database - Reuters and Bloomberg' tool to search for news.
        Provide a comprehensive summary of bearish news that could lead to stock declines.""",
        agent=news_researcher,
        expected_output="Detailed analysis of recent market-moving negative news from Reuters and Bloomberg"
    )
    
    news_strategy_task = Task(
        description="""Based on the news research provided, synthesize the information and identify
        which sectors and stock types would be most negatively affected. Recommend patterns or 
        characteristics of stocks that would be good short candidates based on current news environment.""",
        agent=news_manager,
        expected_output="Strategic insights on sectors and stock characteristics for short positions"
    )
    
    stock_analysis_task = Task(
        description="""Conduct detailed technical and fundamental analysis of US stocks looking for
        candidates suitable for short positions. Focus on:
        1. Technical breakdown patterns and support levels
        2. Bearish divergences and momentum indicators
        3. Deteriorating fundamentals and valuation concerns
        4. High short interest and potential squeeze risks
        5. Stocks breaking key support levels
        
        Provide metrics and analysis for 5-10 potential short candidates.""",
        agent=stock_researcher,
        expected_output="List of 5-10 stocks with detailed technical and fundamental analysis for shorting"
    )
    
    portfolio_strategy_task = Task(
        description="""Based on news analysis and stock recommendations, create a short portfolio strategy.
        For the top 3-5 short candidates:
        1. Recommend entry CFD positions with leverage
        2. Suggest stop-loss levels
        3. Define profit-taking targets
        4. Estimate risk-reward ratios
        5. Suggest position sizing for optimal portfolio management
        
        Consider market volatility, liquidity, and correlation between positions.""",
        agent=stock_manager,
        expected_output="Final short CFD recommendations with specific entry points, stops, and targets"
    )
    
    return [news_research_task, news_strategy_task, stock_analysis_task, portfolio_strategy_task]

# ==================== CREW SETUP ====================

def create_crew():
    """Create the crew of agents"""
    tasks = create_tasks()
    
    crew = Crew(
        agents=[news_researcher, news_manager, stock_researcher, stock_manager],
        tasks=tasks,
        verbose=True,
        memory=True
    )
    
    return crew

def run_analysis():
    """Run the complete analysis workflow"""
    crew = create_crew()
    
    result = crew.kickoff(
        inputs={
            "focus": "Identify short CFD opportunities in the US stock market",
            "market_conditions": "Current market volatility and opportunities"
        }
    )
    
    return result
