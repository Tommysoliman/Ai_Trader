"""
DuckDuckGo news search module for Q&A chatbot.
Compatible with duckduckgo-search 6.x and above.
"""

from duckduckgo_search import DDGS
import logging

logger = logging.getLogger(__name__)


class DuckDuckGoNewsSearcher:
    """Search DuckDuckGo for recent news and market information."""

    def __init__(self):
        self.max_results = 10

    def search_news(self, query: str, num_results: int = 10, region: str = "us-en") -> list:
        """Search DuckDuckGo for recent news matching the query."""
        try:
            logger.info(f"Searching DuckDuckGo for: {query}")
            with DDGS() as ddgs:
                raw = ddgs.news(
                    keywords=query,
                    region=region,
                    safesearch="off",
                    timelimit="m",
                    max_results=num_results
                )
                results = list(raw) if raw else []

            formatted = []
            for article in results:
                formatted.append({
                    "title":  article.get("title", ""),
                    "body":   article.get("body", article.get("excerpt", "")),
                    "source": article.get("source", article.get("publisher", "Unknown")),
                    "url":    article.get("url", ""),
                    "date":   article.get("date", "")
                })

            logger.info(f"Found {len(formatted)} articles")
            return formatted

        except Exception as e:
            logger.error(f"DuckDuckGo search error: {str(e)}")
            return []

    def search_market_news(self, ticker: str, num_results: int = 10) -> list:
        return self.search_news(f"{ticker} stock news market analysis", num_results)

    def search_sector_news(self, sector: str, num_results: int = 10) -> list:
        return self.search_news(f"{sector} sector market news", num_results)

    def search_trading_news(self, topic: str, num_results: int = 10) -> list:
        return self.search_news(f"{topic} market news trading", num_results)

    def format_context_for_agent(self, articles: list, max_chars: int = 3000) -> str:
        """Format search results for CrewAI agent context."""
        if not articles:
            return "No recent news found."

        context = f"Recent News ({len(articles)} articles):\n\n"
        char_count = 0

        for i, article in enumerate(articles, 1):
            article_text = f"{i}. {article['title']}\n"
            article_text += f"   Source: {article['source']}\n"
            if article["body"]:
                article_text += f"   Summary: {article['body'][:200]}...\n"
            article_text += "\n"

            if char_count + len(article_text) > max_chars:
                context += f"\n... and {len(articles) - i + 1} more articles."
                break

            context += article_text
            char_count += len(article_text)

        return context


_searcher = None


def get_searcher() -> DuckDuckGoNewsSearcher:
    global _searcher
    if _searcher is None:
        _searcher = DuckDuckGoNewsSearcher()
    return _searcher


def search_for_question(question: str, num_results: int = 10) -> str:
    """Convenience function: search news and return formatted context."""
    searcher = get_searcher()
    articles = searcher.search_news(question, num_results)
    return searcher.format_context_for_agent(articles)
