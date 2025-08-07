from django.contrib import admin
from .models import (
    Security,
    SecurityFundamentals,
    WatchlistItem,
    Holding,
    NewsSource,
    SecurityNewsSummary,
    NewsItem,
    UpcomingEvent,
    OverallSentiment,
)

admin.site.register(Security)
admin.site.register(SecurityFundamentals)
admin.site.register(WatchlistItem)
admin.site.register(Holding)
admin.site.register(NewsSource)
admin.site.register(SecurityNewsSummary)
admin.site.register(NewsItem)
admin.site.register(UpcomingEvent)
admin.site.register(OverallSentiment)
