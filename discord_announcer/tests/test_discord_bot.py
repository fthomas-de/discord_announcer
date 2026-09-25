"""Handing a post to AA-Discordbot."""

import sys
from unittest import mock

from discord_announcer.discord_bot import send_message_to_discord

from .base import DiscordAnnouncerTestCase, embeds, fake_discord


class TestSendMessage(DiscordAnnouncerTestCase):
    def test_should_refuse_without_the_bot_and_import_nothing(self):
        with mock.patch("discord_announcer.discord_bot.discord_bot_active", return_value=False):
            sent = send_message_to_discord([("Jita", "text")], channel_id=1, title="Sales")

        self.assertFalse(sent)
        self.assertNotIn("aadiscordbot.tasks", sys.modules)

    def test_should_send_one_embed_per_station_with_its_source(self):
        patcher, send_message = fake_discord()

        with patcher, mock.patch("discord_announcer.discord_bot.discord_bot_active", return_value=True):
            sent = send_message_to_discord(
                [("Jita", "Tritanium x 10"), ("Amarr", "Pyerite x 2")],
                channel_id=42,
                title="Sales (last 1 hour)",
                source=("Bravo Corp [BRAVO] · Wallet division 1", "https://logo"),
            )

        self.assertTrue(sent)
        self.assertEqual(
            [embed.title for embed in embeds(send_message)],
            ["Sales (last 1 hour): Jita", "Sales (last 1 hour): Amarr"],
        )
        self.assertEqual(embeds(send_message)[0].author, ("Bravo Corp [BRAVO] · Wallet division 1", "https://logo"))
        self.assertEqual({call.kwargs["channel_id"] for call in send_message.call_args_list}, {42})
