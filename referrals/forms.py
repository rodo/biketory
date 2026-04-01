from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from referrals.models import Referral


class ReferralForm(forms.Form):
    email = forms.EmailField(label=_("Email"))

    def __init__(self, *args, sponsor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.sponsor = sponsor

    def clean_email(self):
        email = self.cleaned_data["email"]

        if self.sponsor and self.sponsor.email == email:
            raise forms.ValidationError(_("You cannot invite yourself."))

        user_model = get_user_model()
        if user_model.objects.filter(email=email).exists():
            raise forms.ValidationError(
                _("This email belongs to an existing user.")
            )

        if self.sponsor and Referral.objects.filter(
            sponsor=self.sponsor, email=email
        ).exists():
            raise forms.ValidationError(
                _("You have already invited this email.")
            )

        if self.sponsor and Referral.objects.filter(
            sponsor=self.sponsor
        ).count() >= settings.MAX_REFERRALS:
            raise forms.ValidationError(
                _("You have reached the maximum number of invitations (%(max)d).")
                % {"max": settings.MAX_REFERRALS}
            )

        return email
