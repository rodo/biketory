from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from traces.models import Subscription


@login_required
def subscription_history(request):
    subscriptions = Subscription.objects.filter(user=request.user)
    return render(request, "traces/subscription_history.html", {
        "subscriptions": subscriptions,
    })
