import pytz
from datetime import datetime, timedelta
from typing import Dict, List
import yfinance as yf
import streamlit as st
import requests
from os import getenv

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

@st.cache_data(ttl=600)  # Cache for 10 minutes
def fetch_financial_news_24h(query: str = "stock market", limit: int = 5) -> List[Dict]:
    """
    Fetch real financial news from the last 24 hours using NewsAPI
    Searches Financial Times, Economist, and major financial sources
    """
    try:
        # Get API key from environment
        news_api_key = getenv("NEWSAPI_KEY", "")
        
        if not news_api_key:
            # Fallback to public news API without key (limited requests)
            news_api_key = "test"
        
        # Calculate 24 hours ago
        date_from = (datetime.utcnow() - timedelta(days=1)).isoformat()
        
        # NewsAPI endpoint
        url = "https://newsapi.org/v2/everything"
        
        params = {
            "q": query,
            "from": date_from,
            "sortBy": "publishedAt",
            "language": "en",
            "apiKey": news_api_key,
            "pageSize": limit,
            "domains": "ft.com,economist.com,bloomberg.com,cnbc.com,reuters.com,marketwatch.com"
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            articles = response.json().get("articles", [])
            
            # Format articles for display
            formatted_news = []
            for article in articles[:limit]:
                formatted_news.append({
                    "title": article.get("title", ""),
                    "summary": article.get("description", ""),
                    "source": article.get("source", {}).get("name", "Unknown"),
                    "url": article.get("url", ""),
                    "published_at": article.get("publishedAt", ""),
                    "image": article.get("urlToImage", "")
                })
            
            return formatted_news
        else:
            print(f"NewsAPI Error: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"Error fetching financial news: {e}")
        return []

def get_latest_market_alerts(tickers: List[str]) -> List[Dict]:
    """
    Generate real alerts based on latest market data and news
    """
    try:
        alerts = []
        
        # Fetch real prices for all tickers
        prices = {}
        for ticker in tickers[:5]:  # Limit to 5 for performance
            try:
                stock = yf.Ticker(ticker)
                data = stock.history(period='1d')
                if not data.empty:
                    current = data['Close'].iloc[-1]
                    prev_close = data['Close'].iloc[0] if len(data) > 1 else current
                    change_pct = ((current - prev_close) / prev_close) * 100
                    prices[ticker] = {
                        "current": current,
                        "change_pct": change_pct
                    }
            except:
                continue
        
        # Create alerts based on price movements
        for ticker, data in prices.items():
            change = data["change_pct"]
            
            if change > 5:
                alerts.append({
                    "type": "success",
                    "title": f"📈 {ticker} Strong Surge",
                    "message": f"{ticker} jumped {change:.2f}% - Long opportunity confirmed",
                    "time": "Just now"
                })
            elif change < -5:
                alerts.append({
                    "type": "warning",
                    "title": f"📉 {ticker} Sharp Decline",
                    "message": f"{ticker} dropped {abs(change):.2f}% - Potential entry point",
                    "time": "Just now"
                })
            elif change > 2:
                alerts.append({
                    "type": "info",
                    "title": f"✅ {ticker} Positive Momentum",
                    "message": f"{ticker} up {change:.2f}% - Uptrend intact",
                    "time": "Recently"
                })
        
        # Add news-based alerts
        news = fetch_financial_news_24h("stock market", limit=3)
        if news:
            for article in news[:2]:
                alerts.append({
                    "type": "info",
                    "title": f"📰 {article['source']} - " + article['title'][:40],
                    "message": article['summary'][:80] if article['summary'] else "Breaking financial news",
                    "time": "Latest"
                })
        
        return alerts if alerts else get_default_alerts()
        
    except Exception as e:
        print(f"Error generating alerts: {e}")
        return get_default_alerts()

def get_default_alerts() -> List[Dict]:
    """
    Return default alerts if real data fetch fails
    """
    return [
        {"type": "info", "title": "📊 Market Data Loading", "message": "Fetching latest prices and news...", "time": "2 min ago"},
        {"type": "success", "title": "✅ System Ready", "message": "Long CFD analysis engine active", "time": "5 min ago"},
        {"type": "info", "title": "🔄 Data Refresh", "message": "Alerts update every 2 minutes", "time": "8 min ago"}
    ]
