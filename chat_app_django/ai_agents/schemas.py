"""
Shared Pydantic models for stock analysis data structures.
Used by both AI agents and Django model transformation layers.
"""

from typing import List, Dict
from pydantic import BaseModel, Field


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