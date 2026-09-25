"""Shared fixtures for the discord_announcer tests.

Nothing here talks to ESI or Discord. ESI answers are plain objects with the
attributes the django-esi 9 client hands out; Discord is a stand-in for the
`discord` and `aadiscordbot.tasks` modules, neither of which is installed in
the dev instance.

Run these inside `manage.py test` only - never from `manage.py shell`, which
writes straight into the real database.
"""

import sys
from datetime import datetime, timedelta, timezone
from itertools import count
from types import ModuleType, SimpleNamespace
from unittest import mock

from django.contrib.auth.models import Permission, User
from django.test import TestCase

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from corptools.models import CorporationAudit, CorporationWalletDivision, EveItemType, EveLocation

from discord_announcer.models import AnnouncerConfig

CORP_ID = 98000001
CORP_NAME = "Bravo Corp"
CORP_TICKER = "BRAVO"

STATION_ID = 60003760
STATION_NAME = "Jita IV - Moon 4 - Caldari Navy Assembly Plant"
OTHER_STATION_ID = 60008494
OTHER_STATION_NAME = "Amarr VIII (Oris) - Emperor Family Academy"

TRITANIUM = 34
PYERITE = 35

# a fixed "now" on the hour, so windows and intervals read as plain numbers
NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)

transaction_ids = count(1_000_000)


class DiscordAnnouncerTestCase(TestCase):
    """Base class for every test of this app."""


def make_corporation(corp_id=CORP_ID, name=CORP_NAME, ticker=CORP_TICKER):
    return EveCorporationInfo.objects.create(
        corporation_id=corp_id,
        corporation_name=name,
        corporation_ticker=ticker,
        member_count=10,
    )


def make_division(corporation, division=1, name=None):
    """A wallet division as corptools syncs it, with the name given in game."""
    audit, _ = CorporationAudit.objects.get_or_create(corporation=corporation)

    return CorporationWalletDivision.objects.create(
        corporation=audit, division=division, balance=0, name=name
    )


def make_config(corporation=None, **fields):
    values = {
        "name": "Market",
        "corporation": corporation or make_corporation(),
        "division": 1,
        "channel_id": 1234567890,
        "time_delta": 1,
        "is_active": True,
    }
    values.update(fields)

    return AnnouncerConfig.objects.create(**values)


def make_names():
    """The stations and item types corptools would know."""
    EveLocation.objects.create(location_id=STATION_ID, location_name=STATION_NAME)
    EveLocation.objects.create(location_id=OTHER_STATION_ID, location_name=OTHER_STATION_NAME)
    EveItemType.objects.create(type_id=TRITANIUM, name="Tritanium", published=True)
    EveItemType.objects.create(type_id=PYERITE, name="Pyerite", published=True)


def make_sale(minutes_ago=30, is_buy=False, location_id=STATION_ID, type_id=TRITANIUM,
              quantity=10, unit_price=5.0, transaction_id=None, now=NOW):
    """One wallet transaction, as the django-esi 9 client returns it."""
    return SimpleNamespace(
        date=now - timedelta(minutes=minutes_ago),
        is_buy=is_buy,
        location_id=location_id,
        type_id=type_id,
        quantity=quantity,
        unit_price=unit_price,
        transaction_id=transaction_id if transaction_id is not None else next(transaction_ids),
    )


def make_user(username="market", character_id=91000001, permissions=("basic_access",)):
    """A user Alliance Auth lets through to the app's views.

    Every url registered through a UrlHook requires a main character, so a
    user without one is redirected to the dashboard whatever their
    permissions say.
    """
    user = User.objects.create_user(username, f"{username}@example.com", "password")
    character = EveCharacter.objects.create(
        character_id=character_id,
        character_name=f"{username} character",
        corporation_id=CORP_ID,
        corporation_name=CORP_NAME,
        corporation_ticker=CORP_TICKER,
    )
    CharacterOwnership.objects.create(
        character=character, user=user, owner_hash=f"owner-hash-{character_id}"
    )
    user.profile.main_character = character
    user.profile.save()

    for codename in permissions:
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="discord_announcer", codename=codename)
        )

    return User.objects.get(pk=user.pk)  # drop the cached permissions


class FakeEmbed:
    """What the app sets on a discord.Embed, kept for the assertions."""

    def __init__(self, title, description, color):
        self.title = title
        self.description = description
        self.color = color
        self.author = None

    def set_author(self, name, icon_url):
        self.author = (name, icon_url)


def fake_discord():
    """Stand-ins for py-cord and AA-Discordbot, and the mock that collects posts.

    Returns (patcher, send_message). While the patcher is active, the app
    believes the bot is installed and every embed it sends lands in
    send_message.call_args_list.
    """
    send_message = mock.Mock()

    discord = ModuleType("discord")
    discord.Embed = FakeEmbed
    discord.Color = SimpleNamespace(nitro_pink=lambda: "pink")

    aadiscordbot = ModuleType("aadiscordbot")
    tasks = ModuleType("aadiscordbot.tasks")
    tasks.send_message = send_message
    aadiscordbot.tasks = tasks

    patcher = mock.patch.dict(
        sys.modules, {"discord": discord, "aadiscordbot": aadiscordbot, "aadiscordbot.tasks": tasks}
    )

    return patcher, send_message


def embeds(send_message):
    return [call.kwargs["embed"] for call in send_message.call_args_list]
