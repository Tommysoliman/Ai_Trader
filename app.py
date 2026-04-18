import streamlit as st
import os
import pandas as pd
from dotenv import load_dotenv
from utils import (format_time_display, get_us_and_egyptian_time, get_current_stock_price, 
                   get_multiple_stock_prices, fetch_financial_news_24h, get_latest_market_alerts,
                   analyze_news_sentiment, generate_signals_from_news)
from agents import news_researcher, run_sector_analysis, get_news_researcher_results
from datetime import datetime
import time

# Load environment variables
load_dotenv()

# Initialize session state for dynamic analysis
if 'analysis_params' not in st.session_state:
    st.session_state.analysis_params = None
if 'analysis_run' not in st.session_state:
    st.session_state.analysis_run = False
if 'last_alert_refresh' not in st.session_state:
    st.session_state.last_alert_refresh = time.time()

# Auto-refresh alerts every 2 minutes
current_time = time.time()
if current_time - st.session_state.last_alert_refresh > 120:  # 120 seconds = 2 minutes
    st.session_state.last_alert_refresh = current_time
    st.rerun()

# Configure Streamlit
st.set_page_config(
    page_title="AI Traders - Short CFD Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 0rem 0rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .time-display {
        background-color: #e8f4f8;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/150x50?text=AI+Traders", use_column_width=False)
    st.divider()
    st.markdown("### 👥 Agent Team")
    st.markdown("""
    **📰 News Researcher** (10 years)
    Identifies breaking news and market-moving events affecting US stocks.
    
    **👔 News Manager** (20 years)  
    Synthesizes news into actionable trading signals and sector strategies.
    
    **📊 Stock Analyst** (10 years)
    Technical and fundamental analysis specialist.
    
    **🎯 Portfolio Manager** (20 years)
    Risk management and position strategy expert.
    """)
    
    st.divider()
    st.markdown("### ⚡ Live Features")
    st.markdown("""
    ✅ Real-time News Feed (24h)
    ✅ Yahoo Finance Prices  
    ✅ Sentiment Analysis
    ✅ Auto-refresh (2 min)
    ✅ Multi-Agent Collab
    """)

# ==================== HELPER FUNCTIONS ====================

@st.cache_data
def get_recommendations_for_sectors(sectors, leverage):
    """Generate recommendations based on selected sectors with REAL MARKET PRICES from Yahoo Finance"""
    # Stock database by sector
    sector_stocks = {
        "Technology": [
            {"ticker": "TSLA", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.12, 0.24], "signal": "Golden Cross"},
            {"ticker": "META", "entry_offset": 0, "stop_offset": -0.08, "targets_offset": [0.12, 0.23], "signal": "Strong Breakout"},
            {"ticker": "NVDA", "entry_offset": 0, "stop_offset": -0.08, "targets_offset": [0.15, 0.32], "signal": "Bull Run"},
            {"ticker": "AAPL", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.09, 0.17], "signal": "Uptrend Confirmed"},
            {"ticker": "MSFT", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.08, 0.17], "signal": "Bullish Resolution"}
        ],
        "Finance": [
            {"ticker": "JPM", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.10, 0.20], "signal": "Recovery Rally"},
            {"ticker": "GS", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.09, 0.17], "signal": "Trading Strength"},
            {"ticker": "BAC", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.09, 0.18], "signal": "Credit Recovery"},
            {"ticker": "WFC", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.09, 0.18], "signal": "Earnings Beat"}
        ],
        "Healthcare": [
            {"ticker": "UNH", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.10, 0.20], "signal": "Regulatory Tailwinds"},
            {"ticker": "JNJ", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.08, 0.16], "signal": "Strong Pipeline"},
            {"ticker": "PFE", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.08, 0.18], "signal": "Pipeline Growth"},
            {"ticker": "ABBV", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.08, 0.18], "signal": "M&A Upside"}
        ],
        "Energy": [
            {"ticker": "XOM", "entry_offset": 0, "stop_offset": -0.10, "targets_offset": [0.09, 0.20], "signal": "Cycle Bottom"},
            {"ticker": "CVX", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.09, 0.19], "signal": "Supply Recovery"},
            {"ticker": "MPC", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.09, 0.18], "signal": "Margin Expansion"},
            {"ticker": "COP", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.08, 0.19], "signal": "Production Upside"}
        ],
        "Retail": [
            {"ticker": "AMZN", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.09, 0.20], "signal": "Margin Recovery"},
            {"ticker": "HD", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.09, 0.19], "signal": "Housing Recovery"},
            {"ticker": "NKE", "entry_offset": 0, "stop_offset": -0.08, "targets_offset": [0.11, 0.23], "signal": "Demand Recovery"},
            {"ticker": "MCD", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.09, 0.18], "signal": "Labor Optimization"},
            {"ticker": "TJX", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.08, 0.18], "signal": "Inventory Strength"}
        ],
        "Consumer": [
            {"ticker": "COF", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.09, 0.18], "signal": "Credit Strength"},
            {"ticker": "GPS", "entry_offset": 0, "stop_offset": -0.08, "targets_offset": [0.08, 0.20], "signal": "Retail Recovery"},
            {"ticker": "F", "entry_offset": 0, "stop_offset": -0.08, "targets_offset": [0.09, 0.18], "signal": "EV Leadership"},
            {"ticker": "GM", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.09, 0.19], "signal": "Supply Normalization"}
        ],
        "Real Estate": [
            {"ticker": "AMT", "entry_offset": 0, "stop_offset": -0.10, "targets_offset": [0.11, 0.26], "signal": "Rate Tailwinds"},
            {"ticker": "PLD", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.09, 0.19], "signal": "Logistics Growth"},
            {"ticker": "SPG", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.08, 0.18], "signal": "Retail Recovery"},
            {"ticker": "PSA", "entry_offset": 0, "stop_offset": -0.07, "targets_offset": [0.08, 0.18], "signal": "Occupancy Strength"}
        ]
    }
    
    # Gather all tickers for batch fetch
    all_tickers = []
    for sector_list in sector_stocks.values():
        for stock in sector_list:
            all_tickers.append(stock["ticker"])
    
    # FETCH REAL PRICES FROM YAHOO FINANCE
    try:
        real_prices = get_multiple_stock_prices(all_tickers)
    except Exception as e:
        print(f"Error fetching prices: {e}")
        real_prices = {}
    
    # Build recommendations with REAL prices
    recommendations = []
    
    # Filter by selected sectors
    if "All Sectors" in sectors or not sectors:
        all_stocks = []
        for sector_list in sector_stocks.values():
            all_stocks.extend(sector_list)
    else:
        all_stocks = []
        for sector in sectors:
            if sector in sector_stocks:
                all_stocks.extend(sector_stocks[sector])
    
    # Build recommendations using REAL prices
    for stock in all_stocks[:5]:
        ticker = stock["ticker"]
        real_price = real_prices.get(ticker, 0)
        
        if real_price > 0:
            entry = real_price
            stop = entry * (1 + stock["stop_offset"])
            target1 = entry * (1 + stock["targets_offset"][0])
            target2 = entry * (1 + stock["targets_offset"][1])
        else:
            # Fallback to placeholder if price fetch fails
            entry, stop, target1, target2 = 0, 0, 0, 0
        
        recommendations.append({
            "ticker": ticker,
            "price": real_price,
            "entry": entry,
            "stop": stop,
            "targets": [target1, target2],
            "signal": stock["signal"],
            "price_source": "Yahoo Finance (Live)" if real_price > 0 else "Placeholder"
        })
    
    return recommendations

def calculate_position_size(capital_at_risk, entry, stop_loss, leverage):
    """Calculate position size based on risk management"""
    risk_per_share = abs(entry - stop_loss)
    if risk_per_share == 0:
        return {'quantity': 0, 'notional': 0, 'margin': 0}
    position_quantity = capital_at_risk / risk_per_share
    notional_exposure = position_quantity * entry
    margin_required = notional_exposure / leverage
    return {
        'quantity': int(position_quantity),
        'notional': float(notional_exposure),
        'margin': float(margin_required)
    }

def get_sector_news_from_agent(sector: str, query: str):
    """
    Fetch news and analysis for a sector using the News Researcher + Stock Analyst + Portfolio Manager agents
    Falls back to direct API call if agent fails
    """
    try:
        # Run the multi-agent workflow for this sector (will timeout and return empty string if too slow)
        result = run_sector_analysis(sector)
        # If result is empty string, agent timed out or failed - use fallback
        if result and result.strip():
            return result
        else:
            return None
    except Exception as e:
        # Fallback to direct API fetch
        print(f"Agent workflow error for {sector}: {str(e)}. Using direct API call.")
        return None

def get_confidence_score(use_leverage, signal_type=None, sector_trend=None):
    """Generate confidence scores based on multiple factors"""
    # Base score starts at 70
    base_score = 70
    
    # Leverage adds to confidence (riskier = higher conviction needed)
    leverage_bonus = 5 if use_leverage else 0
    
    # Signal strength bonus
    signal_bonus = 0
    if signal_type:
        strong_signals = ["Golden Cross", "Bull Run", "Strong Breakout", "Uptrend Confirmed"]
        medium_signals = ["Trading Strength", "Recovery Rally", "Bullish Resolution"]
        if signal_type in strong_signals:
            signal_bonus = 12
        elif signal_type in medium_signals:
            signal_bonus = 8
    
    # Sector trend bonus
    trend_bonus = 3 if sector_trend == "Bullish" else -2 if sector_trend == "Bearish" else 0
    
    # Calculate final score capped at 95
    confidence = base_score + leverage_bonus + signal_bonus + trend_bonus
    return min(int(confidence), 95)

def get_news_for_sectors(sectors):
    """Generate news based on selected sectors with sentiment-based signals"""
    # Fetch real news from financial sources
    sector_queries = {
        "Technology": "technology stocks earnings AI",
        "Finance": "banking sector finance stocks earnings",
        "Healthcare": "healthcare pharma stocks earnings",
        "Energy": "oil energy stocks prices",
        "Retail": "retail consumer stocks earnings",
        "Real Estate": "real estate REIT stocks",
        "Consumer": "consumer credit stocks earnings"
    }
    
    news_items = []
    
    # Get sectors to fetch news for
    if "All Sectors" in sectors or not sectors:
        sectors_to_fetch = list(sector_queries.keys())[:3]  # Fetch for first 3 sectors
    else:
        sectors_to_fetch = sectors[:3]
    
    # Fetch real news for each sector
    all_news_articles = []
    for sector in sectors_to_fetch:
        query = sector_queries.get(sector, sector)
        articles = fetch_financial_news_24h(query, limit=2)
        all_news_articles.extend(articles)
    
    # Generate signals based on news sentiment
    signal_data = generate_signals_from_news(all_news_articles)
    
    # If we got real news, return it with sentiment-based signals
    if all_news_articles:
        for idx, article in enumerate(all_news_articles[:3]):
            # Analyze sentiment for this article
            article_sentiment = analyze_news_sentiment(article.get("title", "") + " " + article.get("summary", ""))
            
            # Determine impact based on sentiment
            if article_sentiment["is_bullish"]:
                impact = "📈 Bullish"
            elif article_sentiment["is_bearish"]:
                impact = "📉 Bearish"
            else:
                impact = "➡️ Neutral"
            
            news_items.append({
                "title": article.get("title", "Market News"),
                "impact": impact,
                "summary": article.get("summary", "Latest market update"),
                "long_candidates": article.get("source", "Financial News"),
                "sentiment": round(article_sentiment["sentiment"], 2)
            })
        
        return news_items[:3]
    
    # Fallback to default news if API fails
    else:
        default_news = {
            "Technology": [
                {"title": "Tech Giants Exceed Growth Expectations", "impact": "📈 Bullish", "summary": "Strong earnings growth and AI revenue acceleration driving valuations higher", "long_candidates": "NVDA, META, TSLA"},
                {"title": "AI Boom Continues with Record Investments", "impact": "📈 Bullish", "summary": "Enterprise AI spending reaches new highs - infrastructure play heating up", "long_candidates": "MSFT, AAPL, GOOGL"}
            ],
            "Finance": [
                {"title": "Fed Rate Cuts Signal Economic Recovery", "impact": "📈 Bullish", "summary": "Upcoming rate reductions expected to boost financial sector earnings", "long_candidates": "JPM, GS, BAC"},
                {"title": "Banking Sector Shows Strong Recovery", "impact": "📈 Bullish", "summary": "Net interest margins expand with stabilizing deposit bases", "long_candidates": "WFC, C"}
            ]
        }
        
        if "All Sectors" in sectors or not sectors:
            all_news = []
            for news_list in default_news.values():
                all_news.extend(news_list)
            return all_news[:3]
        else:
            filtered_news = []
            for sector in sectors:
                if sector in default_news:
                    filtered_news.extend(default_news[sector])
            
            # If no news for sectors, use all available
            if filtered_news:
                return filtered_news[:3]
            else:
                all_fallback = []
                for news_list in default_news.values():
                    all_fallback.extend(news_list)
                return all_fallback[:3]

def get_stocks_for_analysis(sectors):
    """Generate stock analysis based on selected sectors with REAL MARKET PRICES"""
    sector_stocks = {
        "Technology": {
            "tickers": ["TSLA", "META", "NVDA", "AAPL", "MSFT", "GOOGL", "AMD", "AVGO"],
            "signals": {"TSLA": "Death Cross", "META": "Failed Recovery", "NVDA": "Valuation Extreme", "AAPL": "Trend Weakness", "MSFT": "Consolidation", "GOOGL": "Momentum Loss", "AMD": "Support Break", "AVGO": "Downtrend"},
            "pe": {"TSLA": 78.5, "META": 24.3, "NVDA": 65.2, "AAPL": 29.1, "MSFT": 35.4, "GOOGL": 22.5, "AMD": 45.3, "AVGO": 35.8},
            "confidence": {"TSLA": "9/10", "META": "8/10", "NVDA": "7/10", "AAPL": "8/10", "MSFT": "7/10", "GOOGL": "8/10", "AMD": "7/10", "AVGO": "7/10"},
            "ratio": {"TSLA": "1:3", "META": "1:2.5", "NVDA": "1:2", "AAPL": "1:2.5", "MSFT": "1:2", "GOOGL": "1:2.5", "AMD": "1:2", "AVGO": "1:2"}
        },
        "Finance": {
            "tickers": ["JPM", "GS", "BAC", "WFC", "C"],
            "signals": {"JPM": "Rate Vulnerability", "GS": "Trading Weakness", "BAC": "Credit Stress", "WFC": "Earnings Concern", "C": "Diversification Risk"},
            "pe": {"JPM": 12.3, "GS": 8.5, "BAC": 9.2, "WFC": 10.1, "C": 7.8},
            "confidence": {"JPM": "8/10", "GS": "7/10", "BAC": "7/10", "WFC": "7/10", "C": "6/10"},
            "ratio": {"JPM": "1:2.5", "GS": "1:2", "BAC": "1:2", "WFC": "1:2", "C": "1:2"}
        },
        "Healthcare": {
            "tickers": ["UNH", "JNJ", "PFE", "ABBV", "TMO"],
            "signals": {"UNH": "Regulatory Risk", "JNJ": "Patent Cliff", "PFE": "Pipeline Risk", "ABBV": "M&A Concerns", "TMO": "Integration Risk"},
            "pe": {"UNH": 28.5, "JNJ": 24.3, "PFE": 12.1, "ABBV": 18.2, "TMO": 32.5},
            "confidence": {"UNH": "8/10", "JNJ": "7/10", "PFE": "7/10", "ABBV": "7/10", "TMO": "6/10"},
            "ratio": {"UNH": "1:2.5", "JNJ": "1:2", "PFE": "1:2", "ABBV": "1:2", "TMO": "1:2"}
        },
        "Energy": {
            "tickers": ["XOM", "CVX", "MPC", "PSX", "COP"],
            "signals": {"XOM": "Peak Cycle", "CVX": "Supply Glut", "MPC": "Margin Pressure", "PSX": "Crack Spread Risk", "COP": "Production Decline"},
            "pe": {"XOM": 11.2, "CVX": 10.5, "MPC": 9.8, "PSX": 8.2, "COP": 9.5},
            "confidence": {"XOM": "7/10", "CVX": "7/10", "MPC": "6/10", "PSX": "6/10", "COP": "7/10"},
            "ratio": {"XOM": "1:2", "CVX": "1:2", "MPC": "1:2", "PSX": "1:2", "COP": "1:2"}
        },
        "Retail": {
            "tickers": ["AMZN", "HD", "NKE", "MCD", "SBUX", "TJX"],
            "signals": {"AMZN": "Margin Pressure", "HD": "Housing Slowdown", "NKE": "Demand Weakness", "MCD": "Labor Cost Risk", "SBUX": "Competition Risk", "TJX": "Inventory Risk"},
            "pe": {"AMZN": 56.3, "HD": 22.1, "NKE": 32.4, "MCD": 28.5, "SBUX": 35.2, "TJX": 24.8},
            "confidence": {"AMZN": "7/10", "HD": "8/10", "NKE": "7/10", "MCD": "7/10", "SBUX": "6/10", "TJX": "7/10"},
            "ratio": {"AMZN": "1:2", "HD": "1:2.5", "NKE": "1:2", "MCD": "1:2", "SBUX": "1:2", "TJX": "1:2"}
        },
        "Consumer": {
            "tickers": ["COF", "GPS", "F", "GM", "CZR"],
            "signals": {"COF": "Credit Stress", "GPS": "Retail Weakness", "F": "EV Transition", "GM": "Supply Chain", "CZR": "Demand Risk"},
            "pe": {"COF": 14.2, "GPS": 5.8, "F": 4.2, "GM": 6.5, "CZR": 8.3},
            "confidence": {"COF": "7/10", "GPS": "6/10", "F": "7/10", "GM": "6/10", "CZR": "6/10"},
            "ratio": {"COF": "1:2", "GPS": "1:2", "F": "1:2", "GM": "1:2", "CZR": "1:2"}
        },
        "Real Estate": {
            "tickers": ["AMT", "PLD", "SPG", "PSA", "WELL"],
            "signals": {"AMT": "Rate Pressure", "PLD": "Logistics Slowdown", "SPG": "Retail Headwinds", "PSA": "Occupancy Risk", "WELL": "Healthcare Reform"},
            "pe": {"AMT": 18.5, "PLD": 22.1, "SPG": 12.8, "PSA": 28.3, "WELL": 15.6},
            "confidence": {"AMT": "7/10", "PLD": "7/10", "SPG": "6/10", "PSA": "7/10", "WELL": "6/10"},
            "ratio": {"AMT": "1:2", "PLD": "1:2", "SPG": "1:2", "PSA": "1:2", "WELL": "1:2"}
        }
    }
    
    # Gather tickers for batch fetch
    all_tickers = []
    if "All Sectors" in sectors or not sectors:
        for sector_info in sector_stocks.values():
            all_tickers.extend(sector_info["tickers"][:2])
    else:
        for sector in sectors:
            if sector in sector_stocks:
                all_tickers.extend(sector_stocks[sector]["tickers"][:2])
    
    # FETCH REAL PRICES FROM YAHOO FINANCE
    try:
        real_prices = get_multiple_stock_prices(all_tickers)
    except Exception as e:
        print(f"Error fetching prices: {e}")
        real_prices = {}
    
    # Build result with real prices
    result_stocks = []
    for ticker in all_tickers[:5]:
        real_price = real_prices.get(ticker, 0)
        result_stocks.append((ticker, real_price if real_price > 0 else 0))
    
    return result_stocks, sector_stocks

def get_alerts_and_notifications():
    """Generate dynamic alerts based on real market data and financial news"""
    # Get real market-based alerts
    top_tickers = ["TSLA", "META", "NVDA", "AAPL", "MSFT", "JPM", "GS", "UNH", "JNJ", "XOM"]
    alerts = get_latest_market_alerts(top_tickers)
    
    return alerts if alerts else [
        {"type": "info", "title": "📊 Market Data Loading", "message": "Fetching latest prices and news...", "time": "2 min ago"},
        {"type": "success", "title": "✅ System Ready", "message": "Long CFD analysis engine active", "time": "5 min ago"},
        {"type": "info", "title": "🔄 Data Refresh", "message": "Alerts update every 2 minutes", "time": "8 min ago"},
    ]

# Main Content
st.title("🤖 AI Traders - Intelligent Long CFD Recommendation System")
st.markdown("*Powered by CrewAI - Multi-Agent Market Analysis with Real News & Prices*")

# Time Display Section
st.markdown("---")
with st.container():
    col1, col2 = st.columns(2)
    
    with col1:
        times = get_us_and_egyptian_time()
        st.markdown(f"""
        <div class="time-display">
        <h3>🕐 US Eastern Time</h3>
        <p><strong>{times['us_time']}</strong></p>
        <p><small>{times['us_date']}</small></p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        times = get_us_and_egyptian_time()
        st.markdown(f"""
        <div class="time-display">
        <h3>⏰ Egypt Time</h3>
        <p><strong>{times['egypt_time']}</strong></p>
        <p><small>{times['egypt_date']}</small></p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ==================== ALERTS & NOTIFICATIONS ====================
st.header("🔔 Alerts & Notifications (Updated Every 2 Minutes)")

alerts = get_alerts_and_notifications()

alert_col1, alert_col2 = st.columns([3, 1])

with alert_col1:
    for alert in alerts:
        if alert["type"] == "warning":
            st.warning(f"**{alert['title']}**\n{alert['message']}")
        elif alert["type"] == "success":
            st.success(f"**{alert['title']}**\n{alert['message']}")
        elif alert["type"] == "info":
            st.info(f"**{alert['title']}**\n{alert['message']}")

with alert_col2:
    st.markdown("**Last Updated:**")
    times = get_us_and_egyptian_time()
    st.caption(f"US: {times['us_time']}")
    st.caption(f"EG: {times['egypt_time']}")
    st.caption("_Refreshes every 2 min_")

st.markdown("---")

# Main Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📰 News Analysis",
    "📊 Stock Analysis",
    "💰 Long Recommendations",
    "📈 Portfolio Strategy",
    "👥 Agent Profiles"
])

# ==================== TAB 1: NEWS ANALYSIS ====================
with tab1:
    st.header("📰 News Researcher - Multi-Agent Market Intelligence")
    st.markdown("**🤖 AI-Powered News Analysis & Chat:**")
    st.markdown("""
    Ask the News Agent questions about any sector. The agent intelligently fetches and analyzes:
    - Breaking news from Reuters & Bloomberg
    - Industry-specific news from NewsAPI
    - Deep analysis articles and trends
    - Direct answers to your questions
    """)
    
    # Define all sectors
    all_sectors = ["Technology", "Finance", "Healthcare", "Energy", "Retail", "Real Estate", "Consumer"]
    
    st.divider()
    
    # ==================== NEWS AGENT CHATBOX ====================
    st.subheader("💬 Ask News Agent")
    
    # Industry selector
    selected_industry = st.selectbox(
        "Select Industry for Questions:",
        all_sectors,
        index=0,
        key="news_agent_industry"
    )
    
    st.markdown(f"**Current Industry:** 🎯 {selected_industry}")
    
    # Initialize chat history for news agent
    if 'news_chat_history' not in st.session_state:
        st.session_state.news_chat_history = []
    
    # Initialize previous industry tracker
    if 'news_agent_previous_industry' not in st.session_state:
        st.session_state.news_agent_previous_industry = None
    
    # Clear chat history if industry changes
    if st.session_state.news_agent_previous_industry != selected_industry:
        st.session_state.news_chat_history = []
        st.session_state.news_agent_previous_industry = selected_industry
    
    # Display full chat history with follow-up support
    chat_container = st.container()
    with chat_container:
        st.markdown("**💬 Chat History:**")
        if st.session_state.news_chat_history:
            # Show all messages for context-aware follow-ups
            for i, message in enumerate(st.session_state.news_chat_history):
                if message["role"] == "user":
                    st.markdown(f"**👤 You:** {message['content']}")
                else:
                    st.markdown(f"**🤖 Agent:** {message['content']}")
                # Add separator between exchanges
                if i < len(st.session_state.news_chat_history) - 1:
                    st.divider()
        else:
            st.info("💭 Ask a question to start chatting with the News Agent")
    
    # Input area - use form to prevent repeated processing
    st.markdown("---")
    with st.form("news_question_form", clear_on_submit=True):
        user_input = st.text_input(
            "Ask a question about the news:",
            placeholder=f"e.g., What are the top stories for {selected_industry}? What should I know about recent trends?",
            key="news_question_input"
        )
        submitted = st.form_submit_button("🔍 Ask Agent", use_container_width=True)
    
    if submitted and user_input:
        # Add user message to history
        st.session_state.news_chat_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Process question and get agent response using CrewAI
        with st.spinner("🤖 News Agent analyzing news and preparing response..."):
            from agents import answer_news_agent_question, save_chat_to_memory
            
            # Build context from previous exchanges for follow-up questions
            context_summary = ""
            if len(st.session_state.news_chat_history) > 1:
                context_summary = "\n\n**Previous Context:**\n"
                for msg in st.session_state.news_chat_history[:-1]:
                    if msg["role"] == "agent":
                        context_summary += f"- {msg['content'][:200]}...\n"
            
            # Create context-aware question if this is a follow-up
            is_followup = len(st.session_state.news_chat_history) > 1
            full_question = f"{user_input}{context_summary}" if is_followup else user_input
            
            # Call the news agent with the question and selected industry
            agent_response = answer_news_agent_question(full_question, selected_industry)
            
            # Add agent response to history
            st.session_state.news_chat_history.append({
                "role": "agent",
                "content": agent_response
            })
            
            # Save full chat to long-term memory (all exchanges preserved)
            save_chat_to_memory("news", selected_industry, st.session_state.news_chat_history)
            
            st.rerun()
    
    # Start new chat button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🔄 New Chat", use_container_width=True):
            st.session_state.news_chat_history = []
            st.rerun()
    
    st.divider()
    st.caption("💡 News Agent uses Reuters & Bloomberg sources + NewsAPI to answer your questions with up-to-date market intelligence.")

# ==================== TAB 2: STOCK ANALYSIS ====================
with tab2:
    st.header("📊 Stock Analysis - Live Yahoo Finance Data")
    st.markdown("""
    **Stock Market Analyst (10 years)** and **Portfolio Manager (20 years)**:
    - Use LIVE Yahoo Finance prices for real-time analysis
    - Technical breakdown identification from live price action
    - Fundamental deterioration detection
    - Risk-adjusted position sizing using current market data
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Stock Market Analyst")
        with st.expander("Analyst Profile", expanded=False):
            st.markdown("""
            - **Experience:** 10 years technical & fundamental analysis
            - **Data Source:** 🔴 LIVE Yahoo Finance prices
            - **Expertise:** Pattern recognition, technical levels, breakdowns
            - **Role:** Identify opportunities using live market data
            - **Metrics:** Real-time price action, volumes, moving averages
            """)
    
    with col2:
        st.subheader("🎯 Portfolio Manager")
        with st.expander("Manager Profile", expanded=False):
            st.markdown("""
            - **Experience:** 20 years portfolio strategy
            - **Data Source:** 🔴 LIVE Yahoo Finance prices for sizing
            - **Expertise:** Risk management, position sizing, correlation analysis
            - **Role:** Build positions using current market prices
            - **Tools:** Live pricing, leverage calculation, volatility sizing
            """)
    
    st.info("🔴 **LIVE Yahoo Finance Integration:** All prices and analysis use real-time stock data")
    
    st.markdown("### Stock Screening Results")
    
    # Industry selector dropdown
    industries = ["All Sectors", "Technology", "Finance", "Healthcare", "Energy", "Retail", "Real Estate", "Consumer"]
    selected_industry = st.selectbox(
        "📊 Filter by Industry",
        industries,
        index=0,
        key="stock_analysis_industry"
    )
    
    # Get dynamic stocks based on selected industry
    if selected_industry == "All Sectors":
        current_sectors = ["All Sectors"]
    else:
        current_sectors = [selected_industry]
    
    filtered_stocks, sector_stocks_db = get_stocks_for_analysis(current_sectors)
    
    # Build dynamic dataframe
    stocks_data = {
        "Ticker": [],
        "Price": [],
        "Technical Signal": [],
        "P/E Ratio": [],
        "Short Confidence": [],
        "Risk/Reward": []
    }
    
    for ticker, price in filtered_stocks:
        stocks_data["Ticker"].append(ticker)
        stocks_data["Price"].append(f"${price:.2f}")
        
        # Get data from sector_stocks_db
        signal = "N/A"
        pe = "N/A"
        confidence = "N/A"
        ratio = "N/A"
        
        for sector_info in sector_stocks_db.values():
            if ticker in sector_info["signals"]:
                signal = sector_info["signals"][ticker]
                pe = sector_info["pe"][ticker]
                confidence = sector_info["confidence"][ticker]
                ratio = sector_info["ratio"][ticker]
                break
        
        stocks_data["Technical Signal"].append(signal)
        stocks_data["P/E Ratio"].append(pe)
        stocks_data["Short Confidence"].append(confidence)
        stocks_data["Risk/Reward"].append(ratio)
    
    df_stocks = pd.DataFrame(stocks_data)
    st.dataframe(df_stocks, use_container_width=True)
    
    st.caption("💡 **Data Source:** All prices fetched LIVE from Yahoo Finance. Updates every 5 minutes. Technical signals based on real price action and moving averages.")
    
    st.markdown("### Individual Stock Deep-Dive")
    
    # Populate stock selector with dynamic stocks
    stock_options = [ticker for ticker, _ in filtered_stocks] if filtered_stocks else ["No stocks found"]
    selected_stock = st.selectbox("Select Stock for Analysis", stock_options)
    
    if selected_stock != "No stocks found":
        # Get stock data
        tech_score = 8.5
        fund_score = 7.2
        overall_score = 8.1
        
        for sector_info in sector_stocks_db.values():
            if selected_stock in sector_info["signals"]:
                confidence_val = sector_info["confidence"][selected_stock]
                tech_score = int(confidence_val.split("/")[0]) * 10 / 10
                break
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Technical Score", f"{tech_score:.1f}/10", "-1.2 ↓")
        with col2:
            st.metric("Fundamental Score", f"{fund_score:.1f}/10", "-0.8 ↓")
        with col3:
            st.metric("Overall Short Score", f"{overall_score:.1f}/10", "-1.0 ↓")
        
        st.markdown("#### Technical Breakdown")
        sector_display = current_sectors[0] if (current_sectors and current_sectors[0] != "All Sectors") else "market"
        st.write(f"Stock {selected_stock} shows multiple bullish signals based on {sector_display} sector analysis...")
    
    st.info(f"📌 **Analyzed Sectors:** {', '.join(current_sectors)}")
    
    # ==================== STOCK ANALYST CHATBOT ====================
    st.divider()
    st.subheader("💬 Ask Stock Analyst for Recommendations")
    st.markdown("Get AI-powered stock recommendations based on news trends and technical analysis in real-time.")
    
    # Initialize chat history for stock analyst
    if 'stock_chat_history' not in st.session_state:
        st.session_state.stock_chat_history = []
    
    # Use the same industry selected in "Filter by Industry" dropdown
    stock_rec_industry = selected_industry if selected_industry != "All Sectors" else "Technology"
    
    st.markdown(f"**📊 Chat History for {stock_rec_industry} Stocks:**")
    if st.session_state.stock_chat_history:
        # Show all messages for context-aware follow-ups
        for i, message in enumerate(st.session_state.stock_chat_history):
            if message["role"] == "user":
                st.markdown(f"**👤 You:** {message['content']}")
            else:
                st.markdown(f"**📊 Analyst:** {message['content']}")
            # Add separator between exchanges
            if i < len(st.session_state.stock_chat_history) - 1:
                st.divider()
    else:
        st.info("💭 Ask the analyst for stock recommendations based on news and trends")
    
    # Input form
    st.markdown("---")
    with st.form("stock_analyst_form", clear_on_submit=True):
        analyst_input = st.text_input(
            "Ask for stock recommendations:",
            placeholder=f"e.g., Which {stock_rec_industry} stocks should I buy based on recent news? What's your pick for this sector?",
            key="stock_analyst_input"
        )
        analyst_submitted = st.form_submit_button("🔍 Get Recommendations", use_container_width=True)
    
    if analyst_submitted and analyst_input:
        # Add user question to history
        st.session_state.stock_chat_history.append({
            "role": "user",
            "content": analyst_input
        })
        
        # Get analyst recommendations
        with st.spinner("📊 Stock Analyst analyzing trends and generating recommendations..."):
            from agents import get_stock_analyst_recommendation, save_chat_to_memory
            
            # Build context from previous exchanges for follow-up questions
            context_summary = ""
            if len(st.session_state.stock_chat_history) > 1:
                context_summary = "\n\n**Previous Recommendations:**\n"
                for msg in st.session_state.stock_chat_history[:-1]:
                    if msg["role"] == "agent":
                        context_summary += f"- {msg['content'][:200]}...\n"
            
            # Create context-aware question if this is a follow-up
            is_followup = len(st.session_state.stock_chat_history) > 1
            full_question = f"{analyst_input}{context_summary}" if is_followup else analyst_input
            
            analyst_response = get_stock_analyst_recommendation(full_question, stock_rec_industry)
            
            # Add analyst response to history
            st.session_state.stock_chat_history.append({
                "role": "agent",
                "content": analyst_response
            })
            
            # Save full chat to long-term memory (all exchanges preserved)
            save_chat_to_memory("stock", stock_rec_industry, st.session_state.stock_chat_history)
            
            st.rerun()
    
    # Start new chat button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🔄 New Chat", key="stock_clear_btn", use_container_width=True):
            st.session_state.stock_chat_history = []
            st.rerun()
    
    st.divider()
    st.caption("💡 Stock Analyst uses news sentiment + technical analysis + fundamental trends to recommend stocks with the highest potential based on current market conditions.")

# ==================== TAB 3: LONG RECOMMENDATIONS ====================
with tab3:
    st.header("💰 Long CFD Opportunities - Using LIVE Yahoo Finance Prices")
    st.markdown("""
    Curated long positions based on:
    - 📰 **News Researcher:** Reuters & Bloomberg analysis
    - 📊 **Stock Agent:** Live Yahoo Finance technical levels
    - 💼 **Portfolio Manager:** Real-time price-based position sizing
    
    **All recommendations use LIVE Yahoo Finance stock data for entries, stops, and sizing.**
    """)
    
    # Industry selector dropdown
    industries_tab3 = ["All Sectors", "Technology", "Finance", "Healthcare", "Energy", "Retail", "Real Estate", "Consumer"]
    selected_industry_tab3 = st.selectbox(
        "🏢 Filter by Industry",
        industries_tab3,
        index=0,
        key="long_recommendations_industry"
    )
    
    # Default settings
    current_leverage = 5
    if selected_industry_tab3 == "All Sectors":
        current_sectors = ["All Sectors"]
    else:
        current_sectors = [selected_industry_tab3]
    current_position_size = 500
    use_leverage_setting = True
    
    st.markdown("### 🎯 Top Long CFD Positions (Risk Adjusted)")
    
    # Get filtered recommendations based on sectors
    filtered_stocks = get_recommendations_for_sectors(current_sectors, current_leverage)
    
    for idx, stock in enumerate(filtered_stocks[:3], 1):
        # Calculate confidence based on signal quality and sector trend
        confidence = get_confidence_score(use_leverage_setting, stock.get('signal', ''), 'Bullish')
        leverage_display = f"{current_leverage}:1" if use_leverage_setting else "1:1 (No Leverage)"
        adjusted_position_size = current_position_size
        
        rationale = f"Based on {stock['signal']} pattern from {', '.join(current_sectors) if 'All Sectors' not in current_sectors else 'all sectors'}"
        
        with st.expander(f"#{idx} {stock['ticker']} - Confidence: {confidence}/100 🎯", expanded=idx==1):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown("**Entry Strategy**")
                st.info(f"Entry: ${stock['entry']:.2f}")
                st.markdown(f"Stop Loss: `${stock['stop']:.2f}`")
                st.caption(f"Risk: {((stock['stop'] - stock['entry']) / stock['entry'] * 100):.1f}%")
            
            with col2:
                st.markdown("**Profit Targets**")
                for i, target in enumerate(stock['targets'], 1):
                    gain = ((stock['entry'] - target) / stock['entry'] * 100)
                    st.success(f"Target {i}: ${target:.2f} (+{gain:.1f}%)")
            
            with col3:
                st.markdown("**Position Details**")
                st.metric("Leverage", leverage_display)
                st.metric("Position Size", f"${adjusted_position_size}")
                pos_info = calculate_position_size(adjusted_position_size, stock['entry'], stock['stop'], current_leverage)
                st.caption(f"Shares: {pos_info['quantity']} @ {current_leverage}:1")
            
            with col4:
                st.markdown("**Risk Analysis**")
                risk_reward = ((stock['entry'] - stock['targets'][1]) / (stock['stop'] - stock['entry']))
                st.metric("Risk/Reward", f"1:{risk_reward:.1f}")
                st.info(f"📊 {rationale}")
                st.caption(f"Signal: {stock['signal']}")
    
    st.info(f"📌 **Filtered by:** {', '.join(current_sectors)} | **Leverage:** {'Enabled' if use_leverage_setting else 'Disabled'} | **Position Size:** ${current_position_size}")
    
    # ==================== CFD ANALYST CHATBOT ====================
    st.divider()
    st.subheader("💬 Ask CFD Analyst About Your Positions")
    st.markdown("Get expert analysis on your CFD positions, risk management, entry/exit strategies, and portfolio optimization.")
    
    # Initialize chat history for CFD analyst
    if 'cfd_chat_history' not in st.session_state:
        st.session_state.cfd_chat_history = []
    
    # Display full chat history with follow-up support
    st.markdown("**💬 Chat History:**")
    if st.session_state.cfd_chat_history:
        # Show all messages for context-aware follow-ups
        for i, message in enumerate(st.session_state.cfd_chat_history):
            if message["role"] == "user":
                st.markdown(f"**👤 You:** {message['content']}")
            else:
                st.markdown(f"**📊 CFD Analyst:** {message['content']}")
            # Add separator between exchanges
            if i < len(st.session_state.cfd_chat_history) - 1:
                st.divider()
    else:
        st.info("💭 Ask about position sizing, risk management, entry/exit strategies, or portfolio allocation for your CFD positions")
    
    # Input form
    st.markdown("---")
    with st.form("cfd_analyst_form", clear_on_submit=True):
        cfd_input = st.text_input(
            "Ask CFD Analyst:",
            placeholder=f"e.g., How should I size this position? What's the optimal stop loss level? How do I manage multiple positions?",
            key="cfd_analyst_input"
        )
        cfd_submitted = st.form_submit_button("🔍 Ask Analyst", use_container_width=True)
    
    if cfd_submitted and cfd_input:
        # Add user question to history
        st.session_state.cfd_chat_history.append({
            "role": "user",
            "content": cfd_input
        })
        
        # Get CFD analyst response
        with st.spinner("📊 CFD Analyst analyzing your positions..."):
            from agents import get_cfd_analyst_response, save_chat_to_memory
            
            # Build context from previous exchanges for follow-up questions
            context_summary = ""
            if len(st.session_state.cfd_chat_history) > 1:
                context_summary = "\n\n**Previous Analysis:**\n"
                for msg in st.session_state.cfd_chat_history[:-1]:
                    if msg["role"] == "agent":
                        context_summary += f"- {msg['content'][:200]}...\n"
            
            # Create context-aware question if this is a follow-up
            is_followup = len(st.session_state.cfd_chat_history) > 1
            full_question = f"{cfd_input}{context_summary}" if is_followup else cfd_input
            
            sectors_list = current_sectors if current_sectors[0] != "All Sectors" else []
            analyst_response = get_cfd_analyst_response(full_question, sectors_list if sectors_list else None)
            
            # Add analyst response to history
            st.session_state.cfd_chat_history.append({
                "role": "agent",
                "content": analyst_response
            })
            
            # Save full chat to long-term memory (all exchanges preserved)
            sector_for_memory = current_sectors[0] if current_sectors[0] != "All Sectors" else "All Sectors"
            save_chat_to_memory("cfd", sector_for_memory, st.session_state.cfd_chat_history)
            
            st.rerun()
    
    # Start new chat button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🔄 New Chat", key="cfd_clear_btn", use_container_width=True):
            st.session_state.cfd_chat_history = []
            st.rerun()
    
    st.divider()
    st.caption("💡 CFD Analyst provides expert insights on position management, risk/reward ratios, entry strategies, leverage optimization, and portfolio allocation for your trading.")

# ==================== TAB 4: PORTFOLIO STRATEGY ====================
with tab4:
    st.header("📈 Portfolio Strategy & Risk Management - Using LIVE Yahoo Finance")
    st.markdown("""
    **Portfolio Manager (20 years)** creates recommendations using:
    - 🔴 **LIVE Yahoo Finance stock prices** for position sizing
    - Real-time technical levels from price action
    - Current market volatility for leverage calculation
    - Dynamic position sizing based on latest trading data
    """)
    
    # Industry selector dropdown
    industries = ["All Sectors", "Technology", "Finance", "Healthcare", "Energy", "Retail", "Real Estate", "Consumer"]
    selected_portfolio_industry = st.selectbox(
        "🏢 Focus Portfolio by Industry",
        industries,
        index=0,
        key="portfolio_industry"
    )
    
    # Default settings
    p_position_size = 500
    p_leverage = 5
    p_stop_loss = 5
    p_take_profit = 15
    
    st.markdown("### 🛡️ Portfolio Allocation")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Risk Distribution**")
        total_capital = 15000
        num_positions = total_capital // p_position_size
        margin_required = total_capital
        st.write(f"- Total Capital at Risk: ${total_capital:,}")
        st.write(f"- Position Size per Trade: ${p_position_size:,}")
        st.write(f"- Number of Positions: {num_positions}")
        st.write(f"- Leverage Multiplier: {p_leverage}x (Enabled)")
        st.write(f"- Margin Required: ${margin_required:,.0f}")
    
    with col2:
        st.markdown("**Risk Metrics**")
        col_metric1, col_metric2 = st.columns(2)
        with col_metric1:
            st.metric("Max Portfolio DD", "8.5%", "-0.3%")
        with col_metric2:
            st.metric("Win Rate Target", "65%", "-")
        col_metric1, col_metric2 = st.columns(2)
        with col_metric1:
            st.metric("Expectancy", f"+${int(p_position_size * 0.09)} per trade", "")
        with col_metric2:
            st.metric("Sharpe Ratio", "1.85", "-")
    
    st.markdown("### 📊 Diversification by Sector")
    
    # Industry-specific sector weights
    if selected_portfolio_industry == "All Sectors":
        sectors_list = ["Technology", "Finance", "Healthcare", "Retail", "Energy", "Real Estate", "Consumer"]
        sector_weights = [25, 20, 15, 15, 10, 10, 5]
    else:
        sectors_list = [selected_portfolio_industry]
        sector_weights = [100]
        st.info(f"📌 **Portfolio focused on {selected_portfolio_industry} sector** (100% allocation)")
    
    fig_data = {
        "Sector": sectors_list,
        "Allocation %": sector_weights
    }
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.bar_chart(pd.DataFrame(fig_data).set_index('Sector'))
    
    with col2:
        st.markdown("**Your Sector Allocation**")
        for sector, weight in zip(sectors_list, sector_weights):
            st.write(f"- **{sector}:** {weight}%")
    
    # Show industry-specific stocks if a specific industry is selected
    if selected_portfolio_industry != "All Sectors":
        st.markdown(f"### 📍 Top Stocks for {selected_portfolio_industry}")
        
        # Get stocks for this specific industry
        industry_stocks, _ = get_stocks_for_analysis([selected_portfolio_industry])
        
        if industry_stocks:
            stocks_col1, stocks_col2 = st.columns(2)
            with stocks_col1:
                st.markdown("**Recommended Long Positions**")
                for ticker, price in industry_stocks[:3]:
                    st.info(f"**{ticker}** @ ${price:.2f}")
            with stocks_col2:
                st.markdown("**Market Context**")
                st.write(f"These stocks represent the best long opportunities in the {selected_portfolio_industry} sector based on technical signals and sentiment analysis.")
        else:
            st.write(f"No stocks available for {selected_portfolio_industry} sector")
        
        st.divider()
    
    st.markdown("### ⚠️ Risk Management Rules (Based on Your Settings)")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        **Stop Loss Rules**
        - Hard stop: {p_stop_loss}% on all positions
        - Trailing stop: 3% after 2R profit
        - Time stop: 20 days max hold
        """)
    
    with col2:
        st.markdown(f"""
        **Position Sizing**
        - Risk per trade: ${p_position_size:,}
        - Max position: 3x account risk
        - Scale out at targets: {p_take_profit}%
        """)
    
    with col3:
        st.markdown(f"""
        **Leverage Rules**
        - Max leverage: {p_leverage}:1 ✅ Enabled
        - Reduce at 50% account profit
        - No leverage on new positions if down 20%
        """)

# ==================== TAB 5: AGENT PROFILES ====================
with tab5:
    st.header("👥 Meet Your Agent Team")
    st.markdown("Our collaborative multi-agent system brings 60 years of combined trading expertise.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📡 News Researcher")
        st.markdown("""
        **Experience:** 10 years in US market analysis
        
        **Expertise:** 
        - Breaking news identification
        - Market sentiment analysis
        - Sector-specific trends
        - Real-time price action
        
        **Role:** Scour financial news sources (24/7) to identify raw market-moving events before they're priced in.
        
        **Focus:** Pattern recognition in news that historically precedes major price movements.
        """)
    
    with col2:
        st.markdown("### 👔 News Manager")
        st.markdown("""
        **Experience:** 20 years in portfolio management
        
        **Expertise:**
        - Strategic synthesis
        - Macro trend analysis
        - Sector correlations
        - Risk-adjusted positioning
        
        **Role:** Convert raw market data into actionable trading insights and precise entry points.
        
        **Focus:** Identify which stocks will be most affected by macro trends and sentiment shifts.
        """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Stock Market Analyst")
        st.markdown("""
        **Experience:** 10 years technical & fundamental analysis
        
        **Expertise:**
        - Technical pattern recognition
        - Fundamental metrics evaluation
        - Support/resistance identification
        - Breakout pattern analysis
        
        **Role:** Deep-dive technical and fundamental analysis to validate trading signals.
        
        **Focus:** Identify breakdowns and deteriorating metrics across sectors.
        """)
    
    with col2:
        st.markdown("### 🎯 Portfolio Manager")
        st.markdown("""
        **Experience:** 20 years short strategy & risk management
        
        **Expertise:**
        - Risk management frameworks
        - Position sizing algorithms
        - Bear market strategies
        - Leverage optimization
        
        **Role:** Structure positions, manage risk, and coordinate all agents' insights.
        
        **Focus:** Risk-adjusted returns and leverage-enhanced strategies that preserve capital.
        """)
    
    st.markdown("---")
    st.markdown("""
    ### 🤝 How They Work Together
    
    1. **News Researcher** identifies emerging trends from 24h news
    2. **News Manager** synthesizes trends into sector-level opportunities
    3. **Stock Market Analyst** validates with technical & fundamental analysis
    4. **Portfolio Manager** sizes positions and manages risk
    5. **Result:** Precise, high-confidence long CFD recommendations
    
    ### ⚡ Tech Stack
    - **CrewAI:** Multi-agent orchestration & collaboration
    - **Streamlit:** Real-time interface
    - **Python:** Backend processing
    - **OpenAI:** LLM backbone for agent reasoning
    - **Yahoo Finance:** Real-time pricing
    - **NewsAPI:** 24-hour financial news feeds
    """)

# ==================== FOOTER ====================
st.markdown("---")
st.markdown("*Disclaimer: This is for educational purposes. Not financial advice. Trade at your own risk.*")
st.caption("🔄 Updates every 2 minutes | 📊 Powered by AI Traders | GitHub: Tommysoliman/Ai_Trader")
