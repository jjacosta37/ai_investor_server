from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class FinanceBaseAPIService(ABC):
    """
    Abstract base class for external financial API services.
    """

    @abstractmethod
    def get_ticker_details(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a ticker."""
        pass

    @abstractmethod
    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current quote for a ticker."""
        pass

    @abstractmethod
    def search_tickers(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for tickers matching query."""
        pass