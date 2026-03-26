from django.shortcuts import render


def about(request):
    return render(request, "traces/about.html")
