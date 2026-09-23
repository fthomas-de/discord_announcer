"""
App Models
Create your models in here
"""

# Django
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

# Alliance Auth
from allianceauth.eveonline.models import EveCorporationInfo

from discord_announcer.app_settings import TIME_DELTA


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
    periodic task per corp/channel combination.
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
        verbose_name=_("Wallet Division"),
        help_text=_("Corporation wallet division to read (1-7)."),
    )
    channel_id = models.PositiveBigIntegerField(
        verbose_name=_("Discord Channel ID"),
        help_text=_("Numeric Discord channel ID to post the announcement to."),
    )
    time_delta = models.PositiveIntegerField(
        default=TIME_DELTA,
        validators=[MinValueValidator(1)],
        verbose_name=_("Interval (hours)"),
        help_text=_(
            "Posts every this many hours, covering the sales since the previous "
            "post. At least one hour."
        ),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    # end of the last window that was handled, sent or empty; the next window starts here
    last_run_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        verbose_name=_("Last run at"),
    )

    class Meta:
        """Meta definitions"""

        default_permissions = ()
        verbose_name = _("Announcer Configuration")
        verbose_name_plural = _("Announcer Configurations")

    def __str__(self) -> str:
        return self.name
