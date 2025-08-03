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


class SmartWatchlist(models.Model):
    """User's smart watchlist"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="watchlists")
    name = models.CharField(max_length=100, default="My Watchlist")
    description = models.TextField(blank=True)

    # Settings
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "-updated_at"]
        unique_together = ["user", "name"]

    def __str__(self):
        return f"{self.user.username}'s {self.name}"


class WatchlistItem(models.Model):
    """Individual items in a watchlist"""

    watchlist = models.ForeignKey(
        SmartWatchlist, on_delete=models.CASCADE, related_name="items"
    )
    security = models.ForeignKey(Security, on_delete=models.CASCADE)

    # User preferences for this item
    notes = models.TextField(blank=True)
    target_price = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )

    # Tracking
    added_at = models.DateTimeField(auto_now_add=True)
    position = models.PositiveIntegerField(default=0)  # For ordering

    class Meta:
        unique_together = ["watchlist", "security"]
        ordering = ["position", "added_at"]

    def __str__(self):
        return f"{self.security.symbol} in {self.watchlist.name}"


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


class SecurityNews(models.Model):
    """News articles related to securities"""

    RELEVANCE_CHOICES = [
        ("HIGH", "High"),
        ("MEDIUM", "Medium"),
        ("LOW", "Low"),
    ]

    security = models.ForeignKey(
        Security, on_delete=models.CASCADE, related_name="news"
    )
    source = models.ForeignKey(NewsSource, on_delete=models.CASCADE)

    # Article data
    title = models.CharField(max_length=500)
    summary = models.TextField()  # AI-generated or from source
    url = models.URLField(unique=True)
    author = models.CharField(max_length=200, blank=True)

    # Relevance and filtering
    relevance = models.CharField(
        max_length=10, choices=RELEVANCE_CHOICES, default="MEDIUM"
    )
    sentiment_score = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True
    )  # -1 to 1

    # Timestamps
    published_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published_at"]
        indexes = [
            models.Index(fields=["security", "-published_at"]),
            models.Index(fields=["security", "relevance", "-published_at"]),
        ]

    def __str__(self):
        return f"{self.security.symbol}: {self.title[:50]}..."


class Transaction(models.Model):
    """Transaction history for holdings (future feature)"""

    TRANSACTION_TYPES = [
        ("BUY", "Buy"),
        ("SELL", "Sell"),
        ("DIVIDEND", "Dividend"),
        ("SPLIT", "Stock Split"),
    ]

    holding = models.ForeignKey(
        Holding, on_delete=models.CASCADE, related_name="transactions"
    )
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)

    quantity = models.DecimalField(max_digits=12, decimal_places=6)
    price_per_share = models.DecimalField(max_digits=12, decimal_places=4)
    total_amount = models.DecimalField(max_digits=15, decimal_places=4)
    fees = models.DecimalField(max_digits=8, decimal_places=4, default=0)

    transaction_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-transaction_date", "-created_at"]

    def __str__(self):
        return f"{self.transaction_type} {self.quantity} {self.holding.security.symbol}"
