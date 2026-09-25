"""The configuration row itself: its window on reactivation, and migrations
that do not depend on this install's settings."""

from io import StringIO
from unittest import mock

from django.contrib.admin.sites import AdminSite
from django.core.management import call_command
from django.test import RequestFactory

from discord_announcer import models
from discord_announcer.admin import AnnouncerConfigAdmin
from discord_announcer.models import AnnouncerConfig

from .base import NOW, DiscordAnnouncerTestCase, make_config


class TestReactivation(DiscordAnnouncerTestCase):
    def setUp(self):
        self.config = make_config(is_active=False)
        AnnouncerConfig.objects.filter(pk=self.config.pk).update(
            last_run_at=NOW, last_transaction_id=77, last_attempt_at=NOW
        )
        self.config.refresh_from_db()

    def assertFreshWindow(self):
        self.config.refresh_from_db()
        self.assertIsNone(self.config.last_run_at)
        self.assertIsNone(self.config.last_transaction_id)
        self.assertIsNone(self.config.last_attempt_at)

    def test_should_start_a_fresh_window_when_switched_back_on(self):
        """Instead of posting everything sold while the row was off."""
        self.config.is_active = True
        self.config.save()

        self.assertFreshWindow()

    def test_should_do_the_same_from_the_django_admin(self):
        """The page's form used to be the only place that reset it."""
        self.config.is_active = True
        admin = AnnouncerConfigAdmin(AnnouncerConfig, AdminSite())

        admin.save_model(RequestFactory().post("/"), self.config, form=None, change=True)

        self.assertFreshWindow()

    def test_should_keep_the_window_of_a_row_that_stays_active(self):
        AnnouncerConfig.objects.filter(pk=self.config.pk).update(is_active=True)
        self.config.refresh_from_db()
        self.config.name = "Renamed"
        self.config.save()

        self.config.refresh_from_db()
        self.assertEqual(self.config.last_transaction_id, 77)


class TestMigrations(DiscordAnnouncerTestCase):
    def check(self):
        try:
            call_command(
                "makemigrations", "discord_announcer", check=True, dry_run=True,
                verbosity=0, stdout=StringIO(), stderr=StringIO(),
            )
        except SystemExit:
            self.fail("discord_announcer has model changes without a migration")

    def test_should_have_a_migration_for_every_model_change(self):
        self.check()

    def test_should_not_depend_on_the_configured_interval(self):
        """A default read from settings is frozen into the migration, and
        every install with another TIME_DELTA is asked to run makemigrations."""
        with mock.patch.object(models, "TIME_DELTA", 5):
            self.check()
