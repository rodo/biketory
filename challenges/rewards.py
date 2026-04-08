"""Award rewards to challenge winners (badges + subscriptions)."""

import datetime
import logging

from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model

from challenges.models import ChallengeLeaderboardEntry, ChallengeReward

logger = logging.getLogger(__name__)

_DURATION_MAP = {
    ChallengeReward.REWARD_SUB_3M: relativedelta(months=3),
    ChallengeReward.REWARD_SUB_6M: relativedelta(months=6),
    ChallengeReward.REWARD_SUB_1Y: relativedelta(years=1),
}


def award_challenge_rewards(challenge):
    """Award all configured rewards for a challenge.

    Should be called once after the final leaderboard computation.
    """
    rewards = list(challenge.rewards.all())
    if not rewards:
        return

    entries = list(
        ChallengeLeaderboardEntry.objects.filter(challenge=challenge).order_by("rank")
    )
    if not entries:
        return

    user_model = get_user_model()

    for reward in rewards:
        winners = [e for e in entries if e.rank <= reward.rank_threshold and e.goal_met]

        for entry in winners:
            try:
                user = user_model.objects.get(pk=entry.user_id)
            except user_model.DoesNotExist:
                continue

            if reward.reward_type == ChallengeReward.REWARD_BADGE:
                _award_badge(user, reward.badge_id, challenge)
            elif reward.reward_type in _DURATION_MAP:
                _award_subscription(user, reward.reward_type, challenge)


def _award_badge(user, badge_id, challenge):
    """Award a badge to a user."""
    from traces.models import UserBadge

    _, created = UserBadge.objects.get_or_create(
        user=user,
        badge_id=badge_id,
    )

    if created:
        from notifs.helpers import notify
        from notifs.models import Notification

        notify(
            user,
            Notification.BADGE_AWARDED,
            f"Challenge '{challenge.title}': badge earned!",
            f"/challenges/{challenge.pk}/",
        )
        logger.info("Badge %s awarded to user %s for challenge %d", badge_id, user.username, challenge.pk)


def _award_subscription(user, reward_type, challenge):
    """Create a subscription for a user."""
    from traces.models import Subscription

    duration = _DURATION_MAP[reward_type]
    today = datetime.date.today()

    latest_sub = (
        Subscription.objects.filter(user=user).order_by("-end_date").first()
    )
    if latest_sub:
        start = max(latest_sub.end_date + datetime.timedelta(days=1), today)
    else:
        start = today

    Subscription.objects.create(
        user=user,
        start_date=start,
        end_date=start + duration,
    )

    from notifs.helpers import notify
    from notifs.models import Notification

    notify(
        user,
        Notification.BADGE_AWARDED,
        f"Challenge '{challenge.title}': subscription reward!",
        f"/challenges/{challenge.pk}/",
    )
    logger.info(
        "Subscription %s awarded to user %s for challenge %d",
        reward_type, user.username, challenge.pk,
    )
