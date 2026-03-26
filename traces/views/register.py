from django.contrib.auth import login
from django.shortcuts import redirect, render

from traces.forms import RegistrationForm


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return redirect("landing")
    else:
        form = RegistrationForm()
    return render(request, "registration/register.html", {"form": form})
