"""App Tasks"""

# Standard Library
from datetime import datetime, timedelta

# Third Party
from celery import shared_task

# Django
from django.utils import timezone

# Alliance Auth
from allianceauth.services.hooks import get_extension_logger
from allianceauth.services.tasks import QueueOnce
from esi.errors import TokenError
from esi.exceptions import HTTPClientError

from discord_announcer.discord_bot import send_message_to_discord
from discord_announcer.models import AnnouncerConfig
from discord_announcer.selects import get_sales_since, get_transactions_after
from discord_announcer.utilities import describe_source, format_sales

logger = get_extension_logger(__name__)

# Hard floor, also if a stored interval ever ends up below it.
MINIMUM_POST_INTERVAL = timedelta(hours=1)

# How much earlier than its interval a row counts as due. The periodic task
# runs on a fixed tick and last_run_at carries the queue's latency, so a row
# run at 10:00:00.8 was not due at 11:00:00.5 and waited for the next tick -
# 75 minutes instead of 60, and a twelve hour row wandered by a tick per post.
# The price is that two posts can sit up to this much under the floor apart.
DUE_TOLERANCE = timedelta(minutes=1)


# QueueOnce, as corptools runs its own: after a worker outage beat has queued
# the task several times, and a worker with more than one process would run
# them side by side - each seeing the same last_run_at, each posting the same
# sales.
@shared_task(base=QueueOnce)
def discord_announcer_task():
    """Handle every active configuration whose interval has elapsed."""

    now = timezone.now()

    for config in AnnouncerConfig.objects.filter(is_active=True).select_related("corporation"):
        try:
            _announce(config, now)
        except (ValueError, HTTPClientError, TokenError) as error:
            # what a row without a usable token or role runs into on every
            # attempt: said once per attempt, without a traceback
            logger.warning(f"[discord_announcer] '{config.name}': {error}")
        except Exception:
            # one broken configuration must not hold up the others
            logger.exception(f"[discord_announcer] Announcing '{config.name}' failed")


def _is_due(config: AnnouncerConfig, now: datetime) -> bool:
    interval = max(timedelta(hours=config.time_delta), MINIMUM_POST_INTERVAL)
    last = config.last_attempt_at or config.last_run_at

    return last is None or now - last >= interval - DUE_TOLERANCE


def _hours_label(hours: int) -> str:
    return f"last {hours} hour" if hours == 1 else f"last {hours} hours"


def _announce(config: AnnouncerConfig, now: datetime) -> None:
    if not _is_due(config, now):
        return

    # counted as an attempt before anything can fail, so a row that fails is
    # tried again one interval later rather than on every tick
    config.last_attempt_at = now
    config.save(update_fields=["last_attempt_at"])

    interval = max(timedelta(hours=config.time_delta), MINIMUM_POST_INTERVAL)
    since = config.last_run_at or now - interval
    corp_id = config.corporation.corporation_id

    if config.last_transaction_id is None:
        # the first window of a row: by time, and from here on by transaction
        sales, newest = get_sales_since(since, corp_id, config.division)
    else:
        transactions = get_transactions_after(corp_id, config.division, config.last_transaction_id)
        sales = [t for t in transactions if not t.is_buy]
        newest = max((t.transaction_id for t in transactions), default=None)

    if sales:
        hours = round((now - since).total_seconds() / 3600)
        # every sale reaches the message now - an unknown station or type is
        # posted by its id - so the count is the count of what goes out
        logger.info(
            f"[discord_announcer] Sending {len(sales)} sales for '{config.name}' "
            f"({_hours_label(hours)}, channel {config.channel_id}, "
            f"corp {corp_id}, division {config.division})"
        )

        if not send_message_to_discord(
            messages=format_sales(sales),
            channel_id=config.channel_id,
            title=f"Sales ({_hours_label(hours)})",
            source=describe_source(config),
        ):
            # keep the window open, so these sales go out once sending works
            return
    else:
        logger.info(f"[discord_announcer] No sales for '{config.name}' since {since}")

    config.last_run_at = now

    if newest is not None:
        config.last_transaction_id = max(newest, config.last_transaction_id or 0)

    config.save(update_fields=["last_run_at", "last_transaction_id"])
