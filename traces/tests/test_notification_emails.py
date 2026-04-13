from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from notifs.helpers import notify, notify_bulk
from traces.models import UserProfile

from ._helpers import make_user


class NotifyEmailPreferenceTest(TestCase):
    """Tests that notify() defers an email only when the preference is active."""

    def setUp(self):
        self.user = make_user()

    @patch("notifs.helpers.send_notification_email")
    def test_notify_defers_email_when_preference_active(self, mock_task):
        # Default preferences are True, so an email should be deferred
        notify(self.user, "badge_awarded", "You earned a badge!", "/badges/")

        mock_task.defer.assert_called_once_with(
            user_id=self.user.pk, message="You earned a badge!", link="/badges/",
        )

    @patch("notifs.helpers.send_notification_email")
    def test_notify_does_not_defer_email_when_preference_disabled(self, mock_task):
        # Disable the badge email preference
        UserProfile.objects.filter(user=self.user).update(email_on_badge=False)
        self.user.profile.refresh_from_db()

        notify(self.user, "badge_awarded", "You earned a badge!", "/badges/")

        mock_task.defer.assert_not_called()

    @patch("notifs.helpers.send_notification_email")
    def test_notify_friend_request_uses_friend_preference(self, mock_task):
        # friend_request and friend_accepted both use email_on_friend
        UserProfile.objects.filter(user=self.user).update(email_on_friend=False)
        self.user.profile.refresh_from_db()

        notify(self.user, "friend_request", "Bob sent you a request", "/friends/")

        mock_task.defer.assert_not_called()

    @patch("notifs.helpers.send_notification_email")
    def test_notify_unknown_type_does_not_send_email(self, mock_task):
        # An unknown notification type should not trigger an email
        notify(self.user, "unknown_type", "Something happened")

        mock_task.defer.assert_not_called()


class NotifyBulkEmailPreferenceTest(TestCase):
    """Tests that notify_bulk() respects email preferences."""

    def setUp(self):
        self.user = make_user()

    @patch("notifs.helpers.send_notification_email")
    def test_bulk_defers_emails_when_preference_active(self, mock_task):
        # Default preferences are True, so emails should be deferred for each item
        items = [
            ("Badge 1", "/badges/1/"),
            ("Badge 2", "/badges/2/"),
        ]
        notify_bulk(self.user, "badge_awarded", items)

        self.assertEqual(mock_task.defer.call_count, 2)

    @patch("notifs.helpers.send_notification_email")
    def test_bulk_does_not_defer_when_preference_disabled(self, mock_task):
        # Disable the badge email preference
        UserProfile.objects.filter(user=self.user).update(email_on_badge=False)
        self.user.profile.refresh_from_db()

        items = [("Badge 1", "/badges/1/"), ("Badge 2", "/badges/2/")]
        notify_bulk(self.user, "badge_awarded", items)

        mock_task.defer.assert_not_called()


class SettingsEmailPreferencesViewTest(TestCase):
    """Tests that the settings view updates email preferences."""

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_update_email_preferences_all_on(self):
        # Submit all checkboxes checked
        resp = self.client.post(reverse("settings"), {
            "action": "update_email_preferences",
            "email_on_badge": "on",
            "email_on_friend": "on",
            "email_on_trace_analyzed": "on",
            "email_on_referral": "on",
            "email_on_challenge": "on",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["success_field"], "email_preferences")
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.email_on_badge)
        self.assertTrue(self.user.profile.email_on_friend)
        self.assertTrue(self.user.profile.email_on_trace_analyzed)
        self.assertTrue(self.user.profile.email_on_referral)
        self.assertTrue(self.user.profile.email_on_challenge)

    def test_update_email_preferences_all_off(self):
        # Submit with no checkboxes → all False
        resp = self.client.post(reverse("settings"), {
            "action": "update_email_preferences",
        })
        self.assertEqual(resp.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.email_on_badge)
        self.assertFalse(self.user.profile.email_on_friend)
        self.assertFalse(self.user.profile.email_on_trace_analyzed)
        self.assertFalse(self.user.profile.email_on_referral)
        self.assertFalse(self.user.profile.email_on_challenge)

    def test_update_partial_preferences(self):
        # Only badge and trace_analyzed checked
        self.client.post(reverse("settings"), {
            "action": "update_email_preferences",
            "email_on_badge": "on",
            "email_on_trace_analyzed": "on",
        })
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.email_on_badge)
        self.assertFalse(self.user.profile.email_on_friend)
        self.assertTrue(self.user.profile.email_on_trace_analyzed)
        self.assertFalse(self.user.profile.email_on_referral)
        self.assertFalse(self.user.profile.email_on_challenge)

    def test_preferences_shown_in_context(self):
        # Default preferences (all True) should appear in the context
        resp = self.client.get(reverse("settings"))
        self.assertTrue(resp.context["email_on_badge"])
        self.assertTrue(resp.context["email_on_friend"])
        self.assertTrue(resp.context["email_on_trace_analyzed"])
        self.assertTrue(resp.context["email_on_referral"])
        self.assertTrue(resp.context["email_on_challenge"])
