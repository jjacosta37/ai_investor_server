from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid


class Security(models.Model):
    """Base model for stocks and ETFs"""

    # # Polygon.io asset types - filtered for retail MVP
    # SECURITY_TYPES = [
    #     ("CS", "Common Stock"),
    #     ("ETF", "Exchange Traded Fund"),
    #     ("ADRC", "American Depository Receipt"),
    #     # Future expansion options:
    #     # ('PFD', 'Preferred Stock'),
    #     # ('ETN', 'Exchange Traded Note'),
    # ]

    # MVP filter - only these types will be processed
    MVP_ASSET_TYPES = ["CS", "ETF", "ADRC"]

    # Primary identifiers
    symbol = models.CharField(max_length=10, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    security_type = models.CharField(max_length=10)

    # Exchange and market data
    exchange = models.CharField(max_length=50, blank=True)
    sic_description = models.CharField(max_length=100, blank=True)

    # Visual assets
    logo_url = models.URLField(blank=True, help_text="URL to the company/fund logo")

    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["symbol"]
        indexes = [
            models.Index(fields=["symbol"]),
            models.Index(fields=["security_type", "is_active"]),
        ]

    def __str__(self):
        return f"{self.symbol} - {self.name}"


class SecurityFundamentals(models.Model):
    """Fundamental data for securities"""

    security = models.OneToOneField(
        Security, on_delete=models.CASCADE, related_name="fundamentals"
    )

    # Price data
    current_price = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    previous_close = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    day_change = models.DecimalField(max_digits=10, decimal_places=4, null=True)
    day_change_percent = models.DecimalField(max_digits=6, decimal_places=2, null=True)

    # Fundamental metrics
    market_cap = models.BigIntegerField(null=True, blank=True)
    pe_ratio = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    eps = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    dividend_yield = models.DecimalField(
        max_digits=6, decimal_places=4, null=True, blank=True
    )
    book_value = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    debt_to_equity = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True
    )
    roe = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Volume and trading data
    volume = models.BigIntegerField(null=True, blank=True)
    avg_volume = models.BigIntegerField(null=True, blank=True)

    # 52-week data
    week_52_high = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    week_52_low = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )

    # News summary
    news_summary = models.TextField(
        blank=True, help_text="High-level summary of recent news for this security"
    )
    news_summary_updated_at = models.DateTimeField(
        null=True, blank=True, help_text="When the news summary was last updated"
    )

    # Data freshness
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Fundamentals for {self.security.symbol}"


# class SmartWatchlist(models.Model):
#     """User's smart watchlist"""

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="watchlists")
#     name = models.CharField(max_length=100, default="My Watchlist")
#     description = models.TextField(blank=True)

#     # Settings
#     is_default = models.BooleanField(default=False)
#     is_active = models.BooleanField(default=True)

#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         ordering = ["-is_default", "-updated_at"]
#         unique_together = ["user", "name"]

#     def __str__(self):
#         return f"{self.user.username}'s {self.name}"


class WatchlistItem(models.Model):
    """Individual items in a watchlist"""

    # watchlist = models.ForeignKey(
    #     SmartWatchlist, on_delete=models.CASCADE, related_name="items"
    # )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="watchlistitems"
    )
    security = models.ForeignKey(Security, on_delete=models.CASCADE)

    # Tracking
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "security"]
        ordering = ["added_at"]

    def __str__(self):
        return f"{self.security.symbol} in {self.user.username}'s watchlist"


class Holding(models.Model):
    """User's actual stock/ETF holdings"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="holdings")
    security = models.ForeignKey(Security, on_delete=models.CASCADE)

    # Position data
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        validators=[MinValueValidator(Decimal("0.000001"))],
    )
    average_cost = models.DecimalField(max_digits=12, decimal_places=4)
    total_cost = models.DecimalField(max_digits=15, decimal_places=4)

    # Tracking
    first_purchase_date = models.DateField()
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Optional metadata
    notes = models.TextField(blank=True)
    broker = models.CharField(max_length=100, blank=True)

    class Meta:
        unique_together = ["user", "security"]
        ordering = ["-total_cost"]

    def __str__(self):
        return (
            f"{self.user.username} - {self.quantity} shares of {self.security.symbol}"
        )

    @property
    def current_value(self):
        """Calculate current market value"""
        if self.security.fundamentals and self.security.fundamentals.current_price:
            return self.quantity * self.security.fundamentals.current_price
        return None

    @property
    def unrealized_gain_loss(self):
        """Calculate unrealized P&L"""
        current_val = self.current_value
        if current_val:
            return current_val - self.total_cost
        return None


class NewsSource(models.Model):
    """News sources for aggregation"""

    name = models.CharField(max_length=100, unique=True)
    base_url = models.URLField()
    is_active = models.BooleanField(default=True)
    reliability_score = models.PositiveIntegerField(default=5)  # 1-10 scale

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class OverallSentiment(models.Model):
    """Overall sentiment analysis for securities"""

    SENTIMENT_CHOICES = [
        ("Bullish", "Bullish"),
        ("Bearish", "Bearish"),
        ("Neutral", "Neutral"),
    ]

    CONFIDENCE_CHOICES = [
        ("High", "High"),
        ("Medium", "Medium"),
        ("Low", "Low"),
    ]

    sentiment = models.CharField(max_length=10, choices=SENTIMENT_CHOICES)
    rationale = models.TextField(
        help_text="Explanation for the sentiment classification"
    )
    confidence_level = models.CharField(
        max_length=10, choices=CONFIDENCE_CHOICES, blank=True, null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Overall Sentiment"
        verbose_name_plural = "Overall Sentiments"

    def __str__(self):
        return f"{self.sentiment} - {self.rationale[:50]}..."


class SecurityNewsSummary(models.Model):
    """Comprehensive news summary for securities (1:1 with Security)"""

    security = models.OneToOneField(
        Security, on_delete=models.CASCADE, related_name="news_summary"
    )

    # Summary fields
    executive_summary = models.TextField(
        help_text="Comprehensive 3-4 paragraph overview of recent developments"
    )
    summary = models.TextField(
        help_text="Quick 1-2 sentence overview of current situation"
    )

    # Analysis fields
    positive_catalysts = models.TextField(
        help_text="2-3 paragraph summary of upside drivers"
    )
    risk_factors = models.TextField(
        help_text="2-3 paragraph summary of potential headwinds"
    )

    # Sentiment relationship
    overall_sentiment = models.ForeignKey(
        OverallSentiment, on_delete=models.CASCADE, related_name="news_summaries"
    )

    # Metrics as flexible JSON
    key_metrics = models.JSONField(
        default=dict, blank=True, help_text="Key financial metrics as key-value pairs"
    )

    disclaimer = models.TextField(
        help_text="Standard professional disclaimer about analysis"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Security News Summary"
        verbose_name_plural = "Security News Summaries"
        indexes = [
            models.Index(fields=["security", "-updated_at"]),
        ]

    def __str__(self):
        return f"News Summary for {self.security.symbol}"


class NewsItem(models.Model):
    """Enhanced news items for securities - replaces SecurityNews"""

    IMPACT_LEVEL_CHOICES = [
        ("High", "High"),
        ("Medium", "Medium"),
        ("Low", "Low"),
    ]

    security = models.ForeignKey(
        Security, on_delete=models.CASCADE, related_name="news_items"
    )

    # Core news fields
    headline = models.CharField(max_length=500, help_text="Concise, factual title")
    date = models.DateField(help_text="Publication date of the news")
    source = models.CharField(max_length=100, help_text="News source name")
    url = models.URLField(help_text="URL to original article")
    favicon = models.URLField(blank=True, help_text="Favicon URL of the news source")

    # Analysis fields
    impact_level = models.CharField(
        max_length=10,
        choices=IMPACT_LEVEL_CHOICES,
        help_text="Impact assessment: High, Medium, or Low",
    )
    summary = models.TextField(
        help_text="2-3 sentences explaining the news and its implications"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "News Item"
        verbose_name_plural = "News Items"
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["security", "-date"]),
            models.Index(fields=["security", "impact_level", "-date"]),
        ]

    def __str__(self):
        return f"{self.security.symbol}: {self.headline[:50]}..."


class UpcomingEvent(models.Model):
    """Upcoming events and catalysts for securities"""

    CATEGORY_CHOICES = [
        ("Earnings", "Earnings"),
        ("Corporate_Actions", "Corporate Actions"),
        ("Regulatory", "Regulatory"),
        ("Strategic", "Strategic"),
        ("Industry", "Industry"),
        ("Economic", "Economic"),
    ]

    IMPORTANCE_CHOICES = [
        ("High", "High"),
        ("Medium", "Medium"),
        ("Low", "Low"),
    ]

    security = models.ForeignKey(
        Security, on_delete=models.CASCADE, related_name="upcoming_events"
    )

    # Event details
    event = models.TextField(help_text="Clear description of the catalyst")
    date = models.CharField(
        max_length=50,
        help_text="Specific date or timeframe (e.g., 'Q1 2025', 'Late February 2025')",
    )
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, help_text="Event category"
    )
    importance = models.CharField(
        max_length=10, choices=IMPORTANCE_CHOICES, help_text="Importance level"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Upcoming Event"
        verbose_name_plural = "Upcoming Events"
        ordering = ["date", "-importance"]
        indexes = [
            models.Index(fields=["security", "category"]),
            models.Index(fields=["security", "importance"]),
        ]

    def __str__(self):
        return f"{self.security.symbol}: {self.event[:50]}... ({self.date})"


class KeyHighlight(models.Model):
    """Individual key highlights for security news summaries"""

    security_news_summary = models.ForeignKey(
        SecurityNewsSummary, on_delete=models.CASCADE, related_name="key_highlights"
    )

    highlight = models.TextField(help_text="Individual highlight point")
    order = models.PositiveIntegerField(
        default=0, help_text="Order for displaying highlights"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Key Highlight"
        verbose_name_plural = "Key Highlights"
        ordering = ["order", "created_at"]
        indexes = [
            models.Index(fields=["security_news_summary", "order"]),
        ]

    def __str__(self):
        return f"{self.security_news_summary.security.symbol}: {self.highlight[:50]}..."
