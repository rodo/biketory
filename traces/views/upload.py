from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from traces.forms import TraceUploadForm
from traces.trace_processing import _upload_quota, create_trace


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
                trace, error = create_trace(form.cleaned_data["gpx_file"], request.user)
                if error:
                    form.add_error("gpx_file", error)
                else:
                    return redirect("trace_detail", trace_uuid=trace.uuid)
    else:
        form = TraceUploadForm()

    return render(request, "traces/upload.html", {
        "form": form,
        "uploads_today": uploads_today,
        "daily_limit": daily_limit,
        "limit_reached": limit_reached,
        "next_slot": next_slot,
        "strava_auth_enabled": settings.STRAVA_AUTH_ENABLED,
    })
