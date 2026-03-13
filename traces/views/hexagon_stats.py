from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import render

from traces.models import Hexagon, HexagonScore


@login_required
def hexagon_stats(request):
    total_hexagons = Hexagon.objects.count()

    per_user = (
        HexagonScore.objects
        .values("user__username")
        .annotate(hexagon_count=Count("hexagon"), total_points=Sum("points"))
        .order_by("-total_points")
    )

    context = {
        "total_hexagons": total_hexagons,
        "per_user": per_user,
    }
    return render(request, "traces/hexagon_stats.html", context)
