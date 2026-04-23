"""
DuckDuckGo news search module for Q&A chatbot.
Searches recent news from the last 7 weeks and provides context for answers.
"""

from duckduckgo_search import DDGS
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DuckDuckGoNewsSearcher:
    """Search DuckDuckGo for recent news and market information."""
    
    def __init__(self):
        """Initialize DuckDuckGo searcher."""
        self.ddgs = DDGS()
        self.max_results = 10
        self.weeks = 7
    
    def search_news(self, query: str, num_results: int = 10) -> list:
        """
        Search DuckDuckGo for recent news matching the query.
        
        Args:
            query: Search query (e.g., "Apple stock market news")
            num_results: Number of results to return (default: 10)
        
        Returns:
            List of news articles with title, snippet, and source
        """
        try:
            # Calculate date range (last 7 weeks)
            end_date = datetime.now()
            start_date = end_date - timedelta(weeks=self.weeks)
            
            logger.info(f"🔍 Searching DuckDuckGo for: {query}")
            logger.info(f"📅 Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
            # Search news
            results = self.ddgs.news(
                keywords=query,
                region="us",
                safesearch="off",
                timelimit="w"  # Last 7 weeks
            )
            
            # Format results
            formatted_results = []
            for i, result in enumerate(results):
                if i >= num_results:
                    break
                
                formatted_results.append({
                    "title": result.get("title", ""),
                    "body": result.get("body", ""),
                    "source": result.get("source", "Unknown"),
                    "url": result.get("url", ""),
                    "date": result.get("date", "")
                })
            
            logger.info(f"✅ Found {len(formatted_results)} articles")
            return formatted_results
        
        except Exception as e:
            logger.error(f"❌ DuckDuckGo search error: {str(e)}")
            return []
    
    def search_market_news(self, ticker: str, num_results: int = 10) -> list:
        """
        Search DuckDuckGo for market news about a specific stock.
        
        Args:
            ticker: Stock ticker (e.g., "AAPL")
            num_results: Number of results to return
        
        Returns:
            List of market news articles
        """
        query = f"{ticker} stock news market analysis"
        return self.search_news(query, num_results)
    
    def search_sector_news(self, sector: str, num_results: int = 10) -> list:
        """
        Search DuckDuckGo for sector news.
        
        Args:
            sector: Sector name (e.g., "Technology", "Finance", "Energy")
            num_results: Number of results to return
        
        Returns:
            List of sector news articles
        """
        query = f"{sector} sector market news"
        return self.search_news(query, num_results)
    
    def search_trading_news(self, topic: str, num_results: int = 10) -> list:
        """
        Search DuckDuckGo for trading/market related news.
        
        Args:
            topic: Trading topic (e.g., "Fed interest rates", "Bitcoin", "S&P 500")
            num_results: Number of results to return
        
        Returns:
            List of trading news articles
        """
        query = f"{topic} market news trading"
        return self.search_news(query, num_results)
    
    def format_context_for_agent(self, articles: list, max_chars: int = 3000) -> str:
        """
        Format search results for CrewAI agent context.
        
        Args:
            articles: List of article dicts from search
            max_chars: Maximum characters to include
        
        Returns:
            Formatted context string for the agent
        """
        if not articles:
            return "No recent news found."
        
        context = f"📰 Recent News Context (Last 7 weeks, {len(articles)} articles):\n\n"
        char_count = 0
        
        for i, article in enumerate(articles, 1):
            article_text = f"{i}. {article['title']}\n"
            article_text += f"   Source: {article['source']}\n"
            if article['body']:
                article_text += f"   Summary: {article['body'][:200]}...\n"
            article_text += "\n"
            
            if char_count + len(article_text) > max_chars:
                context += f"\n... and {len(articles) - i + 1} more articles."
                break
            
            context += article_text
            char_count += len(article_text)
        
        return context


# Global searcher instance
_searcher = None


def get_searcher() -> DuckDuckGoNewsSearcher:
    """Get or create global DuckDuckGo searcher instance."""
    global _searcher
    if _searcher is None:
        _searcher = DuckDuckGoNewsSearcher()
    return _searcher


def search_for_question(question: str, num_results: int = 10) -> str:
    """
    Convenience function to search for news related to a question.
    Returns formatted context for CrewAI agents.
    
    Args:
        question: User question
        num_results: Number of results to fetch
    
    Returns:
        Formatted context string
    """
    searcher = get_searcher()
    articles = searcher.search_news(question, num_results)
    return searcher.format_context_for_agent(articles)
