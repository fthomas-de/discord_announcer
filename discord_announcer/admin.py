"""Admin models"""

# Django
from django.contrib import admin

from discord_announcer.models import AnnouncerConfig


@admin.register(AnnouncerConfig)
class AnnouncerConfigAdmin(admin.ModelAdmin):
    """Fallback editor for the announcer configurations"""

    list_display = ("name", "corporation", "division", "channel_id", "time_delta", "is_active", "last_run_at")
    list_filter = ("is_active", "corporation")
