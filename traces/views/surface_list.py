from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from traces.models import ClosedSurface


@login_required
def surface_list(request):
    surfaces = (
        ClosedSurface.objects
        .select_related("owner", "trace")
        .order_by("-detected_at")
    )
    return render(request, "traces/surface_list.html", {"surfaces": surfaces})
