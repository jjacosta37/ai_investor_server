from rest_framework import serializers
from .models import (
    Security,
    SecurityFundamentals,
    WatchlistItem,
    Holding,
    OverallSentiment,
    SecurityNewsSummary,
    NewsItem,
    UpcomingEvent,
    KeyHighlight,
)


class OverallSentimentSerializer(serializers.ModelSerializer):
    """Serializer for OverallSentiment model"""

    class Meta:
        model = OverallSentiment
        fields = ["sentiment", "rationale", "confidence_level"]
        read_only_fields = ["sentiment", "rationale", "confidence_level"]


class KeyHighlightSerializer(serializers.ModelSerializer):
    """Serializer for KeyHighlight model"""

    class Meta:
        model = KeyHighlight
        fields = ["highlight", "order"]
        read_only_fields = ["highlight", "order"]


class NewsItemSerializer(serializers.ModelSerializer):
    """Serializer for NewsItem model"""

    class Meta:
        model = NewsItem
        fields = [
            "headline",
            "date",
            "source",
            "url",
            "favicon",
            "impact_level",
            "summary",
        ]
        read_only_fields = [
            "headline",
            "date",
            "source",
            "url",
            "favicon",
            "impact_level",
            "summary",
        ]


class UpcomingEventSerializer(serializers.ModelSerializer):
    """Serializer for UpcomingEvent model"""

    class Meta:
        model = UpcomingEvent
        fields = ["event", "date", "category", "importance"]
        read_only_fields = ["event", "date", "category", "importance"]


class SecurityNewsSummarySerializer(serializers.ModelSerializer):
    """Serializer for SecurityNewsSummary model"""

    overall_sentiment = OverallSentimentSerializer(read_only=True)

    class Meta:
        model = SecurityNewsSummary
        fields = [
            "executive_summary",
            "summary",
            "positive_catalysts",
            "risk_factors",
            "overall_sentiment",
            "key_metrics",
            "disclaimer",
            "updated_at",
        ]
        read_only_fields = [
            "executive_summary",
            "summary",
            "positive_catalysts",
            "risk_factors",
            "overall_sentiment",
            "key_metrics",
            "disclaimer",
            "updated_at",
        ]


class SecurityFundamentalsSerializer(serializers.ModelSerializer):
    """Serializer for SecurityFundamentals model"""

    class Meta:
        model = SecurityFundamentals
        fields = [
            "current_price",
            "previous_close",
            "day_change",
            "day_change_percent",
            "market_cap",
            "pe_ratio",
            "eps",
            "dividend_yield",
            "book_value",
            "debt_to_equity",
            "roe",
            "volume",
            "avg_volume",
            "week_52_high",
            "week_52_low",
            "news_summary",
            "news_summary_updated_at",
            "last_updated",
        ]
        read_only_fields = [
            "current_price",
            "previous_close",
            "day_change",
            "day_change_percent",
            "market_cap",
            "pe_ratio",
            "eps",
            "dividend_yield",
            "book_value",
            "debt_to_equity",
            "roe",
            "volume",
            "avg_volume",
            "week_52_high",
            "week_52_low",
            "news_summary",
            "news_summary_updated_at",
            "last_updated",
        ]


class SecurityListSerializer(serializers.ModelSerializer):
    """Serializer for security list view (with fundamentals data)"""

    current_price = serializers.SerializerMethodField()
    previous_close = serializers.SerializerMethodField()
    day_change = serializers.SerializerMethodField()
    day_change_percent = serializers.SerializerMethodField()
    market_cap = serializers.SerializerMethodField()
    pe_ratio = serializers.SerializerMethodField()
    eps = serializers.SerializerMethodField()
    dividend_yield = serializers.SerializerMethodField()
    volume = serializers.SerializerMethodField()
    avg_volume = serializers.SerializerMethodField()
    week_52_high = serializers.SerializerMethodField()
    week_52_low = serializers.SerializerMethodField()
    book_value = serializers.SerializerMethodField()
    debt_to_equity = serializers.SerializerMethodField()
    roe = serializers.SerializerMethodField()
    news_summary = serializers.SerializerMethodField()

    class Meta:
        model = Security
        fields = [
            "symbol",
            "name",
            "security_type",
            "exchange",
            "current_price",
            "previous_close",
            "day_change",
            "day_change_percent",
            "market_cap",
            "pe_ratio",
            "eps",
            "dividend_yield",
            "volume",
            "avg_volume",
            "week_52_high",
            "week_52_low",
            "book_value",
            "debt_to_equity",
            "roe",
            "news_summary",
            "logo_url",
            "is_active",
        ]
        read_only_fields = [
            "symbol",
            "name",
            "security_type",
            "exchange",
            "logo_url",
            "is_active",
        ]

    def get_current_price(self, obj):
        """Get current price from fundamentals if available"""
        if hasattr(obj, "fundamentals") and obj.fundamentals:
            return obj.fundamentals.current_price
        return None

    def get_previous_close(self, obj):
        """Get previous close from fundamentals if available"""
        if hasattr(obj, "fundamentals") and obj.fundamentals:
            return obj.fundamentals.previous_close
        return None

    def get_day_change(self, obj):
        """Get day change from fundamentals if available"""
        if hasattr(obj, "fundamentals") and obj.fundamentals:
            return obj.fundamentals.day_change
        return None

    def get_day_change_percent(self, obj):
        """Get day change percentage from fundamentals if available"""
        if hasattr(obj, "fundamentals") and obj.fundamentals:
            return obj.fundamentals.day_change_percent
        return None

    def get_market_cap(self, obj):
        """Get market cap from fundamentals if available"""
        if hasattr(obj, "fundamentals") and obj.fundamentals:
            return obj.fundamentals.market_cap
        return None

    def get_pe_ratio(self, obj):
        """Get P/E ratio from fundamentals if available"""
        if hasattr(obj, "fundamentals") and obj.fundamentals:
            return obj.fundamentals.pe_ratio
        return None

    def get_eps(self, obj):
        """Get EPS from fundamentals if available"""
        if hasattr(obj, "fundamentals") and obj.fundamentals:
            return obj.fundamentals.eps
        return None

    def get_dividend_yield(self, obj):
        """Get dividend yield from fundamentals if available"""
        if hasattr(obj, "fundamentals") and obj.fundamentals:
            return obj.fundamentals.dividend_yield
        return None

    def get_volume(self, obj):
        """Get volume from fundamentals if available"""
        if hasattr(obj, "fundamentals") and obj.fundamentals:
            return obj.fundamentals.volume
        return None

    def get_avg_volume(self, obj):
        """Get average volume from fundamentals if available"""
        if hasattr(obj, "fundamentals") and obj.fundamentals:
            return obj.fundamentals.avg_volume
        return None

    def get_week_52_high(self, obj):
        """Get 52-week high from fundamentals if available"""
        if hasattr(obj, "fundamentals") and obj.fundamentals:
            return obj.fundamentals.week_52_high
        return None

    def get_week_52_low(self, obj):
        """Get 52-week low from fundamentals if available"""
        if hasattr(obj, "fundamentals") and obj.fundamentals:
            return obj.fundamentals.week_52_low
        return None

    def get_book_value(self, obj):
        """Get book value from fundamentals if available"""
        if hasattr(obj, "fundamentals") and obj.fundamentals:
            return obj.fundamentals.book_value
        return None

    def get_debt_to_equity(self, obj):
        """Get debt-to-equity ratio from fundamentals if available"""
        if hasattr(obj, "fundamentals") and obj.fundamentals:
            return obj.fundamentals.debt_to_equity
        return None

    def get_roe(self, obj):
        """Get ROE from fundamentals if available"""
        if hasattr(obj, "fundamentals") and obj.fundamentals:
            return obj.fundamentals.roe
        return None

    def get_news_summary(self, obj):
        """Get news summary from fundamentals if available"""
        if hasattr(obj, "fundamentals") and obj.fundamentals:
            return obj.fundamentals.news_summary
        return None


class SecurityDetailSerializer(serializers.ModelSerializer):
    """Serializer for security detail view (complete data)"""

    fundamentals = SecurityFundamentalsSerializer(read_only=True)

    class Meta:
        model = Security
        fields = [
            "symbol",
            "name",
            "security_type",
            "exchange",
            "sic_description",
            "logo_url",
            "is_active",
            "created_at",
            "updated_at",
            "fundamentals",
        ]
        read_only_fields = [
            "symbol",
            "name",
            "security_type",
            "exchange",
            "sic_description",
            "logo_url",
            "is_active",
            "created_at",
            "updated_at",
        ]


class WatchlistItemSerializer(serializers.ModelSerializer):
    """Serializer for WatchlistItem model"""

    security = SecurityListSerializer(read_only=True)
    security_symbol = serializers.CharField(write_only=True)
    security_news_summary = serializers.SerializerMethodField()
    latest_news = serializers.SerializerMethodField()
    key_highlights = serializers.SerializerMethodField()
    upcoming_events = serializers.SerializerMethodField()

    class Meta:
        model = WatchlistItem
        fields = [
            "id",
            "security",
            "security_symbol",
            "added_at",
            "security_news_summary",
            "latest_news",
            "key_highlights",
            "upcoming_events",
        ]
        read_only_fields = [
            "id",
            "added_at",
        ]

    def create(self, validated_data):
        """Create a new watchlist item"""
        security_symbol = validated_data.pop("security_symbol")
        user = self.context["request"].user

        try:
            security = Security.objects.get(
                symbol__iexact=security_symbol, is_active=True
            )
        except Security.DoesNotExist:
            raise serializers.ValidationError(
                {
                    "security_symbol": f"Security with symbol '{security_symbol}' not found or is inactive."
                }
            )

        # Check if already in watchlist
        if WatchlistItem.objects.filter(user=user, security=security).exists():
            raise serializers.ValidationError(
                {
                    "security_symbol": f"Security '{security_symbol}' is already in your watchlist."
                }
            )

        validated_data["security"] = security
        validated_data["user"] = user

        return super().create(validated_data)

    def get_security_news_summary(self, obj):
        """Get SecurityNewsSummary data for the security"""
        if hasattr(obj.security, "news_summary") and obj.security.news_summary:
            return SecurityNewsSummarySerializer(obj.security.news_summary).data
        return None

    def get_latest_news(self, obj):
        """Get the 3 most recent news items for the security"""
        latest_news = obj.security.news_items.all()[:3]
        return NewsItemSerializer(latest_news, many=True).data

    def get_key_highlights(self, obj):
        """Get key highlights for the security"""
        if hasattr(obj.security, "news_summary") and obj.security.news_summary:
            highlights = obj.security.news_summary.key_highlights.all()
            return KeyHighlightSerializer(highlights, many=True).data
        return []

    def get_upcoming_events(self, obj):
        """Get upcoming events for the security"""
        events = obj.security.upcoming_events.all()
        return UpcomingEventSerializer(events, many=True).data


class HoldingWithCompositionSerializer(serializers.Serializer):
    """Serializer for HoldingWithComposition objects from PortfolioService"""

    id = serializers.CharField(source="holding.id", read_only=True)
    security = SecurityListSerializer(source="holding.security", read_only=True)
    quantity = serializers.DecimalField(
        source="holding.quantity", max_digits=12, decimal_places=6, read_only=True
    )
    average_cost = serializers.DecimalField(
        source="holding.average_cost", max_digits=12, decimal_places=4, read_only=True
    )
    total_cost = serializers.DecimalField(
        source="holding.total_cost", max_digits=15, decimal_places=4, read_only=True
    )
    current_value = serializers.DecimalField(
        max_digits=15, decimal_places=4, read_only=True
    )
    unrealized_gain_loss = serializers.DecimalField(
        max_digits=15, decimal_places=4, read_only=True
    )
    unrealized_gain_loss_percent = serializers.FloatField(read_only=True)
    portfolio_weight_percent = serializers.FloatField(read_only=True)
    first_purchase_date = serializers.DateField(
        source="holding.first_purchase_date", read_only=True
    )
    last_updated = serializers.DateTimeField(
        source="holding.last_updated", read_only=True
    )
    notes = serializers.CharField(source="holding.notes", read_only=True)
    broker = serializers.CharField(source="holding.broker", read_only=True)
