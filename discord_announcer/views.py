"""App Views"""

from datetime import datetime, timedelta
from discord_announcer.app_settings import TIME_DELTA, CHANNEL_ID
from discord_announcer.selects import get_transactions_for_timeframe
from discord_announcer.utilities import format_sales
from django.contrib.auth.decorators import login_required, permission_required
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.shortcuts import render
from discord_announcer.discord_bot import send_message_to_discord
from dateutil.tz import tzlocal

# @login_required
# @permission_required("discord_announcer.basic_access")
# def index(request: WSGIRequest) -> HttpResponse:
#     """
#     Index view
#     :param request:
#     :return:
#     """

    # context = {"text": "Hello, World!"}

    # sales = get_transactions_for_timeframe(datetime.now(tz=tzlocal())-timedelta(days=14, hours=TIME_DELTA))
    # sales_formatted = format_sales(sales)
    # print(sales_formatted)
    # send_message_to_discord(messages=sales_formatted, channel_id=CHANNEL_ID, hours=TIME_DELTA)

    # return render(request, "discord_announcer/index.html", context)
