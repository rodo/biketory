from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from traces.models import Friendship, UserSurfaceStats

user_model = get_user_model()


def _get_friends(user):
    """Return queryset of accepted friends for user."""
    friend_ids = Friendship.objects.filter(
        Q(from_user=user, status=Friendship.STATUS_ACCEPTED) |
        Q(to_user=user, status=Friendship.STATUS_ACCEPTED)
    ).values_list("from_user_id", "to_user_id")
    ids = {uid for pair in friend_ids for uid in pair} - {user.pk}
    return user_model.objects.filter(pk__in=ids)


@login_required
def friends(request):
    user = request.user
    error = None
    search_results = None
    query = ""

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "search":
            query = request.POST.get("q", "").strip()
            if query:
                # Search by username (partial) or exact UUID secret
                try:
                    import uuid as _uuid
                    _uuid.UUID(query)
                    # Looks like a UUID — search by secret_uuid
                    stats_qs = UserSurfaceStats.objects.filter(secret_uuid=query).select_related("user")
                    candidates = [s.user for s in stats_qs]
                except ValueError:
                    # Search by username (case-insensitive partial)
                    candidates = list(
                        user_model.objects.filter(username__icontains=query).exclude(pk=user.pk)[:20]
                    )

                # Annotate each candidate with friendship status
                existing = {
                    f.from_user_id: f for f in Friendship.objects.filter(from_user=user, to_user__in=candidates)
                }
                existing.update({
                    f.to_user_id: f for f in Friendship.objects.filter(to_user=user, from_user__in=candidates)
                })

                search_results = []
                for c in candidates:
                    if c.pk == user.pk:
                        continue
                    f = existing.get(c.pk)
                    if f:
                        if f.status == Friendship.STATUS_ACCEPTED:
                            rel = "friend"
                        elif f.from_user_id == user.pk:
                            rel = "sent"
                        else:
                            rel = "received"
                    else:
                        rel = "none"
                    search_results.append({"user": c, "rel": rel, "friendship": f})

        elif action == "send":
            to_id = request.POST.get("to_user_id")
            to_user = get_object_or_404(user_model, pk=to_id)
            if to_user != user:
                Friendship.objects.get_or_create(from_user=user, to_user=to_user)
            return redirect("friends")

        elif action == "accept":
            f_id = request.POST.get("friendship_id")
            f = get_object_or_404(Friendship, pk=f_id, to_user=user, status=Friendship.STATUS_PENDING)
            f.status = Friendship.STATUS_ACCEPTED
            f.save()
            return redirect("friends")

        elif action == "decline":
            f_id = request.POST.get("friendship_id")
            f = get_object_or_404(Friendship, pk=f_id, to_user=user)
            f.delete()
            return redirect("friends")

        elif action == "cancel":
            f_id = request.POST.get("friendship_id")
            f = get_object_or_404(Friendship, pk=f_id, from_user=user)
            f.delete()
            return redirect("friends")

        elif action == "remove":
            f_id = request.POST.get("friendship_id")
            f = get_object_or_404(
                Friendship,
                Q(from_user=user) | Q(to_user=user),
                pk=f_id,
                status=Friendship.STATUS_ACCEPTED,
            )
            f.delete()
            return redirect("friends")

    # Build friends list with stats
    friend_users = _get_friends(user)
    stats_map = {
        s.user_id: s
        for s in UserSurfaceStats.objects.filter(user__in=friend_users)
    }
    friends_data = []
    for f in friend_users:
        fs = Friendship.objects.filter(
            Q(from_user=user, to_user=f) | Q(to_user=user, from_user=f)
        ).first()
        friends_data.append({
            "user": f,
            "stats": stats_map.get(f.pk),
            "friendship_id": fs.pk if fs else None,
        })

    # Pending received
    pending_received = Friendship.objects.filter(
        to_user=user, status=Friendship.STATUS_PENDING
    ).select_related("from_user")

    # Pending sent
    pending_sent = Friendship.objects.filter(
        from_user=user, status=Friendship.STATUS_PENDING
    ).select_related("to_user")

    return render(request, "traces/friends.html", {
        "friends_data": friends_data,
        "pending_received": pending_received,
        "pending_sent": pending_sent,
        "search_results": search_results,
        "query": query,
        "error": error,
    })
