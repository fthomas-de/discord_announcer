"""App Tasks"""

# Standard Library
from datetime import datetime, timedelta
import logging

# Third Party
from celery import shared_task
from discord_announcer.discord_bot import send_message_to_discord
from discord_announcer.selects import get_transactions_for_timeframe
from discord_announcer.app_settings import TIME_DELTA, CHANNEL_ID
from dateutil.tz import tzlocal
from discord_announcer.utilities import format_sales

logger = logging.getLogger(__name__)

@shared_task
def discord_announcer_task(delta):
    logger.info(f"sending sales for TIME_DELTA {TIME_DELTA} to channel {CHANNEL_ID}")

    if delta == None:
        delta = TIME_DELTA

    sales = get_transactions_for_timeframe(datetime.now(tz=tzlocal())-timedelta(hours=delta))
    sales_formatted = format_sales(sales)
    send_message_to_discord(messages=sales_formatted, channel_id=CHANNEL_ID, hours=TIME_DELTA)
