from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from referrals.emails import send_referral_email
from referrals.forms import ReferralForm
from referrals.models import Referral


@login_required
def referral_list(request):
    if request.method == "POST":
        form = ReferralForm(request.POST, sponsor=request.user)
        if form.is_valid():
            referral = Referral.objects.create(
                sponsor=request.user,
                email=form.cleaned_data["email"],
            )
            send_referral_email(referral)
            return redirect("referral_list")
    else:
        form = ReferralForm(sponsor=request.user)

    referrals = Referral.objects.filter(sponsor=request.user).order_by("-created_at")
    limit_reached = referrals.count() >= settings.MAX_REFERRALS

    return render(request, "referrals/referral_list.html", {
        "form": form,
        "referrals": referrals,
        "limit_reached": limit_reached,
        "max_referrals": settings.MAX_REFERRALS,
    })


@login_required
def referral_delete(request, pk):
    referral = get_object_or_404(
        Referral, pk=pk, sponsor=request.user, status=Referral.PENDING
    )
    if request.method == "POST":
        referral.delete()
    return redirect("referral_list")
