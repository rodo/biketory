from django.shortcuts import render


def stats_traces(request):
    return render(request, "traces/stats_traces.html")
