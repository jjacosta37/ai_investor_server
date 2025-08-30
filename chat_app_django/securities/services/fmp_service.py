from typing import List, Dict, Any, Optional
import logging
import requests
from django.conf import settings

from .base_finance_service import FinanceBaseAPIService

logger = logging.getLogger(__name__)


class FinancialModelingPrepService(FinanceBaseAPIService):
    """
    Financial Modeling Prep API service implementation.
    """

    BASE_URL = "https://financialmodelingprep.com/stable"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "FMP_API_KEY", None)
        if not self.api_key:
            raise ValueError("Financial Modeling Prep API key is required")

        self.session = requests.Session()

    def _make_request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Make a request to the Financial Modeling Prep API.

        Args:
            endpoint: API endpoint path
            params: Additional query parameters

        Returns:
            API response data or None if request fails
        """
        if params is None:
            params = {}

        params["apikey"] = self.api_key
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to FMP API: {str(e)}")
            return None

    def get_ticker_details(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed company profile information from Financial Modeling Prep.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            
        Returns:
            Dict containing comprehensive company profile data or None if not found
        """
        try:
            data = self._make_request(f"profile?symbol={symbol}")
            if not data or len(data) == 0:
                return None
                
            profile = data[0]  # FMP returns profile data as a list with one item
            return {
                "symbol": profile.get("symbol"),
                "companyName": profile.get("companyName"),
                "price": profile.get("price"),
                "marketCap": profile.get("marketCap"),
                "beta": profile.get("beta"),
                "lastDividend": profile.get("lastDividend"),
                "range": profile.get("range"),
                "change": profile.get("change"),
                "changePercentage": profile.get("changePercentage"),
                "volume": profile.get("volume"),
                "averageVolume": profile.get("averageVolume"),
                "currency": profile.get("currency"),
                "cik": profile.get("cik"),
                "isin": profile.get("isin"),
                "cusip": profile.get("cusip"),
                "exchangeFullName": profile.get("exchangeFullName"),
                "exchange": profile.get("exchange"),
                "industry": profile.get("industry"),
                "website": profile.get("website"),
                "description": profile.get("description"),
                "ceo": profile.get("ceo"),
                "sector": profile.get("sector"),
                "country": profile.get("country"),
                "fullTimeEmployees": profile.get("fullTimeEmployees"),
                "phone": profile.get("phone"),
                "address": profile.get("address"),
                "city": profile.get("city"),
                "state": profile.get("state"),
                "zip": profile.get("zip"),
                "image": profile.get("image"),
                "ipoDate": profile.get("ipoDate"),
                "defaultImage": profile.get("defaultImage"),
                "isEtf": profile.get("isEtf"),
                "isActivelyTrading": profile.get("isActivelyTrading"),
                "isAdr": profile.get("isAdr"),
                "isFund": profile.get("isFund")
            }
        except Exception as e:
            logger.error(f"Error fetching company profile for {symbol}: {str(e)}")
            return None

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current quote for a ticker from Financial Modeling Prep.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')

        Returns:
            Dict containing quote data or None if not found
        """
        try:
            data = self._make_request(f"quote?symbol={symbol}")
            if not data or len(data) == 0:
                return None

            quote = data[0]  # FMP returns quote data as a list with one item
            return {
                "symbol": quote.get("symbol"),
                "name": quote.get("name"),
                "price": quote.get("price"),
                "changesPercentage": quote.get("changesPercentage"),
                "change": quote.get("change"),
                "dayLow": quote.get("dayLow"),
                "dayHigh": quote.get("dayHigh"),
                "yearHigh": quote.get("yearHigh"),
                "yearLow": quote.get("yearLow"),
                "marketCap": quote.get("marketCap"),
                "priceAvg50": quote.get("priceAvg50"),
                "priceAvg200": quote.get("priceAvg200"),
                "exchange": quote.get("exchange"),
                "volume": quote.get("volume"),
                "avgVolume": quote.get("avgVolume"),
                "open": quote.get("open"),
                "previousClose": quote.get("previousClose"),
                "timestamp": quote.get("timestamp"),
            }
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {str(e)}")
            return None

    def search_tickers(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for tickers matching query."""
        raise NotImplementedError("Method to be implemented later")


def get_fmp_service() -> FinancialModelingPrepService:
    """
    Factory function to get the Financial Modeling Prep API service.
    """
    return FinancialModelingPrepService()
