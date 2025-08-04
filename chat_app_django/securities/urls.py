from django.urls import path
from .views import SecurityListView, SecurityDetailView

app_name = "securities"

urlpatterns = [
    # Securities endpoints
    path("securities/", SecurityListView.as_view(), name="security-list"),
    path("securities/<str:symbol>/", SecurityDetailView.as_view(), name="security-detail"),
]