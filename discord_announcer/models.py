"""App models"""

# Django
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

# Alliance Auth
from allianceauth.eveonline.models import EveCorporationInfo

from discord_announcer.app_settings import TIME_DELTA


# A callable, so migrations store a reference instead of freezing this install's TIME_DELTA. Referenced by migrations.
def default_interval() -> int:
    return TIME_DELTA


class General(models.Model):
    """Meta model for app permissions"""

    class Meta:
        """Meta definitions"""

        managed = False
        default_permissions = ()
        permissions = (("basic_access", "Can access this app"),)


class AnnouncerConfig(models.Model):
    """One sales announcement job: what to look at and where to post it.

    Replaces the earlier approach of one manually configured Celery Beat
    periodic task per corporation, division and channel.
    """

    name = models.CharField(
        max_length=100,
        verbose_name=_("Name"),
        help_text=_("A short label to tell configurations apart."),
    )
    corporation = models.ForeignKey(
        EveCorporationInfo,
        on_delete=models.CASCADE,
        related_name="discord_announcer_configs",
        verbose_name=_("Corporation"),
    )
    division = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(7)],
        verbose_name=_("Wallet division"),
        help_text=_("Corporation wallet division to read (1-7)."),
    )
    channel_id = models.PositiveBigIntegerField(
        verbose_name=_("Discord channel ID"),
        help_text=_(
            "Numeric ID of the channel to post to. Enable Developer Mode in "
            'Discord, then right-click the channel → "Copy Channel ID".'
        ),
    )
    time_delta = models.PositiveIntegerField(
        default=default_interval,
        validators=[MinValueValidator(1)],
        verbose_name=_("Interval (hours)"),
        help_text=_(
            "How often this configuration posts, in hours. Each post covers the "
            "sales since its previous run. At least one hour."
        ),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    # end of the last window that was handled, sent or empty
    last_run_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        verbose_name=_("Last run at"),
    )
    # The newest transaction the last handled window saw, sold or bought. The
    # next window starts after it rather than after a point in time: ESI hands
    # out the transactions from a cache of up to an hour, so a sale made
    # shortly before a run shows up only in a later answer - dated before the
    # run, and lost to a window that starts at the run's own time.
    last_transaction_id = models.BigIntegerField(
        null=True,
        blank=True,
        editable=False,
        verbose_name=_("Last transaction seen"),
    )
    # When the task last tried this row, successful or not. A row that fails -
    # no token, a missing role - is tried again one interval later rather than
    # on every tick of the periodic task.
    last_attempt_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        verbose_name=_("Last attempt at"),
    )

    class Meta:
        """Meta definitions"""

        default_permissions = ()
        verbose_name = _("Announcer configuration")
        verbose_name_plural = _("Announcer configurations")

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        # A reactivated row starts a fresh window instead of posting
        # everything sold while it was switched off. Here rather than in the
        # page's form, so the Django admin does the same.
        if self.pk and self.is_active:
            was_active = (
                type(self).objects.filter(pk=self.pk).values_list("is_active", flat=True).first()
            )

            if was_active is False:
                self.last_run_at = None
                self.last_transaction_id = None
                self.last_attempt_at = None

        super().save(*args, **kwargs)
