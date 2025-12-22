"""App Tasks"""

# Standard Library
from datetime import datetime, timedelta
import logging

# Third Party
from celery import shared_task
from discord_announcer.discord_bot import send_message_to_discord
from discord_announcer.selects import get_transactions_for_timeframe
from discord_announcer.app_settings import TIME_DELTA
from dateutil.tz import tzlocal
from discord_announcer.utilities import format_sales

logger = logging.getLogger(__name__)

@shared_task
def discord_announcer_task(delta, corporation_id, division, channel_id):
    if delta == None:
        delta = TIME_DELTA
    logger.info(f"[discord_announcer] sending sales for TIME_DELTA {delta} to channel {channel_id} for corp {corporation_id} and division {division}")

    sales = get_transactions_for_timeframe(datetime.now(tz=tzlocal())-timedelta(hours=delta), corporation_id, division)
    if not sales:
        logger.info("[discord_announcer] No sales found, not sending message")
        return
    
    else:
        logger.info(f"[discord_announcer] Found {len(sales)} sales, sending message")
    
    sales_formatted = format_sales(sales)
    send_message_to_discord(messages=sales_formatted, channel_id=channel_id, hours=delta)
    sales = []
    sales_formatted = []
