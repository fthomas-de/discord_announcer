"""App Views"""

# Django
from django.contrib.auth.decorators import login_required, permission_required
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.shortcuts import render
from discord_announcer.discord_bot import send_message_to_discord

@login_required
@permission_required("discord_announcer.basic_access")
def index(request: WSGIRequest) -> HttpResponse:
    """
    Index view
    :param request:
    :return:
    """

    context = {"text": "Hello, World!"}
    send_message_to_discord()
    return render(request, "discord_announcer/index.html", context)
