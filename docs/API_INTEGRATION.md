# API Integration Guide

## Overview

This guide explains how to integrate real market data APIs into the AI Traders system to replace demo data with live information.

---

## Currently Implemented (Demo Mode)

In `agents.py`, there are placeholder tools:

```python
@tool("News Database")
def search_market_news(query: str) -> str:
    return f"News search results for: {query}. [In production, connects to live news feeds]"

@tool("Stock Data")
def get_stock_data(ticker: str) -> str:
    return f"Stock data for {ticker}. [In production, connects to live market data]"

@tool("Market Sentiment")
def analyze_sentiment() -> str:
    return "Market sentiment analysis: [VIX, put/call ratios, insider selling, etc.]"

@tool("CFD Analysis")
def cfd_recommendation(ticker: str) -> str:
    return f"Short CFD recommendation for {ticker}: [Risk/Reward analysis]"
```

---

## Available APIs to Integrate

### 1. Alpha Vantage (Stock Data & Technical Analysis)

**Website**: https://www.alphavantage.co
**Pricing**: Free tier available
**Rate Limit**: 5 calls/minute free

#### Setup
```bash
pip install alpha-vantage
```

#### Environment Variable
```env
ALPHA_VANTAGE_KEY=your_api_key_here
```

#### Implementation

```python
from alpha_vantage.timeseries import TimeSeries
import os

def get_stock_data_live(ticker: str) -> dict:
    """Fetch real stock data from Alpha Vantage"""
    ts = TimeSeries(
        key=os.getenv('ALPHA_VANTAGE_KEY'),
        output_format='pandas'
    )
    
    # Get daily time series
    data, meta_data = ts.get_daily(symbol=ticker)
    
    # Get technical indicators
    from alpha_vantage.techindicators import TechIndicators
    ti = TechIndicators(
        key=os.getenv('ALPHA_VANTAGE_KEY'),
        output_format='pandas'
    )
    
    rsi, _ = ti.get_rsi(symbol=ticker, interval='daily', time_period=14)
    macd, _ = ti.get_macd(symbol=ticker, interval='daily')
    
    return {
        'price_data': data,
        'rsi': rsi,
        'macd': macd,
        'meta': meta_data
    }
```

---

### 2. Finnhub (News & Company Data)

**Website**: https://finnhub.io
**Pricing**: Free tier available
**Rate Limit**: 60 calls/minute free
**Strengths**: Excellent for news and company data

#### Setup
```bash
pip install finnhub-python
```

#### Environment Variable
```env
FINNHUB_API_KEY=your_api_key_here
```

#### Implementation

```python
import finnhub
import os

def get_latest_news(query: str = "") -> list:
    """Fetch latest market news from Finnhub"""
    finnhub_client = finnhub.Client(
        api_key=os.getenv('FINNHUB_API_KEY')
    )
    
    # Get general market news
    news = finnhub_client.general_news(
        category='general',
        min_id=0
    )
    
    # Filter by query if provided
    if query:
        news['data'] = [
            n for n in news['data'] 
            if query.lower() in n['headline'].lower()
        ]
    
    return news

def get_company_news(ticker: str) -> list:
    """Get company-specific news"""
    finnhub_client = finnhub.Client(
        api_key=os.getenv('FINNHUB_API_KEY')
    )
    
    news = finnhub_client.company_news(
        symbol=ticker,
        _from='2024-01-01',
        to='2024-12-31'
    )
    
    return news
```

---

### 3. NewsAPI (News Aggregation)

**Website**: https://newsapi.org
**Pricing**: Free and paid tiers
**Rate Limit**: 100 calls/day free
**Strengths**: Best for broad market news

#### Setup
```bash
pip install newsapi-python
```

#### Environment Variable
```env
NEWSAPI_KEY=your_api_key_here
```

#### Implementation

```python
import os
from newsapi import NewsApiClient

def search_market_news_live(query: str) -> list:
    """Search market news from NewsAPI"""
    newsapi = NewsApiClient(
        api_key=os.getenv('NEWSAPI_KEY')
    )
    
    articles = newsapi.get_everything(
        q=query,
        language='en',
        sort_by='publishedAt',
        page_size=50
    )
    
    return articles['articles']

def get_headlines() -> list:
    """Get top headlines"""
    newsapi = NewsApiClient(
        api_key=os.getenv('NEWSAPI_KEY')
    )
    
    headlines = newsapi.get_top_headlines(
        category='business',
        country='us',
        page_size=50
    )
    
    return headlines['articles']
```

---

### 4. IEX Cloud (Market Data & News)

**Website**: https://iexcloud.io
**Pricing**: Free and paid tiers
**Strengths**: Comprehensive financial data

#### Setup
```bash
pip install pyEX
```

#### Implementation

```python
import os
from pyEX import Client

def get_stock_info_live(ticker: str) -> dict:
    """Get comprehensive stock information"""
    client = Client(
        token=os.getenv('IEX_CLOUD_KEY')
    )
    
    quote = client.quote(ticker)
    company = client.company(ticker)
    earnings = client.earnings(ticker)
    
    return {
        'quote': quote,
        'company': company,
        'earnings': earnings
    }
```

---

### 5. Polygon.io (Market Data & Options)

**Website**: https://polygon.io
**Pricing**: Paid but comprehensive
**Strengths**: Real-time quotes, options data, news

#### Setup
```bash
pip install polygon-api-client
```

#### Implementation

```python
import os
from polygon import RESTClient

def get_market_data_live(ticker: str) -> dict:
    """Get comprehensive market data from Polygon"""
    client = RESTClient(
        api_key=os.getenv('POLYGON_API_KEY')
    )
    
    # Get latest price
    quote = client.get_last_quote(ticker)
    
    # Get previous close
    prev = client.get_previous_close(ticker)
    
    # Get aggregate data
    agg = client.get_agg(
        ticker=ticker,
        multiplier=1,
        timespan="day",
        from_="2024-01-01",
        to="2024-12-31"
    )
    
    return {
        'quote': quote,
        'previous': prev,
        'aggregates': agg
    }
```

---

### 6. OANDA (Forex & CFD Data)

**Website**: https://oanda.com
**Pricing**: Paid with free demo account
**Strengths**: CFD pricing and leverage info

#### Setup
```bash
pip install oandapyV20
```

#### Implementation

```python
import os
from oandapyV20 import API
from oandapyV20.endpoints.pricing import PricingInfo

def get_cfd_pricing(symbol: str) -> dict:
    """Get CFD pricing from OANDA"""
    api = API(
        access_token=os.getenv('OANDA_ACCESS_TOKEN'),
        environment="practice"
    )
    
    params = {"instruments": symbol}
    request = PricingInfo(accountID="your_account_id", params=params)
    
    response = api.request(request)
    return response
```

---

### 7. Interactive Brokers (Live Trading)

**Website**: https://www.interactivebrokers.com
**Pricing**: Commission-based
**Strengths**: Actual trading execution

#### Setup
```bash
pip install ibapi
```

#### Implementation

```python
from ibapi.client import EClient
from ibapi.wrapper import EWrapper

class IBTrader(EWrapper, EClient):
    """Interactive Brokers API integration"""
    
    def __init__(self):
        EClient.__init__(self, self)
        
    def error(self, reqId, errorCode, errorString):
        print(f"Error {errorCode}: {errorString}")
    
    def tickPrice(self, reqId, tickType, price, attrib):
        print(f"Tick {reqId}: {price}")

def connect_and_trade():
    """Connect to IB and place orders"""
    app = IBTrader()
    app.connect("127.0.0.1", 7497, 1)
    # Place orders, get data, etc.
    app.run()
```

---

## Integration Steps

### Step 1: Get API Keys

1. Sign up for each service
2. Generate API keys
3. Add to `.env` file:

```env
# News & Market Data
ALPHA_VANTAGE_KEY=your_key
FINNHUB_API_KEY=your_key
NEWSAPI_KEY=your_key
IEX_CLOUD_KEY=your_key
POLYGON_API_KEY=your_key

# Trading Platforms
OANDA_ACCESS_TOKEN=your_token
IB_ACCOUNT_ID=your_account

# OpenAI for LLM
OPENAI_API_KEY=sk-...
```

### Step 2: Install Python Packages

```bash
pip install -r requirements-api.txt
```

Create `requirements-api.txt`:
```
alpha-vantage==2.3.1
finnhub-python==1.3.13
newsapi-python==1.2.0
pyEX==0.5.0
polygon-api-client==1.13.0
oandapyV20==0.7.2
```

### Step 3: Modify agents.py

Replace placeholder tools with real implementations:

```python
from alpha_vantage.timeseries import TimeSeries
import finnhub
import os

@tool("Stock Data")
def get_stock_data(ticker: str) -> str:
    """Get real stock data from Alpha Vantage"""
    try:
        ts = TimeSeries(
            key=os.getenv('ALPHA_VANTAGE_KEY'),
            output_format='json'
        )
        data, meta = ts.get_daily(symbol=ticker)
        
        # Format response
        latest = data[list(data.keys())[0]]
        return f"""
        {ticker} Latest Data:
        Close: ${latest['4. close']}
        Volume: {latest['5. volume']}
        """
    except Exception as e:
        return f"Error fetching data: {str(e)}"

@tool("News Database")
def search_market_news(query: str) -> str:
    """Search real market news"""
    try:
        finnhub_client = finnhub.Client(
            api_key=os.getenv('FINNHUB_API_KEY')
        )
        news = finnhub_client.general_news(category='general')
        
        # Filter and format
        results = []
        for item in news.get('data', [])[:5]:
            results.append(f"- {item['headline']}")
        
        return "\n".join(results)
    except Exception as e:
        return f"Error fetching news: {str(e)}"
```

### Step 4: Add Error Handling

```python
import asyncio
from functools import wraps

def retry_on_api_error(max_retries=3):
    """Decorator for API calls with retry logic"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    wait_time = 2 ** attempt
                    print(f"API error, retrying in {wait_time}s: {str(e)}")
                    asyncio.sleep(wait_time)
        return wrapper
    return decorator

@retry_on_api_error()
@tool("Stock Data")
def get_stock_data_robust(ticker: str) -> str:
    # Implementation here
    pass
```

### Step 5: Rate Limiting

```python
import time
from collections import defaultdict

class RateLimiter:
    def __init__(self, calls_per_minute=60):
        self.calls_per_minute = calls_per_minute
        self.call_times = defaultdict(list)
    
    def wait(self, key: str):
        now = time.time()
        calls = self.call_times[key]
        
        # Remove old calls
        calls[:] = [t for t in calls if t > now - 60]
        
        if len(calls) >= self.calls_per_minute:
            sleep_time = 60 - (now - calls[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        calls.append(now)

limiter = RateLimiter(calls_per_minute=60)

@tool("Stock Data")
def get_stock_data_rate_limited(ticker: str) -> str:
    limiter.wait('alpha_vantage')
    # Fetch data
    pass
```

---

## Production Deployment Checklist

- [ ] All API keys in environment variables
- [ ] Error handling and retry logic
- [ ] Rate limiting implemented
- [ ] Cache mechanism for frequently called data
- [ ] Monitoring and logging
- [ ] Fallback to demo mode if APIs fail
- [ ] Unit tests for API integrations
- [ ] Documentation updated

---

## Monitoring & Logging

```python
import logging

# Configure logging
logging.basicConfig(
    filename='api_calls.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@tool("Stock Data")
def get_stock_data_monitored(ticker: str) -> str:
    try:
        logger.info(f"Fetching data for {ticker}")
        # Implementation
        logger.info(f"Successfully fetched {ticker}")
        return data
    except Exception as e:
        logger.error(f"Error fetching {ticker}: {str(e)}")
        return f"Error: {str(e)}"
```

---

## Cost Optimization

### Free Tier Strategy
- Use free APIs for base functionality
- Implement 1-hour caching
- Batch requests where possible
- Limit update frequency to business hours

### Paid Tier Strategy
- Real-time data for active positions
- Higher update frequency
- More comprehensive data
- Better reliability SLAs

---

## Next Steps

1. Choose which APIs to integrate first
2. Sign up and get API keys
3. Modify `agents.py` with real implementations
4. Test thoroughly before production
5. Add caching and rate limiting
6. Deploy to production
7. Monitor API usage and costs
