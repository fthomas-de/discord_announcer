"""App Views"""

# Django
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from discord_announcer import __version__
from discord_announcer.forms import AnnouncerConfigFormSet
from discord_announcer.models import AnnouncerConfig


@login_required
@permission_required("discord_announcer.basic_access")
def index(request: WSGIRequest) -> HttpResponse:
    """
    Manage the announcer configurations (corporation, division, channel,
    lookback window) that the scheduled task reads.
    :param request:
    :return:
    """

    if request.method == "POST":
        formset = AnnouncerConfigFormSet(
            request.POST, queryset=AnnouncerConfig.objects.all()
        )

        if formset.is_valid():
            formset.save()
            messages.success(request, _("Configuration saved."))

            return redirect("discord_announcer:index")
    else:
        formset = AnnouncerConfigFormSet(queryset=AnnouncerConfig.objects.all())

    context = {
        "title": _("Discord Announcer"),
        "version": __version__,
        "formset": formset,
    }

    return render(request, "discord_announcer/index.html", context)
