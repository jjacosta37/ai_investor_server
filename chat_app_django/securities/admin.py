from django.contrib import admin
from .models import (
    Security,
    SecurityFundamentals,
    WatchlistItem,
    Holding,
    NewsSource,
    SecurityNews,
    Transaction,
)

admin.site.register(Security)
admin.site.register(SecurityFundamentals)
admin.site.register(WatchlistItem)
admin.site.register(Holding)
admin.site.register(NewsSource)
admin.site.register(SecurityNews)
admin.site.register(Transaction)
