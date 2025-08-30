from typing import List, Dict, Any, Optional
import logging
from polygon import RESTClient
from django.conf import settings

from .base_finance_service import FinanceBaseAPIService

logger = logging.getLogger(__name__)


class PolygonAPIService(FinanceBaseAPIService):
    """
    Polygon.io API service implementation.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "POLYGON_API_KEY", None)
        if not self.api_key:
            raise ValueError("Polygon API key is required")

        self.client = RESTClient(self.api_key)

    def get_ticker_details(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed ticker information from Polygon.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')

        Returns:
            Dict containing ticker details or None if not found
        """
        try:
            ticker_details = self.client.get_ticker_details(symbol)
            return {
                "symbol": ticker_details.ticker,
                "name": ticker_details.name,
                "market": ticker_details.market,
                "locale": ticker_details.locale,
                "primary_exchange": ticker_details.primary_exchange,
                "type": ticker_details.type,
                "currency_name": ticker_details.currency_name,
                "description": getattr(ticker_details, "description", ""),
                "homepage_url": getattr(ticker_details, "homepage_url", ""),
                "logo_url": (
                    getattr(ticker_details.branding, "logo_url", "")
                    if hasattr(ticker_details, "branding")
                    else ""
                ),
                "market_cap": getattr(ticker_details, "market_cap", None),
                "share_class_shares_outstanding": getattr(
                    ticker_details, "share_class_shares_outstanding", None
                ),
                "sic_description": getattr(ticker_details, "sic_description", ""),
            }
        except Exception as e:
            logger.error(f"Error fetching ticker details for {symbol}: {str(e)}")
            return None

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current quote for a ticker.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')

        Returns:
            Dict containing quote data or None if not found
        """
        try:
            quote = self.client.get_last_quote(symbol)
            return {
                "symbol": symbol,
                "last_price": (
                    quote.last.price if hasattr(quote, "last") and quote.last else None
                ),
                "bid": (
                    quote.last.bid if hasattr(quote, "last") and quote.last else None
                ),
                "ask": (
                    quote.last.ask if hasattr(quote, "last") and quote.last else None
                ),
                "bid_size": (
                    quote.last.bid_size
                    if hasattr(quote, "last") and quote.last
                    else None
                ),
                "ask_size": (
                    quote.last.ask_size
                    if hasattr(quote, "last") and quote.last
                    else None
                ),
                "timestamp": (
                    quote.last.participant_timestamp
                    if hasattr(quote, "last") and quote.last
                    else None
                ),
            }
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {str(e)}")
            return None

    def get_previous_close(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get previous day's close for a ticker.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')

        Returns:
            Dict containing previous close data or None if not found
        """
        try:
            prev_close = self.client.get_previous_close_agg(symbol)
            if prev_close and len(prev_close) > 0:
                data = prev_close[0]
                return {
                    "symbol": symbol,
                    "close": data.close,
                    "high": data.high,
                    "low": data.low,
                    "open": data.open_,
                    "volume": data.volume,
                    "vwap": data.vwap,
                    "timestamp": data.timestamp,
                }
        except Exception as e:
            logger.error(f"Error fetching previous close for {symbol}: {str(e)}")
            return None

    def search_tickers(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for tickers matching query.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of ticker dictionaries
        """
        try:
            results = []
            for ticker in self.client.list_tickers(
                search=query,
                market="stocks",
                active=True,
                limit=limit,
                sort="ticker",
                order="asc",
            ):
                results.append(
                    {
                        "symbol": ticker.ticker,
                        "name": ticker.name,
                        "market": ticker.market,
                        "locale": ticker.locale,
                        "primary_exchange": ticker.primary_exchange,
                        "type": ticker.type,
                        "currency_name": ticker.currency_name,
                        "last_updated_utc": ticker.last_updated_utc,
                    }
                )
            return results
        except Exception as e:
            logger.error(f"Error searching tickers for query '{query}': {str(e)}")
            return []

    def list_tickers_by_exchange(
        self, exchange: str = "XNYS", limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List tickers from a specific exchange.

        Args:
            exchange: Exchange code (e.g., 'XNYS' for NYSE)
            limit: Maximum number of results

        Returns:
            List of ticker dictionaries
        """
        try:
            results = []
            for ticker in self.client.list_tickers(
                market="stocks",
                exchange=exchange,
                active=True,
                limit=limit,
                sort="ticker",
                order="asc",
            ):
                results.append(
                    {
                        "symbol": ticker.ticker,
                        "name": ticker.name,
                        "market": ticker.market,
                        "locale": ticker.locale,
                        "primary_exchange": ticker.primary_exchange,
                        "type": ticker.type,
                        "currency_name": ticker.currency_name,
                        "last_updated_utc": ticker.last_updated_utc,
                    }
                )
            return results
        except Exception as e:
            logger.error(f"Error listing tickers for exchange {exchange}: {str(e)}")
            return []

    def get_news(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get news articles for a ticker.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            limit: Maximum number of articles

        Returns:
            List of news article dictionaries
        """
        try:
            results = []
            for article in self.client.list_ticker_news(
                ticker=symbol, limit=limit, sort="published_utc", order="desc"
            ):
                results.append(
                    {
                        "id": article.id,
                        "title": article.title,
                        "author": article.author,
                        "published_utc": article.published_utc,
                        "article_url": article.article_url,
                        "description": getattr(article, "description", ""),
                        "keywords": getattr(article, "keywords", []),
                        "image_url": getattr(article, "image_url", ""),
                        "amp_url": getattr(article, "amp_url", ""),
                    }
                )
            return results
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {str(e)}")
            return []


def get_polygon_service() -> PolygonAPIService:
    """
    Factory function to get the Polygon API service.
    """
    return PolygonAPIService()
