"""
Sentiment Analysis using Keyword-Based Scoring
Pulls headlines from yfinance and scores them without external libraries
"""

import os
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import yfinance as yf

class SentimentAnalyzer:
    """Calculate sentiment score from financial headlines using keyword scoring"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.newsapi_key = os.getenv('NEWSAPI_KEY')  # Optional fallback
        self.newsdata_key = os.getenv('NEWSDATA_API_KEY')  # Primary NewsData API
        self.lookback_hours = self.config.get('newsapi', {}).get('lookback_hours', 24)
        
        # Cache for sentiment scores and headlines (ticker -> (timestamp, score/headlines))
        self._sentiment_cache = {}
        self._headlines_cache = {}
        self._cache_ttl_minutes = 30  # Cache expires after 30 minutes
        
        # Keywords for sentiment classification
        self.positive_keywords = [
            'upgrade', 'beat', 'growth', 'partnership', 'bullish',
            'strong', 'raised', 'buyback', 'outperform', 'gain',
            'surge', 'recovery', 'momentum', 'positive', 'approval',
            'deal', 'contract', 'expansion', 'record', 'profit'
        ]
        
        self.negative_keywords = [
            'downgrade', 'miss', 'layoff', 'investigation', 'bearish',
            'weak', 'cut', 'lawsuit', 'underperform', 'loss',
            'decline', 'concern', 'selloff', 'negative', 'warning',
            'fraud', 'risk', 'delay', 'recall', 'bankruptcy'
        ]
    
    def fetch_headlines(self, ticker: str) -> Optional[List[Dict]]:
        """Fetch news for a ticker from yfinance (primary), NewsData API (secondary), or NewsAPI (fallback)"""
        
        # Try yfinance first (most reliable for stock news)
        try:
            print(f"📡 Fetching news from yfinance for {ticker}...")
            ticker_obj = yf.Ticker(ticker)
            news_items = ticker_obj.get_news(count=20)
            
            if news_items and len(news_items) > 0:
                print(f"✅ Got {len(news_items)} headlines from yfinance for {ticker}")
                articles = []
                for item in news_items:
                    # yfinance returns nested content structure
                    content = item.get('content', {})
                    title = content.get('title', '')
                    description = content.get('description', '') or content.get('summary', '')
                    
                    # Clean HTML tags from description if present
                    if '<' in description:
                        import re as regex
                        description = regex.sub(r'<[^>]+>', '', description)
                    
                    article = {
                        'title': title if title else (description[:100] if description else 'News Article'),
                        'description': description,
                        'url': content.get('clickThroughUrl', {}).get('url', '') if isinstance(content.get('clickThroughUrl'), dict) else '',
                        'publishedAt': content.get('pubDate', '')
                    }
                    articles.append(article)
                return articles
        except Exception as e:
            print(f"⚠️  yfinance news fetch failed for {ticker}: {e}")
        
        # Fallback to NewsData API if yfinance fails and key is available
        if self.newsdata_key:
            try:
                print(f"🔄 Falling back to NewsData API for {ticker}...")
                url = "https://newsdata.io/api/1/news"
                params = {
                    'q': ticker,
                    'apikey': self.newsdata_key,
                    'language': 'en',
                    'sortby': 'latest',
                    'limit': 20
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                if data.get('status') == 'success' and 'results' in data:
                    articles = data['results']
                    if articles and len(articles) > 0:
                        print(f"✅ Got {len(articles)} headlines from NewsData API for {ticker}")
                        
                        # Convert NewsData format to standard format
                        converted_articles = []
                        for article in articles:
                            title = article.get('title') or article.get('description', '')[:100]
                            converted = {
                                'title': title if title else 'News Article',
                                'description': article.get('description', ''),
                                'url': article.get('link', ''),
                                'publishedAt': article.get('pubDate', '')
                            }
                            converted_articles.append(converted)
                        return converted_articles
                else:
                    print(f"⚠️  NewsData API error: {data.get('message', 'Unknown error')}")
            except Exception as e:
                print(f"⚠️  NewsData API fetch failed for {ticker}: {e}")
        
        # Fallback to NewsAPI if key is available
        if self.newsapi_key:
            try:
                print(f"🔄 Falling back to NewsAPI for {ticker}...")
                to_date = datetime.utcnow()
                from_date = to_date - timedelta(hours=self.lookback_hours)
                
                from_date_str = from_date.strftime('%Y-%m-%d')
                to_date_str = to_date.strftime('%Y-%m-%d')
                
                url = "https://newsapi.org/v2/everything"
                params = {
                    'q': ticker,
                    'from': from_date_str,
                    'to': to_date_str,
                    'sortBy': 'publishedAt',
                    'language': 'en',
                    'apiKey': self.newsapi_key,
                    'pageSize': 100
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                if data['status'] != 'ok':
                    print(f"⚠️  NewsAPI error for {ticker}: {data.get('message', 'Unknown error')}")
                    return None
                
                articles = data.get('articles', [])
                print(f"✅ Got {len(articles)} headlines from NewsAPI for {ticker}")
                return articles
            
            except Exception as e:
                print(f"❌ NewsAPI fallback failed for {ticker}: {e}")
        
        print(f"⚠️  No headlines available for {ticker}")
        return None
    
    def score_headline(self, headline: str) -> float:
        """Score a single headline on scale -1.0 to +1.0"""
        headline_lower = headline.lower()
        
        positive_count = sum(1 for keyword in self.positive_keywords 
                            if keyword in headline_lower)
        negative_count = sum(1 for keyword in self.negative_keywords 
                            if keyword in headline_lower)
        
        total_keywords = positive_count + negative_count
        
        if total_keywords == 0:
            return 0.0
        
        # Net score: positive - negative, normalized to -1 to +1
        net_score = (positive_count - negative_count) / total_keywords
        
        return max(-1.0, min(1.0, net_score))
    
    def _is_cache_valid(self, cache_dict: Dict, ticker: str) -> bool:
        """Check if cache entry is still valid (not expired)"""
        if ticker not in cache_dict:
            return False
        
        timestamp, _ = cache_dict[ticker]
        age_minutes = (datetime.now() - timestamp).total_seconds() / 60
        return age_minutes < self._cache_ttl_minutes
    
    def _get_from_cache(self, cache_dict: Dict, ticker: str):
        """Retrieve value from cache if valid"""
        if self._is_cache_valid(cache_dict, ticker):
            _, value = cache_dict[ticker]
            return value
        return None
    
    def _set_cache(self, cache_dict: Dict, ticker: str, value):
        """Store value in cache with timestamp"""
        cache_dict[ticker] = (datetime.now(), value)
    
    def calculate_sentiment_score(self, ticker: str) -> float:
        """Calculate aggregate sentiment score for a ticker (-1.0 to +1.0)
        Returns: aggregated sentiment score, or 0.0 if no articles found
        Caches results for 30 minutes to avoid redundant API calls.
        """
        # Check cache first
        cached_score = self._get_from_cache(self._sentiment_cache, ticker)
        if cached_score is not None:
            print(f"INFO: Using cached sentiment for {ticker}: {cached_score:.2f}")
            return cached_score
        
        articles = self.fetch_headlines(ticker)
        
        if not articles or len(articles) == 0:
            print(f"INFO: No headlines found for {ticker} in last {self.lookback_hours}h, sentiment = 0.0")
            self._set_cache(self._sentiment_cache, ticker, 0.0)
            return 0.0
        
        try:
            scores = []
            
            for article in articles:
                # Combine title and description for scoring
                title = article.get('title', '')
                description = article.get('description', '') or ''
                
                headline_text = f"{title} {description}"
                
                if headline_text.strip():
                    score = self.score_headline(headline_text)
                    scores.append(score)
            
            if not scores:
                self._set_cache(self._sentiment_cache, ticker, 0.0)
                return 0.0
            
            # Average sentiment across all articles
            aggregate_score = sum(scores) / len(scores)
            aggregate_score = round(aggregate_score, 2)
            
            print(f"NEWS: {ticker}: Found {len(articles)} articles, sentiment = {aggregate_score:.2f}")
            
            # Cache the result
            self._set_cache(self._sentiment_cache, ticker, aggregate_score)
            
            return aggregate_score
        
        except Exception as e:
            print(f"Error calculating sentiment for {ticker}: {e}")
            return 0.0
    
    def get_top_headlines(self, ticker: str, limit: int = 3) -> List[str]:
        """Get top headlines for context in CrewAI agents"""
        articles = self.fetch_headlines(ticker)
        
        if not articles:
            return []
        
        # Sort by score (highest sentiment first)
        scored_articles = []
        for article in articles[:20]:  # Limit to avoid excessive scoring
            title = article.get('title', '')
            score = self.score_headline(title)
            scored_articles.append((title, score))
        
        # Sort by score (descending)
        scored_articles.sort(key=lambda x: abs(x[1]), reverse=True)
        
        # Return top headlines
        return [title for title, _ in scored_articles[:limit]]


def create_sentiment_context(ticker: str, sentiment_score: float, 
                            top_headlines: List[str]) -> str:
    """Format sentiment data as readable context for CrewAI agents"""
    
    headline_text = "\n".join([f"  • {h}" for h in top_headlines]) if top_headlines else "  (No headlines found)"
    
    context = f"""
MARKET SENTIMENT FOR {ticker}
=============================
Aggregate Sentiment Score: {sentiment_score:.2f} {'(BULLISH)' if sentiment_score > 0.2 else '(BEARISH)' if sentiment_score < -0.2 else '(NEUTRAL)'}

Top Headlines (Last 24h):
{headline_text}

Sentiment Interpretation:
  > +0.2:  Bullish sentiment detected
  < -0.2:  Bearish sentiment detected
  -0.2 to +0.2: Neutral / Mixed signals
"""
    return context
