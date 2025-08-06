from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Case, When, Value, IntegerField
from .models import Security, WatchlistItem
from .serializers import SecurityListSerializer, SecurityDetailSerializer, WatchlistItemSerializer


class SecurityListView(APIView):
    """
    List all securities with optional filtering and search.
    GET /api/securities/
    """
    
    def get(self, request):
        """Get list of all securities with optional filtering"""
        securities = Security.objects.filter(is_active=True).select_related('fundamentals')
        
        # Optional filtering by security type
        security_type = request.query_params.get('type', None)
        if security_type:
            securities = securities.filter(security_type__iexact=security_type)
        
        # Optional filtering by exchange
        exchange = request.query_params.get('exchange', None)
        if exchange:
            securities = securities.filter(exchange__iexact=exchange)
        
        # Optional search by symbol or name
        search = request.query_params.get('search', None)
        if search:
            securities = securities.filter(
                Q(symbol__icontains=search) | Q(name__icontains=search)
            ).annotate(
                # Priority: exact symbol match = 1, other matches = 2
                search_priority=Case(
                    When(symbol__iexact=search, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField()
                )
            )
        
        # Optional ordering
        ordering = request.query_params.get('ordering', 'symbol')
        valid_orderings = ['symbol', '-symbol', 'name', '-name', 'security_type', '-security_type']
        
        if search:
            # When searching, prioritize exact symbol matches first, then apply user ordering
            if ordering in valid_orderings:
                securities = securities.order_by('search_priority', ordering)
            else:
                securities = securities.order_by('search_priority', 'symbol')
        else:
            # No search, use normal ordering
            if ordering in valid_orderings:
                securities = securities.order_by(ordering)
            else:
                securities = securities.order_by('symbol')
        
        # Optional pagination (basic limit/offset)
        limit = request.query_params.get('limit', None)
        offset = request.query_params.get('offset', 0)
        
        try:
            offset = int(offset)
        except (ValueError, TypeError):
            offset = 0
            
        if limit:
            try:
                limit = int(limit)
                securities = securities[offset:offset + limit]
            except (ValueError, TypeError):
                securities = securities[offset:]
        else:
            securities = securities[offset:]
        
        serializer = SecurityListSerializer(securities, many=True)
        
        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        })


class SecurityDetailView(APIView):
    """
    Retrieve detailed information about a specific security.
    GET /api/securities/{symbol}/
    """
    
    def get_object(self, symbol):
        """Get security object by symbol or return 404"""
        return get_object_or_404(
            Security.objects.select_related('fundamentals'), 
            symbol__iexact=symbol, 
            is_active=True
        )
    
    def get(self, request, symbol):
        """Get detailed security information"""
        security = self.get_object(symbol)
        serializer = SecurityDetailSerializer(security)
        return Response(serializer.data)


class WatchlistItemListView(APIView):
    """
    List user's watchlist items or create a new one.
    GET /api/watchlist/ - List all watchlist items for authenticated user
    POST /api/watchlist/ - Add a new item to watchlist
    """
    
    def get(self, request):
        """Get all watchlist items for the authenticated user"""
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        watchlist_items = WatchlistItem.objects.filter(
            user=request.user
        ).select_related('security', 'security__fundamentals').order_by('-added_at')
        
        serializer = WatchlistItemSerializer(watchlist_items, many=True)
        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        })
    
    def post(self, request):
        """Add a new item to user's watchlist"""
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        serializer = WatchlistItemSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WatchlistItemDetailView(APIView):
    """
    Delete a specific watchlist item.
    DELETE /api/watchlist/{id}/ - Remove item from watchlist
    """
    
    def get_object(self, pk, user):
        """Get watchlist item by ID for the authenticated user"""
        return get_object_or_404(
            WatchlistItem.objects.select_related('security', 'security__fundamentals'),
            pk=pk,
            user=user
        )
    
    def delete(self, request, pk):
        """Remove item from user's watchlist"""
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        watchlist_item = self.get_object(pk, request.user)
        watchlist_item.delete()
        
        return Response(
            {"message": "Item removed from watchlist successfully"},
            status=status.HTTP_204_NO_CONTENT
        )
