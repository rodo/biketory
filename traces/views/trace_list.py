from django.contrib.auth.decorators import login_required
from django.contrib.gis.db.models.functions import Length
from django.core.paginator import Paginator
from django.shortcuts import render

from traces.models import Trace


ALLOWED_SORTS = {
    "file": "gpx_file",
    "date": "first_point_date",
    "length": "length_m",
    "uploaded": "uploaded_at",
}
DEFAULT_SORT = "uploaded"
DEFAULT_ORDER = "desc"


@login_required
def trace_list(request):
    sort = request.GET.get("sort", DEFAULT_SORT)
    order = request.GET.get("order", DEFAULT_ORDER)

    if sort not in ALLOWED_SORTS:
        sort = DEFAULT_SORT
    if order not in ("asc", "desc"):
        order = DEFAULT_ORDER

    order_field = ALLOWED_SORTS[sort]
    if order == "desc":
        order_field = "-" + order_field

    qs = (
        Trace.objects
        .filter(uploaded_by=request.user)
        .annotate(length_m=Length("route"))
        .order_by(order_field)
    )
    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "traces/trace_list.html", {
        "page": page,
        "current_sort": sort,
        "current_order": order,
    })
