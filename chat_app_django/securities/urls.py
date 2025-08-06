from django.urls import path
from .views import SecurityListView, SecurityDetailView, WatchlistItemListView, WatchlistItemDetailView

app_name = "securities"

urlpatterns = [
    # Securities endpoints
    path("securities/", SecurityListView.as_view(), name="security-list"),
    path("securities/<str:symbol>/", SecurityDetailView.as_view(), name="security-detail"),
    
    # Watchlist endpoints
    path("watchlist/", WatchlistItemListView.as_view(), name="watchlist-list"),
    path("watchlist/<int:pk>/", WatchlistItemDetailView.as_view(), name="watchlist-detail"),
]