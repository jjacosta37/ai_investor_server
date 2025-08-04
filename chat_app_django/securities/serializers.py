from rest_framework import serializers
from .models import Security, SecurityFundamentals


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
    """Serializer for security list view (minimal data)"""
    
    current_price = serializers.SerializerMethodField()
    day_change_percent = serializers.SerializerMethodField()
    market_cap = serializers.SerializerMethodField()
    
    class Meta:
        model = Security
        fields = [
            "symbol",
            "name", 
            "security_type",
            "exchange",
            "current_price",
            "day_change_percent",
            "market_cap",
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
        if hasattr(obj, 'fundamentals') and obj.fundamentals:
            return obj.fundamentals.current_price
        return None
    
    def get_day_change_percent(self, obj):
        """Get day change percentage from fundamentals if available"""
        if hasattr(obj, 'fundamentals') and obj.fundamentals:
            return obj.fundamentals.day_change_percent
        return None
    
    def get_market_cap(self, obj):
        """Get market cap from fundamentals if available"""
        if hasattr(obj, 'fundamentals') and obj.fundamentals:
            return obj.fundamentals.market_cap
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