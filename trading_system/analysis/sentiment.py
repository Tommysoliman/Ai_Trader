"""
Sentiment Analysis using Keyword-Based Scoring
Pulls 24h headlines from NewsAPI and scores them without external libraries
"""

import os
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class SentimentAnalyzer:
    """Calculate sentiment score from financial headlines using keyword scoring"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.newsapi_key = os.getenv('NEWSAPI_KEY')
        self.lookback_hours = config.get('newsapi', {}).get('lookback_hours', 24)
        
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
        """Fetch last 24 hours of news for a ticker from NewsAPI"""
        if not self.newsapi_key:
            print("WARNING: NewsAPI key not found in .env, skipping sentiment analysis")
            return None
        
        try:
            # Calculate date range (last 24 hours)
            to_date = datetime.utcnow()
            from_date = to_date - timedelta(hours=self.lookback_hours)
            
            from_date_str = from_date.strftime('%Y-%m-%d')
            to_date_str = to_date.strftime('%Y-%m-%d')
            
            # Query NewsAPI
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': ticker,  # Search for ticker symbol
                'from': from_date_str,
                'to': to_date_str,
                'sortBy': 'publishedAt',
                'language': 'en',
                'apiKey': self.newsapi_key,
                'pageSize': 100  # Max articles per request
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] != 'ok':
                print(f"WARNING: NewsAPI error for {ticker}: {data.get('message', 'Unknown error')}")
                return None
            
            articles = data.get('articles', [])
            return articles
        
        except requests.exceptions.RequestException as e:
            print(f"Error fetching headlines for {ticker}: {e}")
            return None
        except Exception as e:
            print(f"Error in fetch_headlines: {e}")
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
    
    def calculate_sentiment_score(self, ticker: str) -> float:
        """Calculate aggregate sentiment score for a ticker (-1.0 to +1.0)
        Returns: aggregated sentiment score, or 0.0 if no articles found
        """
        articles = self.fetch_headlines(ticker)
        
        if not articles or len(articles) == 0:
            print(f"INFO: No headlines found for {ticker} in last {self.lookback_hours}h, sentiment = 0.0")
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
                return 0.0
            
            # Average sentiment across all articles
            aggregate_score = sum(scores) / len(scores)
            
            print(f"NEWS: {ticker}: Found {len(articles)} articles, sentiment = {aggregate_score:.2f}")
            
            return round(aggregate_score, 2)
        
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
