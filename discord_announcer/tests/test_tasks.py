"""The periodic task: which rows are due, which sales a window holds, and
where the next window starts.

ESI is replaced at selects.get_transactions, so everything from there up -
the watermark, the paging, the filters - runs for real.
"""

from datetime import timedelta
from types import SimpleNamespace
from unittest import mock

from esi.errors import TokenInvalidError
from esi.exceptions import HTTPClientError

from allianceauth.services.tasks import QueueOnce

from discord_announcer import tasks
from discord_announcer.models import AnnouncerConfig
from discord_announcer.selects import MAX_PAGES
from discord_announcer.tasks import DUE_TOLERANCE, _announce, discord_announcer_task

from .base import (
    NOW,
    DiscordAnnouncerTestCase,
    embeds,
    fake_discord,
    make_config,
    make_names,
    make_sale,
)

TOKEN = SimpleNamespace(character_name="Accountant Alt")

# Alliance Auth names every extension logger under "extensions."
TASK_LOGGER = "extensions.discord_announcer.tasks"


class AnnounceTestCase(DiscordAnnouncerTestCase):
    """One configuration, a fake bot, and an ESI answer set per test."""

    def setUp(self):
        make_names()
        self.config = make_config(time_delta=1)
        self.answer = []

        discord, self.sent = fake_discord()

        for patch in (
            mock.patch("discord_announcer.selects.get_transactions", side_effect=self.transactions),
            mock.patch("discord_announcer.selects.get_corp_transaction_token", return_value=TOKEN),
            mock.patch("discord_announcer.discord_bot.discord_bot_active", return_value=True),
            discord,
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def transactions(self, corp_id, division, token=None, use_cache=True, from_id=None):
        """ESI's newest-first page, cut at from_id the way ESI cuts it."""
        rows = sorted(self.answer, key=lambda t: -t.transaction_id)

        if from_id is not None:
            rows = [t for t in rows if t.transaction_id <= from_id]

        return rows[: self.page_size]

    page_size = 2500

    def run_at(self, when=NOW):
        _announce(self.config, when)
        self.config.refresh_from_db()

    def titles(self):
        return [embed.title for embed in embeds(self.sent)]


class TestWhenARowIsDue(AnnounceTestCase):
    def test_should_run_a_row_that_never_ran(self):
        self.run_at()

        self.assertEqual(self.config.last_run_at, NOW)

    def test_should_skip_a_row_whose_interval_has_not_passed(self):
        self.config.last_run_at = NOW - timedelta(minutes=30)
        self.config.save()

        self.run_at()

        self.assertEqual(self.config.last_run_at, NOW - timedelta(minutes=30))

    def test_should_count_a_row_due_just_under_its_interval(self):
        """The periodic task's tick and the queue's latency: a run at
        10:00:00.8 was not due at 11:00:00.5 and waited a whole tick."""
        self.config.last_run_at = NOW - timedelta(hours=1) + timedelta(seconds=0.3)
        self.config.save()

        self.run_at()

        self.assertEqual(self.config.last_run_at, NOW)

    def test_should_not_stretch_the_tolerance_beyond_its_minute(self):
        self.config.last_run_at = NOW - timedelta(hours=1) + DUE_TOLERANCE + timedelta(seconds=1)
        self.config.save()

        self.run_at()

        self.assertNotEqual(self.config.last_run_at, NOW)

    def test_should_keep_an_hour_between_posts_whatever_the_row_says(self):
        AnnouncerConfig.objects.filter(pk=self.config.pk).update(time_delta=0)
        self.config.refresh_from_db()
        self.config.last_run_at = NOW - timedelta(minutes=30)
        self.config.save()

        self.run_at()

        self.assertEqual(self.config.last_run_at, NOW - timedelta(minutes=30))


class TestTheFirstWindow(AnnounceTestCase):
    def test_should_cover_the_last_interval_and_start_the_watermark(self):
        inside = make_sale(minutes_ago=30)
        before = make_sale(minutes_ago=90)
        bought = make_sale(minutes_ago=10, is_buy=True)
        self.answer = [inside, before, bought]

        self.run_at()

        self.assertEqual(len(self.titles()), 1)
        self.assertIn("Tritanium x 10", embeds(self.sent)[0].description)
        # the newest transaction of the answer, sold or bought
        self.assertEqual(self.config.last_transaction_id, bought.transaction_id)


class TestTheWatermark(AnnounceTestCase):
    """Windows after the first start after a transaction, not after a time."""

    def setUp(self):
        super().setUp()
        self.seen = make_sale(minutes_ago=120)
        self.config.last_run_at = NOW - timedelta(hours=1)
        self.config.last_transaction_id = self.seen.transaction_id
        self.config.save()

    def test_should_post_a_sale_that_reached_esi_after_the_last_run(self):
        """ESI caches the transactions for up to an hour. A sale made at
        10:50 showed up only after the run at 11:00 had moved the window on,
        dated before it - and a window starting at 11:00 never posted it."""
        late = make_sale(minutes_ago=70)  # sold before the last run
        self.answer = [self.seen, late]

        self.run_at()

        self.assertEqual(len(self.titles()), 1)
        self.assertEqual(self.config.last_transaction_id, late.transaction_id)

    def test_should_not_post_what_the_last_window_already_had(self):
        self.answer = [self.seen]

        self.run_at()

        self.assertEqual(self.titles(), [])
        self.assertEqual(self.config.last_run_at, NOW)

    def test_should_move_past_purchases_without_posting_them(self):
        bought = make_sale(minutes_ago=5, is_buy=True)
        self.answer = [self.seen, bought]

        self.run_at()

        self.assertEqual(self.titles(), [])
        self.assertEqual(self.config.last_transaction_id, bought.transaction_id)

    def test_should_fetch_older_pages_until_it_reaches_the_watermark(self):
        self.page_size = 2
        new = [make_sale(minutes_ago=10 + index) for index in range(5)]
        self.answer = [self.seen, *new]

        self.run_at()

        self.assertIn("Tritanium x 50", embeds(self.sent)[0].description)

    def test_should_stop_after_the_last_page_it_may_fetch(self):
        self.page_size = 1
        self.answer = [self.seen, *[make_sale(minutes_ago=10 + index) for index in range(MAX_PAGES + 2)]]

        with self.assertLogs("extensions.discord_announcer.selects", level="WARNING"):
            self.run_at()

        self.assertIn(f"Tritanium x {10 * MAX_PAGES}", embeds(self.sent)[0].description)


class TestWhatAWindowPosts(AnnounceTestCase):
    def test_should_name_the_hours_covered_in_the_title(self):
        self.config.last_run_at = NOW - timedelta(hours=3)
        self.config.save()
        self.answer = [make_sale(minutes_ago=30)]

        self.run_at()

        self.assertTrue(self.titles()[0].startswith("Sales (last 3 hours): "))

    def test_should_say_hour_for_a_single_one(self):
        self.answer = [make_sale(minutes_ago=30)]

        self.run_at()

        self.assertTrue(self.titles()[0].startswith("Sales (last 1 hour): "))

    def test_should_still_move_on_when_nothing_was_sold(self):
        self.run_at()

        self.assertEqual(self.config.last_run_at, NOW)
        self.assertEqual(self.titles(), [])

    def test_should_keep_the_window_open_when_nothing_could_be_sent(self):
        self.answer = [make_sale(minutes_ago=30)]

        with mock.patch("discord_announcer.discord_bot.discord_bot_active", return_value=False):
            self.run_at()

        self.assertIsNone(self.config.last_run_at)
        self.assertIsNone(self.config.last_transaction_id)
        # but it was tried, and waits its interval before the next attempt
        self.assertEqual(self.config.last_attempt_at, NOW)


class TestAFailingRow(AnnounceTestCase):
    """A row without a usable token fails on every attempt."""

    def fail_with(self, error):
        with mock.patch("discord_announcer.selects.get_transactions", side_effect=error), \
                mock.patch.object(tasks.timezone, "now", return_value=NOW):
            with self.assertLogs(TASK_LOGGER, level="WARNING") as logs:
                discord_announcer_task()

        self.config.refresh_from_db()

        return logs

    def test_should_warn_without_a_traceback(self):
        """96 tracebacks a day for a row that only lacks a token."""
        for error in (
            ValueError("No token"),
            HTTPClientError(403, {}, None),
            TokenInvalidError(),
        ):
            with self.subTest(error=type(error).__name__):
                AnnouncerConfig.objects.filter(pk=self.config.pk).update(last_attempt_at=None)
                logs = self.fail_with(error)

                self.assertEqual([record.levelname for record in logs.records], ["WARNING"])
                self.assertIsNone(logs.records[0].exc_info)

    def test_should_wait_its_interval_before_trying_again(self):
        self.fail_with(ValueError("No token"))

        with mock.patch("discord_announcer.selects.get_transactions") as esi:
            with mock.patch.object(tasks.timezone, "now", return_value=NOW + timedelta(minutes=15)):
                discord_announcer_task()

        esi.assert_not_called()

    def test_should_not_hold_up_the_next_row(self):
        other = make_config(corporation=self.config.corporation, name="Other")

        with mock.patch.object(tasks, "_announce", side_effect=[RuntimeError("boom"), None]) as announce:
            with self.assertLogs(TASK_LOGGER, level="ERROR"):
                discord_announcer_task()

        self.assertEqual(
            sorted(call.args[0].pk for call in announce.call_args_list),
            sorted([self.config.pk, other.pk]),
        )


class TestTheTask(DiscordAnnouncerTestCase):
    def test_should_run_once_at_a_time(self):
        """After a worker outage beat queues the task several times; run side
        by side, each copy saw the same last_run_at and posted the same sales."""
        self.assertIsInstance(discord_announcer_task, QueueOnce)

    def test_should_leave_inactive_rows_alone(self):
        make_config(is_active=False)

        with mock.patch.object(tasks, "_announce") as announce:
            discord_announcer_task()

        announce.assert_not_called()
