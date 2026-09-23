"""App Forms"""

# Django
from django import forms
from django.utils.translation import gettext_lazy as _

# Alliance Auth
from allianceauth.eveonline.models import EveCorporationInfo

from discord_announcer.models import AnnouncerConfig


class AnnouncerConfigForm(forms.ModelForm):
    """One row of the announcer configuration formset"""

    class Meta:
        model = AnnouncerConfig
        fields = [
            "name",
            "corporation",
            "division",
            "channel_id",
            "time_delta",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["corporation"].queryset = EveCorporationInfo.objects.order_by(
            "corporation_name"
        )
        self.fields["channel_id"].help_text = _(
            "Enable Developer Mode in Discord, then right-click the channel "
            '→ "Copy Channel ID".'
        )

    def save(self, commit=True):
        # A reactivated row starts a fresh window, instead of posting
        # everything sold while it was switched off.
        if "is_active" in self.changed_data and self.instance.is_active:
            self.instance.last_run_at = None

        return super().save(commit=commit)


AnnouncerConfigFormSet = forms.modelformset_factory(
    AnnouncerConfig,
    form=AnnouncerConfigForm,
    extra=1,
    can_delete=True,
)
