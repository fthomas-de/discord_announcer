"""The configuration page and its two buttons."""

from types import SimpleNamespace
from unittest import mock

from django.contrib.messages import get_messages
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

from esi.errors import TokenInvalidError
from esi.exceptions import HTTPClientError

from discord_announcer.models import AnnouncerConfig, default_interval

from .base import (
    CORP_NAME,
    NOW,
    DiscordAnnouncerTestCase,
    embeds,
    fake_discord,
    make_config,
    make_corporation,
    make_names,
    make_sale,
    make_user,
)

TOKEN = SimpleNamespace(character_name="Accountant Alt")
INDEX = "discord_announcer:index"
MANAGER = ("basic_access", "manage_configs")


def formset_data(rows, initial=0):
    """A POST of the configuration formset, one dict per row."""
    data = {
        "form-TOTAL_FORMS": str(len(rows)),
        "form-INITIAL_FORMS": str(initial),
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "1000",
    }
    for index, row in enumerate(rows):
        for key, value in row.items():
            data[f"form-{index}-{key}"] = value

    return data


def texts(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


# the button cooldown lives in the cache; keep it off the dev instance's redis
@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class ViewTestCase(DiscordAnnouncerTestCase):
    def setUp(self):
        cache.clear()
        self.corporation = make_corporation()
        self.client.force_login(make_user(permissions=MANAGER))


class TestAccess(ViewTestCase):
    def test_should_turn_away_a_user_without_the_permission(self):
        self.client.force_login(make_user("nobody", 91000002, permissions=()))

        for name in ("index", "check_tokens", "send_latest"):
            with self.subTest(view=name):
                response = self.client.post(reverse(f"discord_announcer:{name}"))

                # back to the login, not on to the page
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response["Location"].startswith("/account/login/"))

    def test_should_keep_the_buttons_from_a_user_who_may_only_look(self):
        self.client.force_login(make_user("viewer", 91000002))

        for name in ("check_tokens", "send_latest"):
            with self.subTest(view=name),                     mock.patch("discord_announcer.views.get_corp_transaction_token") as token:
                response = self.client.post(reverse(f"discord_announcer:{name}"))

                self.assertTrue(response["Location"].startswith("/account/login/"))
                token.assert_not_called()

    def test_should_only_take_the_buttons_as_post(self):

        for name in ("check_tokens", "send_latest"):
            with self.subTest(view=name):
                self.assertEqual(self.client.get(reverse(f"discord_announcer:{name}")).status_code, 405)


class TestTheForm(ViewTestCase):
    def row(self, **fields):
        values = {
            "name": "Market",
            "corporation": CORP_NAME,
            "division": "1",
            "transaction_kind": "sales",
            "channel_id": "1234567890",
            "time_delta": "2",
            "is_active": "on",
        }
        values.update(fields)

        return values

    def test_should_offer_every_corporation_in_one_datalist(self):
        response = self.client.get(reverse(INDEX))

        self.assertContains(response, '<datalist id="discord-announcer-corporations">')
        self.assertContains(response, f'<option value="{CORP_NAME}">BRAVO</option>')
        self.assertContains(response, 'list="discord-announcer-corporations"')

    def test_should_resolve_a_typed_corporation_name(self):
        response = self.client.post(reverse(INDEX), formset_data([self.row()]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(AnnouncerConfig.objects.get().corporation, self.corporation)

    def test_should_save_a_row_for_purchases(self):
        response = self.client.post(reverse(INDEX), formset_data([self.row(transaction_kind="purchases")]))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(AnnouncerConfig.objects.get().posts_purchases)

    def test_should_reject_an_unknown_corporation(self):
        response = self.client.post(reverse(INDEX), formset_data([self.row(corporation="Nobody Corp")]))

        self.assertContains(response, "Unknown corporation. Pick one of the suggestions.")
        self.assertFalse(AnnouncerConfig.objects.exists())

    def test_should_ignore_the_untouched_empty_row(self):
        """A callable default expects a hidden initial input the bootstrap
        fields do not render; the empty row then counted as changed."""
        config = make_config(corporation=self.corporation)
        existing = self.row(id=str(config.pk), name="Renamed")
        # what the browser sends for the last row as rendered: its defaults
        empty = {
            "name": "", "corporation": "", "division": "1", "transaction_kind": "sales",
            "channel_id": "", "time_delta": str(default_interval()), "is_active": "on",
        }

        response = self.client.post(reverse(INDEX), formset_data([existing, empty], initial=1))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(AnnouncerConfig.objects.get().name, "Renamed")

    def test_should_report_a_half_filled_row(self):
        half = {
            "name": "Half", "corporation": "", "division": "1", "transaction_kind": "sales",
            "channel_id": "", "time_delta": "1",
        }

        response = self.client.post(reverse(INDEX), formset_data([half]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(AnnouncerConfig.objects.exists())

    def test_should_show_the_name_of_a_saved_corporation(self):
        make_config(corporation=self.corporation)

        self.assertContains(self.client.get(reverse(INDEX)), f'value="{CORP_NAME}"')

    def test_should_delete_a_ticked_row(self):
        config = make_config(corporation=self.corporation)

        self.client.post(reverse(INDEX), formset_data([self.row(id=str(config.pk), DELETE="on")], initial=1))

        self.assertFalse(AnnouncerConfig.objects.exists())

    def test_should_ask_before_posting(self):
        self.assertContains(
            self.client.get(reverse(INDEX)), "Post the latest transaction of every active row to Discord now?"
        )


class TestLookingOnly(ViewTestCase):
    """basic_access alone shows the page; changing anything needs manage_configs."""

    def setUp(self):
        super().setUp()
        self.config = make_config(corporation=self.corporation)
        self.client.force_login(make_user("viewer", 91000002))

    def test_should_show_the_rows_without_anything_to_change(self):
        response = self.client.get(reverse(INDEX))

        self.assertContains(response, f'value="{CORP_NAME}"')
        self.assertContains(response, "disabled")
        self.assertEqual(response.context["formset"].total_form_count(), 1)  # no empty row
        for absent in ("Save", "Check tokens", "Post latest transaction", "<datalist", "DELETE"):
            with self.subTest(absent=absent):
                self.assertNotContains(response, absent)

    def test_should_refuse_a_change(self):
        row = {
            "id": str(self.config.pk), "name": "Renamed", "corporation": CORP_NAME, "division": "1",
            "transaction_kind": "sales", "channel_id": "1", "time_delta": "1", "is_active": "on", "DELETE": "on",
        }

        response = self.client.post(reverse(INDEX), formset_data([row], initial=1))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(AnnouncerConfig.objects.get().name, "Market")


@mock.patch("discord_announcer.views.get_corp_transaction_token", return_value=TOKEN)
class TestCooldown(ViewTestCase):
    def setUp(self):
        super().setUp()
        make_config(corporation=self.corporation)

    def test_should_turn_away_a_second_click_of_the_same_button(self, token):
        url = reverse("discord_announcer:check_tokens")

        with mock.patch("discord_announcer.views.get_transactions", return_value=[]) as esi:
            self.client.post(url)
            response = self.client.post(url)

        self.assertEqual(esi.call_count, 1)
        self.assertIn("Please wait 60 seconds", texts(response)[-1])

    def test_should_time_each_button_and_user_on_its_own(self, token):
        with mock.patch("discord_announcer.views.get_transactions", return_value=[]) as esi:
            self.client.post(reverse("discord_announcer:check_tokens"))
            self.client.force_login(make_user("second", 91000002, permissions=MANAGER))
            self.client.post(reverse("discord_announcer:check_tokens"))

        self.assertEqual(esi.call_count, 2)

        patcher, sent = fake_discord()
        with patcher, mock.patch("discord_announcer.views.discord_bot_active", return_value=True),                 mock.patch("discord_announcer.views.get_latest_transaction", return_value=None) as latest:
            self.client.post(reverse("discord_announcer:send_latest"))

        latest.assert_called_once()


@mock.patch("discord_announcer.views.get_corp_transaction_token", return_value=TOKEN)
class TestCheckTokens(ViewTestCase):
    def check(self):
        return self.client.post(reverse("discord_announcer:check_tokens"))

    def test_should_say_there_is_nothing_to_check(self, token):
        self.assertEqual(texts(self.check()), ["There are no saved configurations to check."])

    def test_should_name_the_character_whose_token_works_and_skip_the_cache(self, token):
        """A cached answer would not prove the token still works."""
        make_config(corporation=self.corporation)

        with mock.patch("discord_announcer.views.get_transactions", return_value=[]) as esi:
            response = self.check()

        self.assertEqual(texts(response), ["Market: OK, the wallet is read as Accountant Alt."])
        self.assertIs(esi.call_args.kwargs["use_cache"], False)

    def test_should_name_the_roles_when_no_token_qualifies(self, token):
        make_config(corporation=self.corporation)
        token.return_value = None

        message = texts(self.check())[0]

        self.assertIn("no character of Bravo Corp", message)
        self.assertIn("Director", message)

    def test_should_explain_each_esi_failure_in_its_own_words(self, token):
        make_config(corporation=self.corporation)

        for error, words in (
            (HTTPClientError(403, {}, None), "one of the in-game roles"),
            (TokenInvalidError(), "is no longer valid"),
        ):
            with self.subTest(error=type(error).__name__):
                cache.clear()

                with mock.patch("discord_announcer.views.get_transactions", side_effect=error):
                    # the redirect is not followed, so earlier messages are still queued
                    self.assertIn(words, texts(self.check())[-1])


@mock.patch("discord_announcer.views.get_corp_transaction_token", return_value=TOKEN)
class TestPostLatestSale(ViewTestCase):
    # what the row posts; TestPostLatestPurchase runs the same tests for purchases
    kind = AnnouncerConfig.TransactionKind.SALES
    is_buy = False
    singular, plural = "sale", "sales"

    def setUp(self):
        super().setUp()
        make_names()
        self.config = make_config(corporation=self.corporation, transaction_kind=self.kind)
        patcher, self.sent = fake_discord()
        patcher.start()
        self.addCleanup(patcher.stop)

    def post(self, bot=True, sales=()):
        with mock.patch("discord_announcer.views.discord_bot_active", return_value=bot), \
                mock.patch("discord_announcer.discord_bot.discord_bot_active", return_value=bot), \
                mock.patch("discord_announcer.views.get_latest_transaction", return_value=sales[0] if sales else None) as latest:
            response = self.client.post(reverse("discord_announcer:send_latest"))

        return response, latest

    def test_should_fetch_nothing_without_the_bot(self, token):
        response, latest = self.post(bot=False)

        self.assertEqual(texts(response), ["AA-Discordbot is not installed, nothing can be posted."])
        latest.assert_not_called()

    def test_should_ask_esi_for_what_the_row_posts(self, token):
        _, latest = self.post()

        self.assertIs(latest.call_args.args[2], self.is_buy)

    def test_should_warn_when_esi_has_none(self, token):
        response, _ = self.post()

        self.assertEqual(texts(response), [f"Market: ESI returned no {self.plural} for this wallet division."])
        self.assertEqual(self.sent.call_count, 0)

    def test_should_post_it_with_its_date_and_leave_the_rhythm_alone(self, token):
        transaction = make_sale(minutes_ago=0, is_buy=self.is_buy)

        response, _ = self.post(sales=[transaction])

        self.assertEqual(
            [embed.title for embed in embeds(self.sent)],
            [f"Latest {self.singular}, {NOW:%Y-%m-%d %H:%M} EVE: Jita IV - Moon 4 - Caldari Navy Assembly Plant"],
        )
        self.config.refresh_from_db()
        self.assertIsNone(self.config.last_run_at)
        self.assertTrue(texts(response)[0].startswith(f"Market: posted the latest {self.singular}"))

    def test_should_post_it_at_a_station_corptools_does_not_know(self, token):
        """It used to warn and post nothing."""
        self.post(sales=[make_sale(location_id=1_234_567_890_123, is_buy=self.is_buy)])

        self.assertTrue(embeds(self.sent)[0].title.endswith(": Location 1234567890123"))


class TestPostLatestPurchase(TestPostLatestSale):
    kind = AnnouncerConfig.TransactionKind.PURCHASES
    is_buy = True
    singular, plural = "purchase", "purchases"
