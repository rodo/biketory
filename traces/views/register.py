from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.utils import timezone

from traces.forms import RegistrationForm


def register(request):
    ref_token = request.POST.get("ref", "") or request.GET.get("ref", "")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")

            if ref_token:
                _accept_referral(ref_token, user)

            return redirect("landing")
    else:
        initial = {}
        if ref_token:
            from referrals.models import Referral

            referral = Referral.objects.filter(
                token=ref_token, status=Referral.PENDING
            ).first()
            if referral:
                initial["email"] = referral.email
        form = RegistrationForm(initial=initial)

    return render(request, "registration/register.html", {
        "form": form,
        "ref_token": ref_token,
    })


def _accept_referral(token, user):
    from notifs.helpers import notify
    from notifs.models import Notification
    from referrals.models import Referral

    referral = Referral.objects.filter(
        token=token, status=Referral.PENDING
    ).first()
    if not referral:
        return

    referral.status = Referral.ACCEPTED
    referral.referee = user
    referral.accepted_at = timezone.now()
    referral.save(update_fields=["status", "referee", "accepted_at"])

    notify(
        user=referral.sponsor,
        notification_type=Notification.REFERRAL_SIGNUP,
        message=f"{user.username} a rejoint Biketory grace a votre invitation !",
        link="/referrals/",
    )
