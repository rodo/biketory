from django.contrib.auth.decorators import login_required
from django.contrib.gis.db.models.functions import Length
from django.shortcuts import render

from traces.models import Trace


@login_required
def trace_list(request):
    traces = (
        Trace.objects
        .filter(uploaded_by=request.user)
        .annotate(length_m=Length("route"))
        .order_by("-uploaded_at")
    )
    return render(request, "traces/trace_list.html", {"traces": traces})
