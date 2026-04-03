from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from traces.models import ApiToken
from traces.trace_processing import _upload_quota, create_trace


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

    if not user.profile.is_premium:
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

    trace, error = create_trace(gpx_file, user)
    if error:
        return JsonResponse({"error": error}, status=400)

    return JsonResponse({"id": trace.pk, "uuid": str(trace.uuid)}, status=201)
