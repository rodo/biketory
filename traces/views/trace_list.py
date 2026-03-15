from django.contrib.auth.decorators import login_required
from django.contrib.gis.db.models.functions import Length
from django.core.paginator import Paginator
from django.shortcuts import render

from traces.models import Trace


@login_required
def trace_list(request):
    qs = (
        Trace.objects
        .filter(uploaded_by=request.user)
        .annotate(length_m=Length("route"))
        .order_by("-uploaded_at")
    )
    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "traces/trace_list.html", {"page": page})
