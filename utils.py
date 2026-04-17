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
def fetch_financial_news_24h(query: str = "stock market", limit: int = 5, sector: str = "") -> List[Dict]:
    """
    Fetch real financial news from the last 24 hours using NewsAPI
    Filters results to ensure they're relevant to the sector
    Falls back to sample data if API fails
    """
    try:
        # Try to get API key from Streamlit secrets first (for cloud deployment)
        # Then fall back to environment variable (for local development)
        try:
            news_api_key = st.secrets.get("NEWSAPI_KEY", "")
        except:
            news_api_key = getenv("NEWSAPI_KEY", "")
        
        if not news_api_key or news_api_key == "test":
            print(f"WARNING: NewsAPI key not found. Showing sample data.")
            return get_sample_news(query, limit)
        
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
            "pageSize": limit * 2,  # Fetch more to filter
            "domains": "ft.com,economist.com,bloomberg.com,cnbc.com,reuters.com,marketwatch.com"
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get("articles", [])
            
            # If no articles found, return sample data
            if not articles:
                print(f"INFO: No articles found for query: {query}. Showing sample data.")
                return get_sample_news(query, limit)
            
            # Filter articles for sector relevance
            sector_keywords = get_sector_keywords(sector)
            filtered_articles = []
            
            for article in articles:
                title_lower = article.get("title", "").lower()
                summary_lower = article.get("description", "").lower()
                combined_text = title_lower + " " + summary_lower
                
                # Check if article contains sector keywords
                if any(keyword in combined_text for keyword in sector_keywords):
                    filtered_articles.append(article)
            
            # Use filtered articles if found, otherwise use all articles
            articles_to_use = filtered_articles if filtered_articles else articles
            
            # Format articles for display
            formatted_news = []
            for article in articles_to_use[:limit]:
                formatted_news.append({
                    "title": article.get("title", ""),
                    "summary": article.get("description", ""),
                    "source": article.get("source", {}).get("name", "Unknown"),
                    "url": article.get("url", ""),
                    "published_at": article.get("publishedAt", ""),
                    "image": article.get("urlToImage", "")
                })
            
            return formatted_news if formatted_news else get_sample_news(query, limit)
        else:
            print(f"ERROR: NewsAPI returned {response.status_code}. Using sample data.")
            return get_sample_news(query, limit)
            
    except Exception as e:
        print(f"Error fetching financial news: {e}")
        return get_sample_news(query, limit)

def get_sector_keywords(sector: str) -> List[str]:
    """Get validation keywords for each sector to filter news relevance"""
    sector_keywords_map = {
        "Technology": ["tech", "software", "ai", "cloud", "semiconductor", "nvidia", "apple", "microsoft", "google", "meta", "algorithm", "data center", "chip", "gpu", "coding", "digital", "internet", "cyber", "innovation", "startup"],
        "Finance": ["bank", "finance", "financial", "fed", "rate", "credit", "mortgage", "loan", "investment", "stocks", "trading", "jpmorgan", "goldman", "wells fargo", "interest rate", "deposit", "loan", "treasury", "hedge fund", "banking"],
        "Healthcare": ["health", "pharma", "pharmaceutical", "drug", "medical", "hospital", "clinical", "fda", "vaccine", "biotech", "treatment", "disease", "patient", "medicine", "doctor", "healthcare", "nursing", "therapy", "cure", "diagnosis"],
        "Energy": ["oil", "gas", "energy", "coal", "renewable", "battery", "solar", "wind", "fuel", "power", "electricity", "petroleum", "crude", "hydro", "nuclear", "exxon", "shell", "chevron", "renewable energy"],
        "Retail": ["retail", "e-commerce", "shopping", "consumer", "amazon", "walmart", "target", "mall", "fashion", "clothing", "merchandise", "store", "sales", "commerce", "ebay", "mall", "discount"],
        "Real Estate": ["real estate", "reit", "property", "housing", "commercial", "residential", "apartment", "building", "construction", "developer", "land", "rent", "mortgage", "realestate", "homebuilder"],
        "Consumer": ["consumer", "credit", "spending", "credit card", "debt", "household", "income", "purchase", "retail sales", "payroll", "wages", "employment", "jobs", "consumer spending"]
    }
    
    return sector_keywords_map.get(sector, [])

def get_sample_news(query: str, limit: int) -> List[Dict]:
    """
    Return sample news data when API is unavailable
    """
    sample_data = {
        "technology stocks AI earnings machine learning": [
            {
                "title": "AI Revolution Continues: Tech Giants Report Record Earnings",
                "summary": "Major technology companies exceed expectations with strong AI-driven revenue growth",
                "source": "Bloomberg",
                "url": "#",
                "published_at": datetime.now().isoformat(),
                "image": ""
            },
            {
                "title": "Machine Learning Infrastructure Plays Heating Up",
                "summary": "Enterprise AI spending accelerates as companies race to deploy large language models",
                "source": "Reuters",
                "url": "#",
                "published_at": datetime.now().isoformat(),
                "image": ""
            },
            {
                "title": "NVIDIA Leads AI Chip Race with Record Data Center Sales",
                "summary": "GPU demand surges as AI adoption accelerates across industries",
                "source": "Financial Times",
                "url": "#",
                "published_at": datetime.now().isoformat(),
                "image": ""
            }
        ],
        "banking financial sector stocks earnings interest rates": [
            {
                "title": "Fed Signals Potential Rate Cuts Ahead",
                "summary": "Banking sector rallies on expectations of favorable monetary policy",
                "source": "CNBC",
                "url": "#",
                "published_at": datetime.now().isoformat(),
                "image": ""
            },
            {
                "title": "JPMorgan Reports Strong Q1 Results, Raises Guidance",
                "summary": "Net interest margins widen as deposit base stabilizes",
                "source": "MarketWatch",
                "url": "#",
                "published_at": datetime.now().isoformat(),
                "image": ""
            },
            {
                "title": "Credit Quality Improves Across Financial Sector",
                "summary": "Default rates decline, suggesting economic resilience",
                "source": "Bloomberg",
                "url": "#",
                "published_at": datetime.now().isoformat(),
                "image": ""
            }
        ],
        "healthcare pharma pharmaceutical stocks clinical trials": [
            {
                "title": "Breakthrough Drug Advances to Phase 3 Trials",
                "summary": "Major pharma stock surges on successful clinical trial results",
                "source": "Reuters",
                "url": "#",
                "published_at": datetime.now().isoformat(),
                "image": ""
            },
            {
                "title": "Healthcare Innovation Accelerates Amid Investment Surge",
                "summary": "Biotech companies attract record venture capital funding",
                "source": "Financial Times",
                "url": "#",
                "published_at": datetime.now().isoformat(),
                "image": ""
            },
            {
                "title": "FDA Approves New Cancer Treatment",
                "summary": "Regulatory tailwinds support healthcare sector growth",
                "source": "CNBC",
                "url": "#",
                "published_at": datetime.now().isoformat(),
                "image": ""
            }
        ],
        "oil energy gas stocks renewable energy commodities": [
            {
                "title": "Oil Prices Rally on Supply Concerns",
                "summary": "Geopolitical tensions support crude prices above $80/barrel",
                "source": "Bloomberg",
                "url": "#",
                "published_at": datetime.now().isoformat(),
                "image": ""
            },
            {
                "title": "Renewable Energy Adoption Accelerates Globally",
                "summary": "Clean energy stocks rally on policy support and innovation",
                "source": "Reuters",
                "url": "#",
                "published_at": datetime.now().isoformat(),
                "image": ""
            },
            {
                "title": "Energy Sector Transition Continues",
                "summary": "Traditional oil majors diversify into renewable energy",
                "source": "Financial Times",
                "url": "#",
                "published_at": datetime.now().isoformat(),
                "image": ""
            }
        ],
        "retail consumer stocks e-commerce sales earnings": [
            {
                "title": "E-commerce Spending Accelerates Post-Quarter",
                "summary": "Online retailers report strong sales growth exceeding expectations",
                "source": "CNBC",
                "url": "#",
                "published_at": datetime.now().isoformat(),
                "image": ""
            },
            {
                "title": "Consumer Sentiment Strengthens",
                "summary": "Retail confidence index hits 6-month high",
                "source": "MarketWatch",
                "url": "#",
                "published_at": datetime.now().isoformat(),
                "image": ""
            },
            {
                "title": "Amazon and Competitors Report Margin Expansion",
                "summary": "Operating leverage improves as scale increases",
                "source": "Bloomberg",
                "url": "#",
                "published_at": datetime.now().isoformat(),
                "image": ""
            }
        ],
        "real estate REIT property stocks housing": [
            {
                "title": "Commercial REIT Valuations Rise on Rate Expectations",
                "summary": "Property sector benefits from improving capitalization rates",
                "source": "Reuters",
                "url": "#",
                "published_at": datetime.now().isoformat(),
                "image": ""
            },
            {
                "title": "Residential Real Estate Market Stabilizes",
                "summary": "Housing inventory levels balance after recent supply surge",
                "source": "Financial Times",
                "url": "#",
                "published_at": datetime.now().isoformat(),
                "image": ""
            },
            {
                "title": "Data Center REITs Rally on AI Boom",
                "summary": "Infrastructure demand remains strong for AI computing",
                "source": "CNBC",
                "url": "#",
                "published_at": datetime.now().isoformat(),
                "image": ""
            }
        ],
        "consumer credit cards stocks spending debt": [
            {
                "title": "Consumer Credit Health Improves",
                "summary": "Delinquency rates decline, suggesting economic strength",
                "source": "Bloomberg",
                "url": "#",
                "published_at": datetime.now().isoformat(),
                "image": ""
            },
            {
                "title": "Credit Card Companies Report Record Spending",
                "summary": "Payment volumes hit all-time highs",
                "source": "Reuters",
                "url": "#",
                "published_at": datetime.now().isoformat(),
                "image": ""
            },
            {
                "title": "Consumer Discretionary Spending Accelerates",
                "summary": "Household confidence strengthens demand for consumer goods",
                "source": "MarketWatch",
                "url": "#",
                "published_at": datetime.now().isoformat(),
                "image": ""
            }
        ]
    }
    
    # Find matching sample data or return generic market news
    for key, articles in sample_data.items():
        if any(term in query.lower() for term in key.split()):
            return articles[:limit]
    
    # Default market news
    return [
        {
            "title": "Markets Rally on Positive Economic Data",
            "summary": "Stock indices reach new highs amid strong economic indicators",
            "source": "Bloomberg",
            "url": "#",
            "published_at": datetime.now().isoformat(),
            "image": ""
        },
        {
            "title": "Fed Policy Supports Market Sentiment",
            "summary": "Central bank messaging provides stability to financial markets",
            "source": "Reuters",
            "url": "#",
            "published_at": datetime.now().isoformat(),
            "image": ""
        },
        {
            "title": "Corporate Earnings Season Begins Strong",
            "summary": "Early results exceed expectations as companies guide higher",
            "source": "CNBC",
            "url": "#",
            "published_at": datetime.now().isoformat(),
            "image": ""
        }
    ][:limit]

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

def analyze_news_sentiment(text: str) -> Dict[str, any]:
    """
    Analyze news sentiment using keyword matching
    Returns sentiment score (-1 to 1) and signal type
    """
    text_lower = text.lower()
    
    # Bullish keywords
    bullish_keywords = [
        "surge", "jump", "rally", "beat", "exceed", "growth", "strong", "recovery",
        "upside", "bullish", "gains", "outperform", "breakthrough", "upgrade",
        "record high", "accelerate", "boom", "momentum", "crush", "soar"
    ]
    
    # Bearish keywords
    bearish_keywords = [
        "plunge", "drop", "crash", "miss", "fail", "decline", "weak", "stress",
        "downside", "bearish", "loss", "underperform", "downgrade", "warning",
        "warning sign", "risk", "concern", "slump", "tumble", "collapse"
    ]
    
    bullish_score = sum(1 for keyword in bullish_keywords if keyword in text_lower)
    bearish_score = sum(1 for keyword in bearish_keywords if keyword in text_lower)
    
    # Calculate sentiment (-1 to 1)
    total = bullish_score + bearish_score
    if total == 0:
        sentiment = 0
    else:
        sentiment = (bullish_score - bearish_score) / total
    
    return {
        "sentiment": sentiment,
        "bullish_count": bullish_score,
        "bearish_count": bearish_score,
        "is_bullish": sentiment > 0.2,
        "is_bearish": sentiment < -0.2,
        "is_neutral": -0.2 <= sentiment <= 0.2
    }

def generate_signals_from_news(news_articles: List[Dict]) -> Dict[str, str]:
    """
    Generate technical signals based on recent news sentiment
    Returns mapping of signal types to descriptions
    """
    if not news_articles:
        return {
            "signal_type": "Neutral",
            "bullish_signal": "Consolidation",
            "bearish_signal": "No Pressure"
        }
    
    # Analyze sentiment across all news articles
    all_sentiments = []
    for article in news_articles[:5]:
        title_sentiment = analyze_news_sentiment(article.get("title", ""))
        summary_sentiment = analyze_news_sentiment(article.get("summary", ""))
        
        # Combine both
        combined = (title_sentiment["sentiment"] + summary_sentiment["sentiment"]) / 2
        all_sentiments.append(combined)
    
    # Calculate average sentiment
    avg_sentiment = sum(all_sentiments) / len(all_sentiments) if all_sentiments else 0
    
    # Map sentiment to signals
    bullish_signals = [
        "Golden Cross", "Strong Breakout", "Bull Run", "Uptrend Confirmed",
        "Bullish Resolution", "Recovery Rally", "Trading Strength", "Credit Recovery",
        "Regulatory Tailwinds", "Strong Pipeline", "Pipeline Growth", "M&A Upside",
        "Cycle Bottom", "Supply Recovery", "Margin Expansion", "Production Upside",
        "Margin Recovery", "Housing Recovery", "Demand Recovery", "Labor Optimization"
    ]
    
    bearish_signals = [
        "Death Cross", "Failed Recovery", "Valuation Extreme", "Trend Weakness",
        "Rate Vulnerability", "Trading Weakness", "Credit Stress", "Earnings Concern",
        "Patent Cliff", "Pipeline Risk", "M&A Concerns", "Peak Cycle", "Supply Glut",
        "Margin Pressure", "Production Decline", "Housing Slowdown", "Demand Weakness"
    ]
    
    neutral_signals = [
        "Consolidation", "Range Trading", "Support Holds", "Technical Equilibrium"
    ]
    
    # Select signal based on sentiment
    if avg_sentiment > 0.3:
        signal = bullish_signals[int((avg_sentiment * 10) % len(bullish_signals))]
        signal_type = "Strong Bullish"
    elif avg_sentiment > 0.1:
        signal = bullish_signals[int((avg_sentiment * 5) % len(bullish_signals))]
        signal_type = "Mildly Bullish"
    elif avg_sentiment < -0.3:
        signal = bearish_signals[int((abs(avg_sentiment) * 10) % len(bearish_signals))]
        signal_type = "Strong Bearish"
    elif avg_sentiment < -0.1:
        signal = bearish_signals[int((abs(avg_sentiment) * 5) % len(bearish_signals))]
        signal_type = "Mildly Bearish"
    else:
        signal = neutral_signals[0]
        signal_type = "Neutral"
    
    return {
        "signal": signal,
        "signal_type": signal_type,
        "sentiment_score": round(avg_sentiment, 2),
        "confidence": round(abs(avg_sentiment) * 100, 0)
    }
