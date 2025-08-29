"""
Data transformation layer for converting Pydantic models to Django model instances.
"""

import logging
from datetime import datetime, date
from typing import List, Optional
from django.db import transaction
from django.utils.dateparse import parse_date
from django.conf import settings

from ai_agents.schemas.news_schemas import StructuredStockAnalysis
from securities.models import (
    Security,
    OverallSentiment,
    SecurityNewsSummary,
    NewsItem,
    UpcomingEvent,
    KeyHighlight,
)

# Configurable limits for data retention
MAX_NEWS_ITEMS_PER_SECURITY = getattr(settings, "MAX_NEWS_ITEMS_PER_SECURITY", 20)
MAX_UPCOMING_EVENTS_PER_SECURITY = getattr(
    settings, "MAX_UPCOMING_EVENTS_PER_SECURITY", 20
)

logger = logging.getLogger(__name__)


class NewsDataTransformer:
    """Transform Pydantic analysis data to Django model instances"""

    @staticmethod
    def parse_date_string(date_str: str) -> Optional[date]:
        """
        Parse various date string formats to date object

        Args:
            date_str: Date string in various formats

        Returns:
            date object or None if parsing fails
        """
        if not date_str:
            return None

        # Try common date formats
        formats = [
            "%Y-%m-%d",  # 2024-01-15
            "%m/%d/%Y",  # 01/15/2024
            "%B %d, %Y",  # January 15, 2024
            "%b %d, %Y",  # Jan 15, 2024
            "%Y-%m-%d %H:%M:%S",  # Full datetime
        ]

        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_str.strip(), fmt).date()
                return parsed_date
            except ValueError:
                continue

        # If no format works, try Django's parse_date
        parsed_date = parse_date(date_str.strip())
        if parsed_date:
            return parsed_date

        # For relative dates like "Q1 2025", "Late February 2025", return None
        # These will be stored as-is in the event date field
        logger.warning(f"Could not parse date: {date_str}")
        return None

    @staticmethod
    @transaction.atomic
    def save_analysis_to_db(
        security: Security,
        analysis: StructuredStockAnalysis,
        max_news_items: int = None,
        max_events: int = None,
        skip_cleanup: bool = False,
    ) -> SecurityNewsSummary:
        """
        Save complete analysis to database

        Args:
            security: Security instance
            analysis: StructuredStockAnalysis from AI agent
            max_news_items: Override for maximum news items (uses default if None)
            max_events: Override for maximum events (uses default if None)
            skip_cleanup: If True, skip cleanup operations

        Returns:
            SecurityNewsSummary instance
        """
        try:
            logger.info(f"Saving analysis for {security.symbol}")

            # 1. Create or reuse OverallSentiment (avoid duplicates)
            sentiment, sentiment_created = OverallSentiment.objects.get_or_create(
                sentiment=analysis.overall_sentiment.sentiment,
                rationale=analysis.overall_sentiment.rationale,
                defaults={
                    "confidence_level": getattr(
                        analysis.overall_sentiment, "confidence_level", None
                    )
                },
            )

            if sentiment_created:
                logger.debug(f"Created new sentiment record for {security.symbol}")
            else:
                logger.debug(f"Reused existing sentiment record for {security.symbol}")

            # 2. Create or update SecurityNewsSummary
            news_summary, created = SecurityNewsSummary.objects.update_or_create(
                security=security,
                defaults={
                    "executive_summary": analysis.executive_summary,
                    "summary": analysis.summary,
                    "positive_catalysts": analysis.positive_catalysts,
                    "risk_factors": analysis.risk_factors,
                    "overall_sentiment": sentiment,
                    "key_metrics": analysis.key_metrics,
                    "disclaimer": analysis.disclaimer,
                },
            )

            if created:
                logger.info(f"Created new SecurityNewsSummary for {security.symbol}")
            else:
                logger.info(f"Updated SecurityNewsSummary for {security.symbol}")

            # 3. Clear and recreate KeyHighlights
            KeyHighlight.objects.filter(security_news_summary=news_summary).delete()

            for order, highlight in enumerate(analysis.key_highlights):
                KeyHighlight.objects.create(
                    security_news_summary=news_summary, highlight=highlight, order=order
                )

            logger.info(f"Created {len(analysis.key_highlights)} key highlights")

            # 4. Add new NewsItems (avoid duplicates by URL) and manage retention
            news_items_created = 0
            for news_data in analysis.recent_news:
                # Check if news item already exists by URL
                if not NewsItem.objects.filter(url=news_data.url).exists():
                    parsed_date = NewsDataTransformer.parse_date_string(news_data.date)

                    # Use today if date parsing fails
                    if not parsed_date:
                        parsed_date = date.today()
                        logger.warning(
                            f"Using today's date for news item: {news_data.headline}"
                        )

                    NewsItem.objects.create(
                        security=security,
                        headline=news_data.headline,
                        date=parsed_date,
                        source=news_data.source,
                        url=news_data.url,
                        favicon=news_data.favicon,
                        impact_level=news_data.impact_level,
                        summary=news_data.summary,
                    )
                    news_items_created += 1
                else:
                    logger.debug(f"Skipping duplicate news item: {news_data.url}")

            logger.info(f"Created {news_items_created} new news items")

            # Clean up excess NewsItems to maintain rolling window
            if not skip_cleanup:
                effective_max_news = (
                    max_news_items
                    if max_news_items is not None
                    else MAX_NEWS_ITEMS_PER_SECURITY
                )
                NewsDataTransformer.cleanup_excess_news_items(
                    security, effective_max_news
                )

            # 5. Add new UpcomingEvents and manage retention
            events_created = 0
            for event_data in analysis.upcoming_events:
                UpcomingEvent.objects.create(
                    security=security,
                    event=event_data.event,
                    date=event_data.date,  # Store as string for flexible formats
                    category=event_data.category,
                    importance=event_data.importance,
                )
                events_created += 1

            logger.info(f"Created {events_created} upcoming events")

            # Clean up excess UpcomingEvents to maintain rolling window
            if not skip_cleanup:
                effective_max_events = (
                    max_events
                    if max_events is not None
                    else MAX_UPCOMING_EVENTS_PER_SECURITY
                )
                NewsDataTransformer.cleanup_excess_upcoming_events(
                    security, effective_max_events
                )

            logger.info(f"Successfully saved analysis for {security.symbol}")
            return news_summary

        except Exception as e:
            logger.error(f"Error saving analysis for {security.symbol}: {e}")
            raise

    @staticmethod
    def get_watchlisted_securities() -> List[Security]:
        """
        Get all unique securities that are in any user's watchlist

        Returns:
            List of Security instances
        """
        try:
            from securities.models import WatchlistItem

            # Get unique security IDs from watchlist items
            security_ids = WatchlistItem.objects.values_list(
                "security_id", flat=True
            ).distinct()

            # Get the Security objects
            securities = Security.objects.filter(id__in=security_ids, is_active=True)

            logger.info(f"Found {securities.count()} securities in watchlists")
            return list(securities)

        except Exception as e:
            logger.error(f"Error getting watchlisted securities: {e}")
            return []

    @staticmethod
    def get_security_by_symbol(symbol: str) -> Optional[Security]:
        """
        Get Security instance by symbol

        Args:
            symbol: Stock symbol

        Returns:
            Security instance or None
        """
        try:
            return Security.objects.get(symbol=symbol.upper(), is_active=True)
        except Security.DoesNotExist:
            logger.warning(f"Security not found: {symbol}")
            return None
        except Exception as e:
            logger.error(f"Error getting security {symbol}: {e}")
            return None

    @staticmethod
    def cleanup_excess_news_items(security: Security, max_items: int):
        """
        Clean up excess NewsItems for a security, keeping only the most recent ones

        Args:
            security: Security instance
            max_items: Maximum number of items to keep
        """
        try:
            total_count = NewsItem.objects.filter(security=security).count()

            if total_count > max_items:
                excess_count = total_count - max_items

                # Get IDs of oldest items to delete
                oldest_items = (
                    NewsItem.objects.filter(security=security)
                    .order_by("created_at")
                    .values_list("id", flat=True)[:excess_count]
                )

                # Delete the oldest items
                deleted_count = NewsItem.objects.filter(
                    id__in=list(oldest_items)
                ).delete()[0]

                logger.info(
                    f"Cleaned up {deleted_count} old news items for {security.symbol}, "
                    f"keeping {max_items} most recent"
                )

        except Exception as e:
            logger.error(f"Error cleaning up news items for {security.symbol}: {e}")

    @staticmethod
    def cleanup_excess_upcoming_events(security: Security, max_items: int):
        """
        Clean up excess UpcomingEvents for a security, keeping only the most recent ones

        Args:
            security: Security instance
            max_items: Maximum number of items to keep
        """
        try:
            total_count = UpcomingEvent.objects.filter(security=security).count()

            if total_count > max_items:
                excess_count = total_count - max_items

                # Get IDs of oldest items to delete
                oldest_items = (
                    UpcomingEvent.objects.filter(security=security)
                    .order_by("created_at")
                    .values_list("id", flat=True)[:excess_count]
                )

                # Delete the oldest items
                deleted_count = UpcomingEvent.objects.filter(
                    id__in=list(oldest_items)
                ).delete()[0]

                logger.info(
                    f"Cleaned up {deleted_count} old upcoming events for {security.symbol}, "
                    f"keeping {max_items} most recent"
                )

        except Exception as e:
            logger.error(
                f"Error cleaning up upcoming events for {security.symbol}: {e}"
            )
