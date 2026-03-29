from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render

from traces.models import Trace


@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard_traces(request):
    traces = (
        Trace.objects.filter(status=Trace.STATUS_NOT_ANALYZED)
        .select_related("uploaded_by")
        .order_by("-uploaded_at")[:10]
    )

    return render(
        request,
        "traces/admin_dashboard_traces.html",
        {"traces": traces},
    )
