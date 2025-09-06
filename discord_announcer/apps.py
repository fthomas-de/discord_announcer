"""App Configuration"""

# Django
from django.apps import AppConfig

# AA Example App
from discord_announcer import __version__


class DAConfig(AppConfig):
    """App Config"""

    name = "discord_announcer"
    label = "discord_announcer"
    verbose_name = f"Discord Announcer v{__version__}"
