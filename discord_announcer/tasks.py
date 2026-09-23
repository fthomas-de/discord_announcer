"""App Tasks"""

# Standard Library
from datetime import datetime, timedelta
import logging

# Third Party
from celery import shared_task

# Django
from django.utils import timezone

from discord_announcer.discord_bot import send_message_to_discord
from discord_announcer.models import AnnouncerConfig
from discord_announcer.selects import get_sales_since
from discord_announcer.utilities import format_sales

logger = logging.getLogger(__name__)

# Hard floor, also if a stored interval ever ends up below it.
MINIMUM_POST_INTERVAL = timedelta(hours=1)


@shared_task
def discord_announcer_task():
    """Handle every active configuration whose interval has elapsed."""

    now = timezone.now()

    for config in AnnouncerConfig.objects.filter(is_active=True).select_related("corporation"):
        try:
            _announce(config, now)
        except Exception:
            # one broken configuration must not hold up the others
            logger.exception(f"[discord_announcer] Announcing '{config.name}' failed")


def _announce(config: AnnouncerConfig, now: datetime) -> None:
    interval = max(timedelta(hours=config.time_delta), MINIMUM_POST_INTERVAL)

    if config.last_run_at and now - config.last_run_at < interval:
        return

    # Each window starts where the previous one ended, so nothing is posted
    # twice and a late run still covers everything since the last one.
    since = config.last_run_at or now - interval
    sales = get_sales_since(since, config.corporation.corporation_id, config.division)

    if sales:
        hours = round((now - since).total_seconds() / 3600)
        logger.info(
            f"[discord_announcer] Sending {len(sales)} sales for '{config.name}' "
            f"(last {hours}h, channel {config.channel_id}, "
            f"corp {config.corporation.corporation_id}, division {config.division})"
        )

        if not send_message_to_discord(
            messages=format_sales(sales), channel_id=config.channel_id, hours=hours
        ):
            # keep the window open, so these sales go out once sending works
            return
    else:
        logger.info(f"[discord_announcer] No sales for '{config.name}' since {since}")

    config.last_run_at = now
    config.save(update_fields=["last_run_at"])
