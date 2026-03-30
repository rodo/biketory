import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from traces.base62 import uuid_to_base62
from traces.models import (
    ApiToken,
    Subscription,
    UserProfile,
    UserSurfaceStats,
)


@login_required
def settings(request):
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "generate_token":
            sub = Subscription.objects.filter(user=request.user).first()
            if sub and sub.is_active():
                ApiToken.objects.filter(user=request.user).delete()
                ApiToken.objects.create(
                    user=request.user,
                    expires_at=timezone.now() + timedelta(days=31),
                )
            return redirect("settings")

        if action == "update_home_location":
            try:
                lat = float(request.POST.get("lat", ""))
                lng = float(request.POST.get("lng", ""))
                from django.contrib.gis.geos import Point
                profile, _created = UserProfile.objects.get_or_create(user=request.user)
                profile.home_location = Point(lng, lat, srid=4326)
                profile.save(update_fields=["home_location"])
            except (ValueError, TypeError):
                pass
            return redirect("settings")

        if action == "update_username":
            new_username = request.POST.get("username", "").strip()
            username_error = None
            if not new_username:
                username_error = _("The username cannot be empty.")
            elif len(new_username) > 150:
                username_error = _("The username must be 150 characters or fewer.")
            elif not re.match(r'^[\w.@+-]+$', new_username):
                username_error = _("The username may only contain letters, digits, and @/./+/-/_ characters.")
            else:
                user_model = get_user_model()
                if user_model.objects.filter(username=new_username).exclude(pk=request.user.pk).exists():
                    username_error = _("This username is already taken.")
                else:
                    request.user.username = new_username
                    request.user.save(update_fields=["username"])
                    return redirect("settings")
            request.username_error = username_error

        if action == "update_email":
            new_email = request.POST.get("email", "").strip()
            email_error = None
            if not new_email:
                email_error = _("The email address cannot be empty.")
            elif "@" not in new_email:
                email_error = _("Invalid email address.")
            else:
                user_model = get_user_model()
                if user_model.objects.filter(email=new_email).exclude(pk=request.user.pk).exists():
                    email_error = _("This email address is already in use.")
                else:
                    request.user.email = new_email
                    request.user.save(update_fields=["email"])
                    return redirect("settings")
            request.email_error = email_error

    user = request.user
    sub = Subscription.objects.filter(user=user).first()
    is_premium = sub is not None and sub.is_active()
    api_token = ApiToken.objects.filter(user=user).first() if is_premium else None
    username_error = getattr(request, "username_error", None)
    email_error = getattr(request, "email_error", None)
    user_profile, _created = UserProfile.objects.get_or_create(user=user)
    home_location = user_profile.home_location

    stats, _created = UserSurfaceStats.objects.get_or_create(user=user)
    share_code = uuid_to_base62(stats.secret_uuid)
    share_url = request.build_absolute_uri(f"/s/{share_code}/")

    return render(request, "traces/settings.html", {
        "share_url": share_url,
        "secret_uuid": stats.secret_uuid,
        "api_token": api_token,
        "is_premium": is_premium,
        "username_error": username_error,
        "email_error": email_error,
        "home_location": home_location,
    })
