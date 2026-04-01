from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Polygon
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from procrastinate.exceptions import AlreadyEnqueued

from traces.forms import TraceUploadForm
from traces.models import Trace
from traces.trace_processing import (
    MAX_TRACE_LENGTH_KM,
    _create_trace_hexagons,
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
                        _(
                            "Trace too long (%(length).0f km)."
                            " Maximum allowed is %(max)d km."
                        ) % {"length": length_km, "max": MAX_TRACE_LENGTH_KM},
                    )
                elif first_point_date and Trace.objects.filter(
                    uploaded_by=request.user, first_point_date=first_point_date
                ).exists():
                    form.add_error(
                        "gpx_file",
                        _("This trace has already been uploaded (same start date detected)."),
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
                        extent = route.extent  # (xmin, ymin, xmax, ymax)
                        buf = 0.01
                        bbox = Polygon.from_bbox((
                            extent[0] - buf, extent[1] - buf,
                            extent[2] + buf, extent[3] + buf,
                        ))
                        bbox.srid = 4326
                        trace.bbox = bbox
                        trace.save(update_fields=["bbox"])
                    from traces.tasks import (
                        award_trace_badges,
                        extract_surfaces,
                        generate_tiles,
                        generate_user_tiles,
                    )
                    try:
                        extract_surfaces.configure(
                            queueing_lock=f"extract_surfaces_{trace.pk}",
                        ).defer(trace_id=trace.pk)
                    except AlreadyEnqueued:
                        pass
                    try:
                        award_trace_badges.configure(
                            queueing_lock=f"award_badges_{trace.pk}",
                        ).defer(trace_id=trace.pk)
                    except AlreadyEnqueued:
                        pass
                    if route:
                        for zoom in range(settings.TILES_STATIC_MIN_ZOOM, settings.TILES_STATIC_MAX_ZOOM + 1):
                            try:
                                generate_tiles.configure(
                                    queueing_lock=f"generate_tiles_{trace.pk}_{zoom}",
                                ).defer(trace_id=trace.pk, zoom=zoom)
                            except AlreadyEnqueued:
                                pass
                        from traces.models import Subscription
                        sub = Subscription.objects.filter(user=request.user).first()
                        if sub and sub.is_active():
                            for zoom in range(settings.TILES_STATIC_MIN_ZOOM, settings.TILES_STATIC_MAX_ZOOM + 1):
                                try:
                                    generate_user_tiles.configure(
                                        queueing_lock=f"generate_user_tiles_{request.user.pk}_{trace.pk}_{zoom}",
                                    ).defer(trace_id=trace.pk, user_id=request.user.pk, zoom=zoom)
                                except AlreadyEnqueued:
                                    pass
                    _reward_referral_sponsor(request.user)
                    return redirect("trace_detail", trace_uuid=trace.uuid)
    else:
        form = TraceUploadForm()

    return render(request, "traces/upload.html", {
        "form": form,
        "uploads_today": uploads_today,
        "daily_limit": daily_limit,
        "limit_reached": limit_reached,
        "next_slot": next_slot,
    })


def _reward_referral_sponsor(user):
    if Trace.objects.filter(uploaded_by=user).count() != 1:
        return

    from referrals.models import Referral

    referral = Referral.objects.filter(
        referee=user, status=Referral.ACCEPTED, rewarded=False
    ).first()
    if not referral:
        return

    import datetime

    from dateutil.relativedelta import relativedelta

    from traces.models import Subscription

    today = datetime.date.today()
    sub, created = Subscription.objects.get_or_create(
        user=referral.sponsor,
        defaults={"start_date": today, "end_date": today + relativedelta(months=1)},
    )
    if not created:
        sub.end_date = max(sub.end_date, today) + relativedelta(months=1)
        sub.save(update_fields=["end_date"])

    referral.rewarded = True
    referral.save(update_fields=["rewarded"])
