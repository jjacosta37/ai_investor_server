"""
Stock Analysis Service using Tavily search and AI agents.
"""

import logging
from typing import Optional
from langchain.chat_models import init_chat_model
from langchain_tavily import TavilySearch
from langchain.schema import HumanMessage
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

from .prompts.prompts import structured_analysis_prompt
from .schemas import StructuredStockAnalysis

load_dotenv()

logger = logging.getLogger(__name__)

REACT_MODEL = "claude-sonnet-4-20250514"


class StockAnalysisService:
    """Service class for getting structured stock analysis using Tavily search"""

    def __init__(self):
        """Initialize the service with LLM and search tools"""
        try:
            self.llm = init_chat_model(
                model=REACT_MODEL, temperature=0, max_tokens=10000
            )

            self.tavily_search_tool = TavilySearch(
                max_results=5,
                topic="general",
                include_favicon=True,
            )

            self.agent = create_react_agent(
                model=self.llm,
                tools=[self.tavily_search_tool],
                prompt=structured_analysis_prompt,
                response_format=StructuredStockAnalysis,
            )

            logger.info("StockAnalysisService initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize StockAnalysisService: {e}")
            raise

    def get_stock_analysis(self, symbol: str) -> Optional[StructuredStockAnalysis]:
        """
        Get comprehensive stock analysis for a given symbol

        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'NVDA')

        Returns:
            StructuredStockAnalysis object or None if analysis fails
        """
        try:
            logger.info(f"Starting analysis for {symbol}")

            user_input = f"Can you provide an overview of the most recent news on the {symbol} stock?"

            # Get analysis from agent
            response = self.agent.invoke(
                {"messages": [HumanMessage(content=user_input)]}
            )

            # Extract structured response
            if "structured_response" in response and isinstance(
                response["structured_response"], StructuredStockAnalysis
            ):
                logger.info(f"Successfully extracted structured response for {symbol}")
                return response["structured_response"]

            logger.warning(
                f"No structured_response found in agent response for {symbol}"
            )
            return None

        except Exception as e:
            logger.error(f"Failed to get analysis for {symbol}: {e}")
            return None

    def validate_analysis(self, analysis: StructuredStockAnalysis) -> bool:
        """
        Validate that the analysis contains required data

        Args:
            analysis: StructuredStockAnalysis object

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check required fields
            required_fields = [
                "summary",
                "executive_summary",
                "positive_catalysts",
                "risk_factors",
                "disclaimer",
            ]

            for field in required_fields:
                if not getattr(analysis, field, "").strip():
                    logger.warning(f"Missing or empty required field: {field}")
                    return False

            # Validate sentiment
            if (
                not analysis.overall_sentiment
                or not analysis.overall_sentiment.sentiment
            ):
                logger.warning("Missing sentiment analysis")
                return False

            if analysis.overall_sentiment.sentiment not in [
                "Bullish",
                "Bearish",
                "Neutral",
            ]:
                logger.warning(
                    f"Invalid sentiment: {analysis.overall_sentiment.sentiment}"
                )
                return False

            # Validate news items impact levels
            for news_item in analysis.recent_news:
                if news_item.impact_level not in ["High", "Medium", "Low"]:
                    logger.warning(f"Invalid impact level: {news_item.impact_level}")
                    return False

            # Validate upcoming events
            valid_categories = [
                "Earnings",
                "Corporate_Actions",
                "Regulatory",
                "Strategic",
                "Industry",
                "Economic",
            ]
            valid_importance = ["High", "Medium", "Low"]

            for event in analysis.upcoming_events:
                if event.category not in valid_categories:
                    logger.warning(f"Invalid event category: {event.category}")
                    return False
                if event.importance not in valid_importance:
                    logger.warning(f"Invalid event importance: {event.importance}")
                    return False

            logger.info("Analysis validation passed")
            return True

        except Exception as e:
            logger.error(f"Error validating analysis: {e}")
            return False
