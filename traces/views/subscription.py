from django.shortcuts import render


def subscription_required(request):
    return render(request, "traces/subscription_required.html")
