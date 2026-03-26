from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from traces.badge_award import award_badges
from traces.forms import TraceUploadForm
from traces.models import Trace
from traces.trace_processing import (
    MAX_TRACE_LENGTH_KM,
    _create_trace_hexagons,
    _extract_surfaces,
    _parse_route,
    _upload_quota,
)


@login_required
def upload_trace(request):
    uploads_today, daily_limit, next_slot = _upload_quota(request.user)
    limit_reached = next_slot is not None

    if request.method == "POST":
        if limit_reached:
            form = TraceUploadForm()
        else:
            form = TraceUploadForm(request.POST, request.FILES)
            if form.is_valid():
                gpx_file = form.cleaned_data["gpx_file"]
                route, first_point_date, length_km = _parse_route(gpx_file)
                if length_km > MAX_TRACE_LENGTH_KM:
                    form.add_error(
                        "gpx_file",
                        f"Trace too long ({length_km:.0f} km). Maximum allowed is {MAX_TRACE_LENGTH_KM} km.",
                    )
                elif first_point_date and Trace.objects.filter(
                    uploaded_by=request.user, first_point_date=first_point_date
                ).exists():
                    form.add_error(
                        "gpx_file",
                        "Cette trace a déjà été uploadée (même date de départ détectée).",
                    )
                else:
                    trace = Trace.objects.create(
                        gpx_file=gpx_file,
                        route=route,
                        length_km=length_km,
                        first_point_date=first_point_date,
                        uploaded_by=request.user,
                    )
                    if route:
                        _create_trace_hexagons(route)
                        _extract_surfaces(trace)
                    award_badges(request.user, trace)
                    return redirect("trace_detail", pk=trace.pk)
    else:
        form = TraceUploadForm()

    return render(request, "traces/upload.html", {
        "form": form,
        "uploads_today": uploads_today,
        "daily_limit": daily_limit,
        "limit_reached": limit_reached,
        "next_slot": next_slot,
    })
