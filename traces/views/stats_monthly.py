from django.shortcuts import render


def stats_monthly(request):
    return render(request, "traces/stats_monthly.html")
