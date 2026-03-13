from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect

from traces.models import Trace


@login_required
def delete_trace(request, pk):
    trace = get_object_or_404(Trace, pk=pk)
    if request.method == "POST":
        trace.delete()
    return redirect("trace_list")
