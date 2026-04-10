from datetime import timedelta

from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone
from procrastinate.contrib.django.models import ProcrastinateJob, ProcrastinateWorker


@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard_workers(request):
    # Workers with a heartbeat in the last 2 minutes are considered alive
    alive_cutoff = timezone.now() - timedelta(minutes=2)
    workers = ProcrastinateWorker.objects.order_by("-last_heartbeat")
    active_count = workers.filter(last_heartbeat__gte=alive_cutoff).count()

    recent_jobs = (
        ProcrastinateJob.objects.select_related("worker")
        .order_by("-id")[:20]
    )

    job_counts = {
        "todo": ProcrastinateJob.objects.filter(status="todo").count(),
        "doing": ProcrastinateJob.objects.filter(status="doing").count(),
        "succeeded": ProcrastinateJob.objects.filter(status="succeeded").count(),
        "failed": ProcrastinateJob.objects.filter(status="failed").count(),
    }

    # Pending jobs (todo + doing) grouped by queue
    pending_by_queue = list(
        ProcrastinateJob.objects.filter(status__in=["todo", "doing"])
        .values("queue_name")
        .annotate(
            todo=Count("id", filter=Q(status="todo")),
            doing=Count("id", filter=Q(status="doing")),
        )
        .order_by("queue_name")
    )

    return render(
        request,
        "traces/admin_dashboard_workers.html",
        {
            "workers": workers,
            "active_count": active_count,
            "recent_jobs": recent_jobs,
            "job_counts": job_counts,
            "alive_cutoff": alive_cutoff,
            "pending_by_queue": pending_by_queue,
        },
    )
