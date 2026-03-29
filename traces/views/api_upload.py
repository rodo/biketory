from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from traces.models import ApiToken, Subscription, Trace
from traces.trace_processing import (
    MAX_TRACE_LENGTH_KM,
    _create_trace_hexagons,
    _extract_surfaces,
    _parse_route,
    _upload_quota,
)


def _authenticate(request):
    """Return the User if the Bearer token is valid, else None."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    raw = auth[len("Bearer "):]
    try:
        api_token = ApiToken.objects.select_related("user").get(token=raw)
    except ApiToken.DoesNotExist:
        return None
    if not api_token.is_valid:
        return None
    return api_token.user


@csrf_exempt
@require_POST
def api_upload_trace(request):
    user = _authenticate(request)
    if user is None:
        return JsonResponse({"error": _("Invalid or expired token.")}, status=401)

    sub = Subscription.objects.filter(user=user).first()
    if not sub or not sub.is_active():
        return JsonResponse({"error": _("API access requires an active Premium subscription.")}, status=403)

    gpx_file = request.FILES.get("gpx_file")
    if gpx_file is None:
        return JsonResponse({"error": _("Missing gpx_file field.")}, status=400)

    _count, daily_limit, next_slot = _upload_quota(user)
    if next_slot is not None:
        return JsonResponse(
            {
                "error": _("Daily upload limit reached."),
                "limit": daily_limit,
                "next_slot": next_slot.isoformat(),
            },
            status=429,
        )

    route, first_point_date, length_km = _parse_route(gpx_file)
    if length_km > MAX_TRACE_LENGTH_KM:
        return JsonResponse(
            {
                "error": _(
                    "Trace too long (%(length).0f km). Maximum is %(max)d km."
                ) % {"length": length_km, "max": MAX_TRACE_LENGTH_KM},
            },
            status=400,
        )

    trace = Trace.objects.create(
        gpx_file=gpx_file,
        route=route,
        first_point_date=first_point_date,
        uploaded_by=user,
    )
    if route:
        _create_trace_hexagons(route)
        _extract_surfaces(trace)

    return JsonResponse({"id": trace.pk, "extracted": trace.extracted}, status=201)
