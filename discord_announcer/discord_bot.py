from django.apps import apps
from allianceauth.services.hooks import get_extension_logger

logger = get_extension_logger(__name__)


def discord_bot_active():
    """Check if AA-Discordbot is installed"""
    return apps.is_installed("aadiscordbot")


def send_message_to_discord(
    messages: list, channel_id: int, title: str, source: tuple[str, str] | None = None
) -> bool:
    """Queue one embed per (station, text) pair, with source as (author line, icon url); False if impossible."""
    if not discord_bot_active():
        logger.error("[discord_announcer] AADiscordBot not installed, cannot send message to discord")
        return False

    from aadiscordbot.tasks import send_message
    from discord import Color, Embed

    for header, message in messages:
        e = Embed(
            title=f"{title}: {header}",
            description=message,
            color=Color.nitro_pink(),
        )

        if source:
            author, icon_url = source
            e.set_author(name=author, icon_url=icon_url)

        send_message(channel_id=channel_id, embed=e)

    return True