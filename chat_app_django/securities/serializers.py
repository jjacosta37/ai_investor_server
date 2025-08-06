from rest_framework import serializers
from .models import Security, SecurityFundamentals, WatchlistItem


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


class WatchlistItemSerializer(serializers.ModelSerializer):
    """Serializer for WatchlistItem model"""
    
    security = SecurityListSerializer(read_only=True)
    security_symbol = serializers.CharField(write_only=True)
    
    class Meta:
        model = WatchlistItem
        fields = [
            "id",
            "security",
            "security_symbol",
            "added_at",
        ]
        read_only_fields = [
            "id",
            "added_at",
        ]
    
    def create(self, validated_data):
        """Create a new watchlist item"""
        security_symbol = validated_data.pop('security_symbol')
        user = self.context['request'].user
        
        try:
            security = Security.objects.get(symbol__iexact=security_symbol, is_active=True)
        except Security.DoesNotExist:
            raise serializers.ValidationError(
                {"security_symbol": f"Security with symbol '{security_symbol}' not found or is inactive."}
            )
        
        # Check if already in watchlist
        if WatchlistItem.objects.filter(user=user, security=security).exists():
            raise serializers.ValidationError(
                {"security_symbol": f"Security '{security_symbol}' is already in your watchlist."}
            )
        
        validated_data['security'] = security
        validated_data['user'] = user
        
        return super().create(validated_data)