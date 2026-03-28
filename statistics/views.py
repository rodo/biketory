from django.core.management import call_command
from django.http import JsonResponse


def api_compute_stats(request):
    """Run compute_stats for a given granularity. DEBUG-only endpoint."""
    granularity = request.GET.get("granularity", "all")
    date_from = request.GET.get("from")
    date_to = request.GET.get("to")

    args = [granularity]
    kwargs = {}
    if date_from:
        kwargs["date_from"] = date_from
    if date_to:
        kwargs["date_to"] = date_to

    call_command("compute_stats", *args, **kwargs)

    return JsonResponse({"status": "ok", "granularity": granularity})
