"""App Views"""

# Django
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

# Alliance Auth
from allianceauth.eveonline.models import EveCorporationInfo
from allianceauth.services.hooks import get_extension_logger

# Third Party
from esi.errors import TokenError
from esi.exceptions import HTTPClientError

from discord_announcer import __version__
from discord_announcer.discord_bot import discord_bot_active, send_message_to_discord
from discord_announcer.forms import CORPORATION_DATALIST_ID, AnnouncerConfigFormSet
from discord_announcer.models import AnnouncerConfig
from discord_announcer.selects import get_corp_transaction_token, get_latest_sale, get_transactions
from discord_announcer.utilities import format_sales

logger = get_extension_logger(__name__)


@login_required
@permission_required("discord_announcer.basic_access")
def index(request: WSGIRequest) -> HttpResponse:
    """
    Manage the announcer configurations (corporation, division, channel,
    interval) that the scheduled task reads.
    :param request:
    :return:
    """

    queryset = AnnouncerConfig.objects.select_related("corporation")

    if request.method == "POST":
        formset = AnnouncerConfigFormSet(request.POST, queryset=queryset)

        if formset.is_valid():
            formset.save()
            messages.success(request, _("Configuration saved."))

            return redirect("discord_announcer:index")
    else:
        formset = AnnouncerConfigFormSet(queryset=queryset)

    context = {
        "title": _("Discord Announcer"),
        "version": __version__,
        "formset": formset,
        "corporation_datalist_id": CORPORATION_DATALIST_ID,
        "corporations": EveCorporationInfo.objects.order_by("corporation_name").values_list(
            "corporation_name", "corporation_ticker"
        ),
    }

    return render(request, "discord_announcer/index.html", context)


def _describe_failure(config: AnnouncerConfig, token, error: Exception) -> str:
    """What went wrong reading the wallet, in words an admin can act on."""
    names = {"name": config.name, "character": token.character_name}

    if isinstance(error, HTTPClientError) and error.status_code == 403:
        return _(
            "%(name)s: ESI refused the token of %(character)s. The character needs "
            "the in-game role Accountant or Junior Accountant."
        ) % names

    if isinstance(error, TokenError):
        return _(
            "%(name)s: the token of %(character)s is no longer valid. Add it again "
            "by logging in with that character."
        ) % names

    logger.exception(f"[discord_announcer] Reading the wallet for '{config.name}' failed")

    return _("%(name)s: reading the wallet as %(character)s failed: %(error)s") % {
        **names,
        "error": error,
    }


def _missing_token(config: AnnouncerConfig) -> str:
    return _(
        "%(name)s: no character of %(corporation)s has a token with the wallet scope."
    ) % {"name": config.name, "corporation": config.corporation.corporation_name}


@login_required
@permission_required("discord_announcer.basic_access")
@require_POST
def check_tokens(request: WSGIRequest) -> HttpResponse:
    """Read every saved configuration's wallet once, the way the task does, without posting."""

    configs = AnnouncerConfig.objects.select_related("corporation").order_by("name")

    if not configs:
        messages.info(request, _("There are no saved configurations to check."))

    for config in configs:
        token = get_corp_transaction_token(config.corporation.corporation_id)

        if not token:
            messages.error(request, _missing_token(config))
            continue

        try:
            # bypass the cache, a cached answer would not prove the token still works
            get_transactions(config.corporation.corporation_id, config.division, token=token, use_cache=False)
        except Exception as error:
            messages.error(request, _describe_failure(config, token, error))
        else:
            messages.success(
                request,
                _("%(name)s: OK, the wallet is read as %(character)s.")
                % {"name": config.name, "character": token.character_name},
            )

    return redirect("discord_announcer:index")


@login_required
@permission_required("discord_announcer.basic_access")
@require_POST
def send_latest(request: WSGIRequest) -> HttpResponse:
    """Post the newest sale of every active configuration once; the regular rhythm is not touched."""

    if not discord_bot_active():
        messages.error(request, _("AA-Discordbot is not installed, nothing can be posted."))

        return redirect("discord_announcer:index")

    configs = AnnouncerConfig.objects.filter(is_active=True).select_related("corporation").order_by("name")

    if not configs:
        messages.info(request, _("There are no active configurations."))

    for config in configs:
        token = get_corp_transaction_token(config.corporation.corporation_id)

        if not token:
            messages.error(request, _missing_token(config))
            continue

        try:
            sale = get_latest_sale(config.corporation.corporation_id, config.division, token=token)
        except Exception as error:
            messages.error(request, _describe_failure(config, token, error))
            continue

        if sale is None:
            messages.warning(
                request, _("%(name)s: ESI returned no sales for this wallet division.") % {"name": config.name}
            )
            continue

        sold_at = f"{sale.date:%Y-%m-%d %H:%M} EVE"
        formatted = format_sales([sale])

        if not formatted:
            messages.warning(
                request,
                _(
                    "%(name)s: the latest sale (%(sold_at)s) is at a station or of an item "
                    "type Corp Tools does not know yet, so there is nothing to post."
                ) % {"name": config.name, "sold_at": sold_at},
            )
            continue

        send_message_to_discord(messages=formatted, channel_id=config.channel_id, title=f"Latest sale, {sold_at}")
        messages.success(
            request,
            _("%(name)s: posted the latest sale (%(sold_at)s).") % {"name": config.name, "sold_at": sold_at},
        )

    return redirect("discord_announcer:index")
