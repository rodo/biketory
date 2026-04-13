from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from challenges.models import (
    Challenge,
    ChallengeLeaderboardEntry,
    ChallengeReward,
)
from challenges.rewards import award_challenge_rewards
from notifs.models import Notification

user_model = get_user_model()


class AwardChallengeRewardsNotificationTest(TestCase):
    """Tests that award_challenge_rewards sends challenge_won notifications."""

    def setUp(self):
        self.admin = user_model.objects.create_user(
            username="admin", password="test1234", email="admin@test.com"
        )
        self.winner = user_model.objects.create_user(
            username="winner", password="test1234", email="winner@test.com"
        )
        now = timezone.now()
        self.challenge = Challenge.objects.create(
            title="Spring Challenge",
            challenge_type=Challenge.TYPE_MAX_POINTS,
            start_date=now - timedelta(days=7),
            end_date=now - timedelta(days=1),
            created_by=self.admin,
        )
        ChallengeReward.objects.create(
            challenge=self.challenge,
            rank_threshold=3,
            reward_type=ChallengeReward.REWARD_BADGE,
            badge_id="spring_badge",
        )
        ChallengeLeaderboardEntry.objects.create(
            challenge=self.challenge,
            user_id=self.winner.pk,
            username=self.winner.username,
            score=100,
            goal_met=True,
            rank=1,
            computed_at=now,
        )

    def test_challenge_won_notification_created(self):
        # A challenge_won notification should be created for the winner
        award_challenge_rewards(self.challenge)

        notif = Notification.objects.filter(
            user=self.winner,
            notification_type=Notification.CHALLENGE_WON,
        )
        self.assertEqual(notif.count(), 1)
        self.assertIn("Spring Challenge", notif.first().message)
        self.assertIn("#1", notif.first().message)

    def test_challenge_won_notification_sent_once_per_user(self):
        # Even with multiple rewards, only one challenge_won notification per user
        ChallengeReward.objects.create(
            challenge=self.challenge,
            rank_threshold=3,
            reward_type=ChallengeReward.REWARD_SUB_3M,
        )

        award_challenge_rewards(self.challenge)

        count = Notification.objects.filter(
            user=self.winner,
            notification_type=Notification.CHALLENGE_WON,
        ).count()
        self.assertEqual(count, 1)

    @patch("notifs.helpers.send_notification_email")
    def test_challenge_won_defers_email_when_preference_active(self, mock_task):
        # Default email_on_challenge is True, so an email should be deferred
        award_challenge_rewards(self.challenge)

        # Find the challenge_won defer call (there may also be badge_awarded calls)
        challenge_calls = [
            c for c in mock_task.defer.call_args_list
            if "you finished #1" in c.kwargs.get("message", "")
        ]
        self.assertEqual(len(challenge_calls), 1)

    @patch("notifs.helpers.send_notification_email")
    def test_challenge_won_no_email_when_preference_disabled(self, mock_task):
        # Disable the challenge email preference
        from traces.models import UserProfile
        UserProfile.objects.filter(user=self.winner).update(email_on_challenge=False)
        self.winner.profile.refresh_from_db()

        award_challenge_rewards(self.challenge)

        # The challenge_won defer should not be in the calls
        challenge_calls = [
            c for c in mock_task.defer.call_args_list
            if "you finished #1" in c.kwargs.get("message", "")
        ]
        self.assertEqual(len(challenge_calls), 0)

    def test_no_notification_when_goal_not_met(self):
        # If goal_met is False, no challenge_won notification
        ChallengeLeaderboardEntry.objects.filter(
            challenge=self.challenge, user_id=self.winner.pk,
        ).update(goal_met=False)

        award_challenge_rewards(self.challenge)

        count = Notification.objects.filter(
            user=self.winner,
            notification_type=Notification.CHALLENGE_WON,
        ).count()
        self.assertEqual(count, 0)
