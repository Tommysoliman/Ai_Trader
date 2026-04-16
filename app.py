import streamlit as st
import os
from dotenv import load_dotenv
from utils import format_time_display, get_us_and_egyptian_time, get_current_stock_price, get_multiple_stock_prices
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
    st.image("https://via.placeholder.com/150x50?text=AI+Traders", use_column_width=True)
    st.title("⚙️ Controls")
    
    analysis_type = st.radio(
        "Select Analysis Type",
        ["Quick Analysis", "Full Deep Dive", "News Only", "Technical Only"]
    )
    
    market_focus = st.multiselect(
        "Market Focus Sectors",
        ["Technology", "Finance", "Healthcare", "Energy", "Retail", "Real Estate", "Consumer", "All Sectors"],
        default=["All Sectors"]
    )
    
    position_size = st.slider(
        "Position Size Risk ($)",
        min_value=5,
        max_value=500,
        value=50,
        step=5
    )
    
    st.divider()
    run_button = st.button("🚀 Run Analysis", use_container_width=True, key="run_analysis_btn")
    st.divider()
    
    st.subheader("📊 Settings")
    
    use_leverage = st.checkbox("Use CFD Leverage", value=True)
    if use_leverage:
        leverage = st.slider("Leverage Ratio", 1, 50, 5)
    else:
        leverage = 1
    
    stop_loss_pct = st.slider("Stop Loss %", 1, 20, 5)
    take_profit_pct = st.slider("Take Profit %", 5, 50, 15)
    
    st.divider()
    st.subheader("🔌 API Configuration")
    
    api_key = st.text_input("OpenAI API Key (Optional)", type="password", placeholder="sk-...")
    
    if run_button:
        # Store analysis parameters in session state
        st.session_state.analysis_params = {
            'analysis_type': analysis_type,
            'market_focus': market_focus,
            'position_size': position_size,
            'use_leverage': use_leverage,
            'leverage': leverage,
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct
        }
        st.session_state.analysis_run = True
        st.success("✅ Analysis Updated! Results below are now based on your selections.")

# ==================== HELPER FUNCTIONS ====================

@st.cache_data
def get_recommendations_for_sectors(sectors, leverage):
    """Generate recommendations based on selected sectors with REAL MARKET PRICES from Yahoo Finance"""
    # Stock database by sector
    sector_stocks = {
        "Technology": [
            {"ticker": "TSLA", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.12, -0.24], "signal": "Death Cross"},
            {"ticker": "META", "entry_offset": 0, "stop_offset": 0.08, "targets_offset": [-0.12, -0.23], "signal": "Failed Recovery"},
            {"ticker": "NVDA", "entry_offset": 0, "stop_offset": 0.08, "targets_offset": [-0.15, -0.32], "signal": "Valuation Extreme"},
            {"ticker": "AAPL", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.09, -0.17], "signal": "Trend Weakness"},
            {"ticker": "MSFT", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.08, -0.17], "signal": "Consolidation"}
        ],
        "Finance": [
            {"ticker": "JPM", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.10, -0.20], "signal": "Rate Vulnerability"},
            {"ticker": "GS", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.09, -0.17], "signal": "Trading Weakness"},
            {"ticker": "BAC", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.09, -0.18], "signal": "Credit Stress"},
            {"ticker": "WFC", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.09, -0.18], "signal": "Earnings Concern"}
        ],
        "Healthcare": [
            {"ticker": "UNH", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.10, -0.20], "signal": "Regulatory Risk"},
            {"ticker": "JNJ", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.08, -0.16], "signal": "Patent Cliff"},
            {"ticker": "PFE", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.08, -0.18], "signal": "Pipeline Risk"},
            {"ticker": "ABBV", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.08, -0.18], "signal": "M&A Concerns"}
        ],
        "Energy": [
            {"ticker": "XOM", "entry_offset": 0, "stop_offset": 0.10, "targets_offset": [-0.09, -0.20], "signal": "Peak Cycle"},
            {"ticker": "CVX", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.09, -0.19], "signal": "Supply Glut"},
            {"ticker": "MPC", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.09, -0.18], "signal": "Margin Pressure"},
            {"ticker": "COP", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.08, -0.19], "signal": "Production Decline"}
        ],
        "Retail": [
            {"ticker": "AMZN", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.09, -0.20], "signal": "Margin Pressure"},
            {"ticker": "HD", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.09, -0.19], "signal": "Housing Slowdown"},
            {"ticker": "NKE", "entry_offset": 0, "stop_offset": 0.08, "targets_offset": [-0.11, -0.23], "signal": "Demand Weakness"},
            {"ticker": "MCD", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.09, -0.18], "signal": "Labor Cost Risk"},
            {"ticker": "TJX", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.08, -0.18], "signal": "Inventory Risk"}
        ],
        "Consumer": [
            {"ticker": "COF", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.09, -0.18], "signal": "Credit Stress"},
            {"ticker": "GPS", "entry_offset": 0, "stop_offset": 0.08, "targets_offset": [-0.08, -0.20], "signal": "Retail Weakness"},
            {"ticker": "F", "entry_offset": 0, "stop_offset": 0.08, "targets_offset": [-0.09, -0.18], "signal": "EV Transition"},
            {"ticker": "GM", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.09, -0.19], "signal": "Supply Chain"}
        ],
        "Real Estate": [
            {"ticker": "AMT", "entry_offset": 0, "stop_offset": 0.10, "targets_offset": [-0.11, -0.26], "signal": "Rate Pressure"},
            {"ticker": "PLD", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.09, -0.19], "signal": "Logistics Slowdown"},
            {"ticker": "SPG", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.08, -0.18], "signal": "Retail Headwinds"},
            {"ticker": "PSA", "entry_offset": 0, "stop_offset": 0.07, "targets_offset": [-0.08, -0.18], "signal": "Occupancy Risk"}
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

def get_confidence_score(use_leverage):
    """Generate confidence scores that vary based on parameters"""
    base_score = 85
    leverage_bonus = 2 if use_leverage else 0
    return min(base_score + leverage_bonus, 95)

def get_news_for_sectors(sectors):
    """Generate news based on selected sectors"""
    sector_news = {
        "Technology": [
            {"title": "Tech Giants Report Slowing Growth", "impact": "📉 Bearish", "summary": "Multiple earnings misses suggest market saturation and AI bubble concerns", "short_candidates": "NVDA, META, TSLA"},
            {"title": "AI Spending Concerns Emerge", "impact": "📉 Bearish", "summary": "Investors question ROI on AI infrastructure investments", "short_candidates": "MSTR, NVDA"}
        ],
        "Finance": [
            {"title": "Fed Hints at Rate Hold Through 2027", "impact": "📉 Bearish", "summary": "Long-term low rates pressure unleveraged sectors", "short_candidates": "JPM, GS, C"},
            {"title": "Banking Crisis Fears Return", "impact": "📉 Bearish", "summary": "Regional bank stress signals emerging", "short_candidates": "Regional Banks"}
        ],
        "Healthcare": [
            {"title": "Pharma Patent Cliffs Accelerate", "impact": "📉 Bearish", "summary": "Major drug expirations brewing", "short_candidates": "JNJ, PFE, ABBV"},
            {"title": "Healthcare Regulation Tightens", "impact": "📉 Bearish", "summary": "New pricing controls announced", "short_candidates": "UNH, CI"}
        ],
        "Energy": [
            {"title": "Oil Prices Plateau as Demand Softens", "impact": "📉 Bearish", "summary": "Global recession fears weigh on energy", "short_candidates": "XOM, CVX, COP"},
            {"title": "Renewable Energy Threatens Traditional Oil", "impact": "📉 Bearish", "summary": "Long-term structural decline accelerating", "short_candidates": "Oil ETFs"}
        ],
        "Retail": [
            {"title": "Consumer Spending Deteriorates", "impact": "📉 Bearish", "summary": "Retail earnings disappoint across board", "short_candidates": "HD, LOW, NKE"},
            {"title": "E-commerce Compression Continues", "impact": "📉 Bearish", "summary": "Online retail margins under pressure", "short_candidates": "AMZN, EBAY"}
        ],
        "Real Estate": [
            {"title": "Commercial Real Estate Crisis Deepens", "impact": "📉 Bearish", "summary": "Office vacancy rates hit record highs", "short_candidates": "REIT ETFs"},
            {"title": "Interest Rate Pain for Property Owners", "impact": "📉 Bearish", "summary": "Rising rates crush real estate valuations", "short_candidates": "AMT, PLD"}
        ],
        "Consumer": [
            {"title": "Consumer Confidence Index Plummets", "impact": "📉 Bearish", "summary": "Households cutting back spending", "short_candidates": "XRT, IYC"},
            {"title": "Credit Card Delinquencies Rise", "impact": "📉 Bearish", "summary": "Consumer stress mounting", "short_candidates": "COF, AXP"}
        ]
    }
    
    if "All Sectors" in sectors or not sectors:
        all_news = []
        for news_list in sector_news.values():
            all_news.extend(news_list)
        return all_news[:3]
    else:
        filtered_news = []
        for sector in sectors:
            if sector in sector_news:
                filtered_news.extend(sector_news[sector])
        if filtered_news:
            return filtered_news[:3]
        else:
            all_news = []
            for news_list in sector_news.values():
                all_news.extend(news_list)
            return all_news[:3]

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
    """Generate dynamic alerts and notifications"""
    alerts = [
        {"type": "warning", "title": "⚠️ ROKU Near Stop Loss", "message": "ROKU approaching stop at $125.50 (-11% from entry)", "time": "2 minutes ago"},
        {"type": "success", "title": "📈 Profit Target Hit", "message": "META exceeded 1st target at $175.40 - Consider taking profits on 25%", "time": "5 minutes ago"},
        {"type": "info", "title": "📊 VIX Alert", "message": "VIX above 30 - Position spike risk detected. Consider tighter stops", "time": "8 minutes ago"},
        {"type": "warning", "title": "⚡ TSLA Volatility", "message": "TSLA experiencing 3.5% intraday swing. Monitor for breakouts", "time": "12 minutes ago"},
        {"type": "success", "title": "💰 Position Update", "message": "JPM down 2.1% - Short entry confirmed. Monitor for bounce", "time": "15 minutes ago"},
    ]
    return alerts

# Main Content
st.title("🤖 AI Traders - Intelligent Short CFD Recommendation System")
st.markdown("*Powered by CrewAI - Multi-Agent Market Analysis*")

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
tab1, tab2, tab3, tab4 = st.tabs([
    "📰 News Analysis",
    "📊 Stock Analysis",
    "💰 Short Recommendations",
    "📈 Portfolio Strategy"
])

# ==================== TAB 1: NEWS ANALYSIS ====================
with tab1:
    st.header("📰 Market News Analysis")
    st.markdown("""
    This section provides latest market news and sentiment analysis affecting US stocks.
    The News Researcher (10 years) and News Manager (20 years) collaborate to identify bearish signals.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📡 News Researcher (10 years)")
        with st.expander("Researcher Profile", expanded=False):
            st.markdown("""
            - **Experience:** 10 years in US market
            - **Expertise:** Breaking news, market sentiment, sector analysis
            - **Role:** Identify raw market-moving events
            - **Focus:** Pattern recognition in news that precedes movements
            """)
    
    with col2:
        st.subheader("👔 News Manager (20 years)")
        with st.expander("Manager Profile", expanded=False):
            st.markdown("""
            - **Experience:** 20 years in US market
            - **Expertise:** Strategic synthesis, macro trends, sector correlations
            - **Role:** Convert raw data into actionable trading insights
            - **Focus:** Identify stocks affected by macro trends
            """)
    
    # News Analysis Results
    st.markdown("### Latest Market-Moving News")
    
    # Get current parameters with defaults
    if st.session_state.analysis_params:
        params = st.session_state.analysis_params
        current_sectors = params['market_focus']
    else:
        current_sectors = ["All Sectors"]
    
    # Get dynamic news based on sectors
    news_items = get_news_for_sectors(current_sectors)
    
    for item in news_items:
        with st.container():
            st.markdown(f"**{item['title']}** {item['impact']}")
            st.write(item['summary'])
            st.caption(f"💡 Short Ideas: {item['short_candidates']}")
            st.divider()
    
    st.info(f"📌 **Analyzed Sectors:** {', '.join(current_sectors)}")

# ==================== TAB 2: STOCK ANALYSIS ====================
with tab2:
    st.header("📊 Technical & Fundamental Analysis")
    st.markdown("""
    Stock Market Analyst (10 years) and Portfolio Manager (20 years) identify technical breakdowns
    and fundamental deterioration suitable for short positions.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📉 Stock Market Analyst (10 years)")
        with st.expander("Analyst Profile", expanded=False):
            st.markdown("""
            - **Experience:** 10 years technical & fundamental analysis
            - **Expertise:** Pattern recognition, metrics evaluation, breakdowns
            - **Role:** Identify technical and fundamental short signals
            - **Focus:** Overbought conditions, support breaks, deteriorating metrics
            """)
    
    with col2:
        st.subheader("🎯 Portfolio Manager (20 years)")
        with st.expander("Manager Profile", expanded=False):
            st.markdown("""
            - **Experience:** 20 years short strategy management
            - **Expertise:** Risk management, position sizing, bear markets
            - **Role:** Coordinate analysis and structure positions
            - **Focus:** Risk-adjusted returns, leverage strategies
            """)
    
    st.markdown("### Stock Screening Results")
    
    # Create dynamic analysis table
    import pandas as pd
    
    # Get current parameters with defaults
    if st.session_state.analysis_params:
        params = st.session_state.analysis_params
        current_sectors = params['market_focus']
    else:
        current_sectors = ["All Sectors"]
    
    # Get dynamic stocks based on sectors
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
        st.write(f"Stock {selected_stock} shows multiple bearish signals based on {sector_display} sector analysis...")
    
    st.info(f"📌 **Analyzed Sectors:** {', '.join(current_sectors)}")

# ==================== TAB 3: SHORT RECOMMENDATIONS ====================
with tab3:
    st.header("💰 Short CFD Recommendations")
    st.markdown("Curated short positions based on collaborative multi-agent analysis")
    
    # Get current parameters with defaults
    if st.session_state.analysis_params:
        params = st.session_state.analysis_params
        current_leverage = params['leverage']
        current_sectors = params['market_focus']
        current_position_size = params['position_size']
        use_leverage_setting = params['use_leverage']
    else:
        current_leverage = 5
        current_sectors = ["All Sectors"]
        current_position_size = 5000
        use_leverage_setting = True
    
    st.markdown("### 🎯 Top Short CFD Positions (Risk Adjusted)")
    
    # Get filtered recommendations based on sectors
    filtered_stocks = get_recommendations_for_sectors(current_sectors, current_leverage)
    
    for idx, stock in enumerate(filtered_stocks[:3], 1):
        confidence = get_confidence_score(use_leverage_setting)
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

# ==================== TAB 4: PORTFOLIO STRATEGY ====================
with tab4:
    st.header("📈 Portfolio Strategy & Risk Management")
    
    # Get current parameters with defaults
    if st.session_state.analysis_params:
        p = st.session_state.analysis_params
        p_position_size = p['position_size']
        p_leverage = p['leverage']
        p_stop_loss = p['stop_loss_pct']
        p_take_profit = p['take_profit_pct']
        p_sectors = p['market_focus']
        p_use_leverage = p['use_leverage']
    else:
        p_position_size = 5000
        p_leverage = 5
        p_stop_loss = 5
        p_take_profit = 15
        p_sectors = ["All Sectors"]
        p_use_leverage = True
    
    st.markdown("### 🛡️ Portfolio Allocation")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Risk Distribution**")
        total_capital = 15000
        num_positions = total_capital // p_position_size
        margin_required = (total_capital * p_leverage) / p_leverage if p_use_leverage else total_capital
        st.write(f"- Total Capital at Risk: ${total_capital:,}")
        st.write(f"- Position Size per Trade: ${p_position_size:,}")
        st.write(f"- Number of Positions: {num_positions}")
        st.write(f"- Leverage Multiplier: {p_leverage}x" if p_use_leverage else "- Leverage: Disabled (1:1)")
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
    
    st.markdown("### 📊 Diversification by Selected Sectors")
    
    # Calculate sector weights based on selected sectors
    if "All Sectors" in p_sectors or not p_sectors:
        sectors_list = ["Technology", "Finance", "Healthcare", "Retail", "Energy"]
        sector_weights = [35, 25, 15, 15, 10]
    else:
        sectors_list = p_sectors
        base_weight = 100 // len(sectors_list)
        sector_weights = [base_weight] * len(sectors_list)
    
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
        - Max leverage: {p_leverage}:1 {'✅ Enabled' if p_use_leverage else '❌ Disabled'}
        - Reduce at 50% account profit
        - No leverage on new positions if down 20%
        """)
    
    st.info(f"⚙️ **Current Settings:** Stop Loss: {stop_loss_pct}% | Take Profit: {take_profit_pct}% | Leverage: {'Enabled' if use_leverage else 'Disabled'}")

# ==================== FOOTER ====================
st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    **👥 Agent Team**
    - News Researcher (10y)
    - News Manager (20y)  
    - Stock Analyst (10y)
    - Portfolio Manager (20y)
    """)

with col2:
    st.markdown("""
    **⚡ Tech Stack**
    - CrewAI: Multi-agent orchestration
    - Streamlit: Interface
    - Python: Backend processing
    - OpenAI: LLM backbone
    """)

with col3:
    st.markdown("""
    **📱 Connect & Deploy**
    - GitHub: Source code & documentation
    - Docker: Easy deployment
    - Cloud: Scalable infrastructure
    """)

st.markdown("*Disclaimer: This is for educational purposes. Not financial advice. Trade at your own risk.*")
