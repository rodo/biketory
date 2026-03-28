from django.shortcuts import render


def stats(request):
    return render(request, "traces/stats.html")
