from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render


@staff_member_required
def trace_create(request):
    return render(request, "traces/trace_create.html")
