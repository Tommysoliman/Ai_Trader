import pytz
from datetime import datetime
from typing import Dict
import yfinance as yf
import streamlit as st

def get_current_stock_price(ticker):
    """
    Fetch current stock price from Yahoo Finance
    Returns price or None if not available
    """
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period='1d')
        if data.empty:
            return None
        current_price = data['Close'].iloc[-1]
        return float(current_price)
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_multiple_stock_prices(tickers):
    """
    Fetch current prices for multiple stocks
    Returns dict with ticker: price mapping
    """
    prices = {}
    for ticker in tickers:
        price = get_current_stock_price(ticker)
        prices[ticker] = price if price else 0
    return prices

def get_us_and_egyptian_time() -> Dict[str, str]:
    """
    Get current time in both US (Eastern) and Egyptian time zones
    Returns time in 12-hour AM/PM format
    """
    # US Eastern Time
    us_tz = pytz.timezone('America/New_York')
    us_time = datetime.now(us_tz)
    us_time_str = us_time.strftime('%I:%M:%S %p')
    us_date = us_time.strftime('%A, %B %d, %Y')
    
    # Egyptian Time
    egypt_tz = pytz.timezone('Africa/Cairo')
    egypt_time = datetime.now(egypt_tz)
    egypt_time_str = egypt_time.strftime('%I:%M:%S %p')
    egypt_date = egypt_time.strftime('%A, %B %d, %Y')
    
    return {
        'us_time': us_time_str,
        'us_date': us_date,
        'egypt_time': egypt_time_str,
        'egypt_date': egypt_date,
        'us_timezone': 'US Eastern Time (ET)',
        'egypt_timezone': 'Egypt (CAT)'
    }

def format_time_display() -> str:
    """
    Format current time for display in Streamlit
    """
    times = get_us_and_egyptian_time()
    return f"""
    **🕐 Current Time:**
    
    🇺🇸 **US Eastern Time:** {times['us_time']} | {times['us_date']}
    
    🇪🇬 **Egyptian Time:** {times['egypt_time']} | {times['egypt_date']}
    """
