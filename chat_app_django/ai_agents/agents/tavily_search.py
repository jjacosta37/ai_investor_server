from typing import Any, Dict, Optional, List
import datetime

from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch, TavilyCrawl
from langchain.schema import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
from prompts import analysis_prompt, news_summary_prompt, structured_analysis_prompt
from pydantic import BaseModel, Field

load_dotenv()

REACT_MODEL = "claude-sonnet-4-20250514"


def main():

    class NewsItem(BaseModel):
        """Individual news item with impact assessment"""

        headline: str = Field(description="Brief headline or title of the news")
        date: str = Field(description="Publication date of the news")
        source: str = Field(description="Source of the news (e.g., Reuters, Bloomberg)")
        url: str = Field(description="URL link to the original news article")
        impact_level: str = Field(description="Impact assessment: High, Medium, or Low")
        summary: str = Field(
            description="Brief summary of the news and its implications"
        )

    class SentimentAnalysis(BaseModel):
        """Structured sentiment analysis with separate sentiment and rationale"""

        sentiment: str = Field(
            description="Overall sentiment classification: Bullish, Bearish, or Neutral"
        )
        rationale: str = Field(
            description="Brief explanation for the sentiment classification"
        )

    class UpcomingEvent(BaseModel):
        """Individual upcoming event with categorization"""

        event: str = Field(description="Description of the upcoming event")
        date: str = Field(description="Expected date or timeframe")
        category: str = Field(
            description="Event category: Earnings, Corporate_Actions, Regulatory, Strategic, Industry, Economic"
        )
        importance: str = Field(description="Importance level: High, Medium, Low")

    class StructuredStockAnalysis(BaseModel):
        """Structured response format for stock analysis with both summary and comprehensive sections"""

        # Summary Section (for quick overview)
        summary: str = Field(
            description="Quick 1-2 sentence overview of the stock's current situation and recent developments"
        )
        key_highlights: List[str] = Field(
            description="Top 3-5 most important developments in bullet format"
        )
        overall_sentiment: SentimentAnalysis = Field(
            description="Structured sentiment analysis with classification and rationale"
        )

        # Comprehensive Section (detailed analysis)
        executive_summary: str = Field(
            description="Comprehensive executive summary with key developments and current situation"
        )
        recent_news: List[NewsItem] = Field(
            description="List of recent news items with impact assessment"
        )
        key_metrics: Dict[str, str] = Field(
            description="Key financial metrics when available (price, market cap, volume, etc.)"
        )
        positive_catalysts: str = Field(
            description="Summary of factors driving potential upside"
        )
        risk_factors: str = Field(
            description="Summary of factors that could negatively impact the stock"
        )
        upcoming_events: List[UpcomingEvent] = Field(
            description="Upcoming catalysts and events to watch, categorized by type"
        )
        disclaimer: str = Field(
            description="Professional disclaimer about the analysis"
        )

    llm = init_chat_model(model=REACT_MODEL, temperature=0, max_tokens=10000)

    # Initialize Tavily Search Tool
    tavily_search_tool = TavilySearch(
        max_results=5,
        topic="general",
    )

    # Set up Prompt with structured analysis capabilities
    prompt = structured_analysis_prompt

    # Create an agent that can use tools with structured response format
    agent = create_react_agent(
        model=llm,
        tools=[tavily_search_tool],
        prompt=prompt,
        response_format=StructuredStockAnalysis,
    )

    # # Create an Agent Executor to handle tool execution
    # agent_executor = AgentExecutor(agent=agent, tools=[tavily_search_tool, tavily_crawl_tool], verbose=True)

    user_input = (
        "Can you provide an overview of the most recent news on the NVDA stock??"
    )

    # Construct input properly as a dictionary
    response = agent.invoke({"messages": [HumanMessage(content=user_input)]})

    for m in response["messages"]:
        m.pretty_print()


if __name__ == "__main__":
    main()
