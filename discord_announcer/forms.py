"""App Forms"""

# Django
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Alliance Auth
from allianceauth.eveonline.models import EveCorporationInfo

from discord_announcer.models import AnnouncerConfig

# One datalist per page, shared by the corporation inputs of all rows
CORPORATION_DATALIST_ID = "discord-announcer-corporations"


class CorporationByNameField(forms.ModelChoiceField):
    """Corporation picked by name from a datalist, like the AA optimer's DataListWidget."""

    def __init__(self, **kwargs):
        super().__init__(
            queryset=EveCorporationInfo.objects.order_by("corporation_name"),
            to_field_name="corporation_name",
            widget=forms.TextInput(
                attrs={"list": CORPORATION_DATALIST_ID, "autocomplete": "off"}
            ),
            **kwargs,
        )

    def to_python(self, value):
        if value in self.empty_values:
            return None

        # names are not unique in the database, so no .get() here
        corporation = self.queryset.filter(corporation_name=value.strip()).first()

        if corporation is None:
            raise ValidationError(
                _("Unknown corporation. Pick one of the suggestions."),
                code="invalid_choice",
            )

        return corporation


class AnnouncerConfigForm(forms.ModelForm):
    """One row of the announcer configuration formset"""

    corporation = CorporationByNameField(
        label=_("Corporation"),
        help_text=_("Type to search, then pick one of the suggestions."),
    )

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

        # the input shows the name, the model stores the foreign key
        if self.instance.pk:
            self.initial["corporation"] = self.instance.corporation.corporation_name

        # A callable model default makes Django expect a hidden "initial-" input,
        # which the bootstrap fields do not render; without it the untouched empty
        # row counts as changed and blocks saving. The default is stable, so off.
        self.fields["time_delta"].show_hidden_initial = False

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
