from functools import wraps

from django.shortcuts import redirect


def premium_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("account_login")
        sub = getattr(request.user, "subscription", None)
        if sub and sub.is_active():
            return view_func(request, *args, **kwargs)
        return redirect("subscription_required")
    return wrapper
