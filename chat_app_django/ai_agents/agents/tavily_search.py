from typing import Any, Dict, Optional, List
from langchain.chat_models import init_chat_model
from langchain_tavily import TavilySearch, TavilyCrawl
from langchain.schema import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
from ai_agents.prompts.prompts import (
    analysis_prompt,
    news_summary_prompt,
    structured_analysis_prompt,
)
from ai_agents.schemas import StructuredStockAnalysis
from ai_agents.services import StockAnalysisService

load_dotenv()


def main():
    """Test the StockAnalysisService"""
    
    service = StockAnalysisService()
    
    # Test with NVDA
    symbol = "NVDA"
    print(f"Getting analysis for {symbol}...")
    
    analysis = service.get_stock_analysis(symbol)
    
    if analysis:
        print(f"Analysis received for {symbol}")
        print(f"Summary: {analysis.summary}")
        print(f"Sentiment: {analysis.overall_sentiment.sentiment}")
        print(f"Recent news items: {len(analysis.recent_news)}")
        print(f"Upcoming events: {len(analysis.upcoming_events)}")
        
        is_valid = service.validate_analysis(analysis)
        print(f"Analysis is valid: {is_valid}")
    else:
        print(f"Failed to get analysis for {symbol}")


if __name__ == "__main__":
    main()
