from uuid import uuid4

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class TraceUploadForm(forms.Form):
    gpx_file = forms.FileField(label=_("GPX file"))


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label=_("Email"))

    class Meta:
        model = User
        fields = ("email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("This email address is already in use."))
        return email

    def save(self, commit=True):
        self.instance.username = uuid4().hex[:30]
        return super().save(commit=commit)
