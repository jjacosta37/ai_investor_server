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

            # The langgraph agent with response_format should return structured data
            # Let's check different ways the response might be structured

            # Method 1: Check if response has structured content directly
            if hasattr(response, "content") and isinstance(response.content, dict):
                try:
                    analysis = StructuredStockAnalysis(**response.content)
                    logger.info(f"Successfully parsed structured response for {symbol}")
                    return analysis
                except Exception as e:
                    logger.error(
                        f"Failed to create StructuredStockAnalysis from response.content: {e}"
                    )

            # Method 2: Check messages for structured content
            if "messages" in response:
                for message in reversed(response["messages"]):
                    # Check if message has structured content
                    if hasattr(message, "content"):
                        if isinstance(message.content, dict):
                            try:
                                analysis = StructuredStockAnalysis(**message.content)
                                logger.info(
                                    f"Successfully parsed structured message content for {symbol}"
                                )
                                return analysis
                            except Exception as e:
                                logger.debug(
                                    f"Message content not structured properly: {e}"
                                )
                                continue
                        elif hasattr(message, "tool_calls") and message.tool_calls:
                            # Check tool calls for structured output
                            for tool_call in message.tool_calls:
                                if hasattr(tool_call, "args") and isinstance(
                                    tool_call.args, dict
                                ):
                                    try:
                                        analysis = StructuredStockAnalysis(
                                            **tool_call.args
                                        )
                                        logger.info(
                                            f"Successfully parsed tool call args for {symbol}"
                                        )
                                        return analysis
                                    except Exception as e:
                                        logger.debug(
                                            f"Tool call args not structured properly: {e}"
                                        )
                                        continue
            
            # Method 3: Check for artifact content in messages (common in structured outputs)
            if "messages" in response:
                for message in response["messages"]:
                    if hasattr(message, "content") and isinstance(message.content, str):
                        # Try to parse JSON from string content
                        import json
                        try:
                            # Look for JSON-like content in the message
                            content_str = message.content.strip()
                            if content_str.startswith('{') and content_str.endswith('}'):
                                content_dict = json.loads(content_str)
                                analysis = StructuredStockAnalysis(**content_dict)
                                logger.info(f"Successfully parsed JSON content for {symbol}")
                                return analysis
                        except (json.JSONDecodeError, Exception) as e:
                            logger.debug(f"Failed to parse JSON from message content: {e}")
                            continue
            
            # Method 4: Check if the response itself is a StructuredStockAnalysis object
            if isinstance(response, StructuredStockAnalysis):
                logger.info(f"Response is already a StructuredStockAnalysis for {symbol}")
                return response
            
            # Method 5: Try to extract from any dict-like structure in the response
            def extract_dict_from_response(obj, path=""):
                """Recursively search for dict structures that might contain our data"""
                if isinstance(obj, dict):
                    try:
                        # Check if this dict can be converted to StructuredStockAnalysis
                        analysis = StructuredStockAnalysis(**obj)
                        logger.info(f"Found structured data at path: {path}")
                        return analysis
                    except Exception:
                        # Recursively check nested dicts
                        for key, value in obj.items():
                            result = extract_dict_from_response(value, f"{path}.{key}")
                            if result:
                                return result
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        result = extract_dict_from_response(item, f"{path}[{i}]")
                        if result:
                            return result
                elif hasattr(obj, '__dict__'):
                    # Check object attributes
                    return extract_dict_from_response(obj.__dict__, f"{path}.__dict__")
                return None
            
            extracted = extract_dict_from_response(response)
            if extracted:
                return extracted
            
            logger.warning(f"Could not extract structured analysis from response for {symbol}")
            logger.debug(f"Response type: {type(response)}")
            logger.debug(f"Response keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
            
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
