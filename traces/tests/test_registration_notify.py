from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from traces.tasks_notifications import notify_new_registration


class NotifyNewRegistrationTaskTest(TestCase):
    """Tests for the notify_new_registration Procrastinate task."""

    @override_settings(REGISTRATION_NOTIFY_EMAIL="admin@biketory.fr")
    def test_sends_email_to_configured_address(self):
        # The task sends a notification email to the configured admin address
        notify_new_registration(user_id=42, username="alice", email="alice@test.local")

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("admin@biketory.fr", mail.outbox[0].to)

    @override_settings(REGISTRATION_NOTIFY_EMAIL="admin@biketory.fr")
    def test_email_contains_username_and_email(self):
        # The email body includes the new user's username and email
        notify_new_registration(user_id=42, username="alice", email="alice@test.local")

        body = mail.outbox[0].body
        self.assertIn("alice", body)
        self.assertIn("alice@test.local", body)

    @override_settings(REGISTRATION_NOTIFY_EMAIL="admin@biketory.fr")
    def test_email_contains_admin_link(self):
        # The email body includes a link to the Django admin user page
        notify_new_registration(user_id=42, username="alice", email="alice@test.local")

        self.assertIn("/admin/auth/user/42/change/", mail.outbox[0].body)

    @override_settings(REGISTRATION_NOTIFY_EMAIL="admin@biketory.fr")
    def test_subject_contains_username(self):
        # The subject line includes the new user's username for quick identification
        notify_new_registration(user_id=42, username="alice", email="alice@test.local")

        self.assertIn("alice", mail.outbox[0].subject)

    @override_settings(REGISTRATION_NOTIFY_EMAIL="")
    def test_skips_when_email_not_configured(self):
        # When REGISTRATION_NOTIFY_EMAIL is empty, no email is sent
        notify_new_registration(user_id=42, username="alice", email="alice@test.local")

        self.assertEqual(len(mail.outbox), 0)


class RegisterViewNotifyTest(TestCase):
    """Tests for the registration view dispatching the notification task."""

    @override_settings(
        REGISTRATION_CLOSED=False,
        REGISTRATION_NOTIFY_ENABLED=True,
    )
    @patch("traces.tasks_notifications.notify_new_registration")
    def test_registration_defers_notification(self, mock_task):
        # When REGISTRATION_NOTIFY_ENABLED=True, the task is deferred after signup
        resp = self.client.post(reverse("register"), {
            "email": "new@test.local",
            "password1": "Str0ngP@ss!",
            "password2": "Str0ngP@ss!",
        })
        self.assertEqual(resp.status_code, 302)
        mock_task.defer.assert_called_once()

        # Verify the deferred kwargs contain the new user's info
        call_kwargs = mock_task.defer.call_args[1]
        self.assertIn("username", call_kwargs)
        self.assertEqual(call_kwargs["email"], "new@test.local")

    @override_settings(
        REGISTRATION_CLOSED=False,
        REGISTRATION_NOTIFY_ENABLED=False,
    )
    @patch("traces.tasks_notifications.notify_new_registration")
    def test_registration_does_not_notify_when_disabled(self, mock_task):
        # When REGISTRATION_NOTIFY_ENABLED=False, no task is deferred
        resp = self.client.post(reverse("register"), {
            "email": "other@test.local",
            "password1": "Str0ngP@ss!",
            "password2": "Str0ngP@ss!",
        })
        self.assertEqual(resp.status_code, 302)
        mock_task.defer.assert_not_called()

    @override_settings(
        REGISTRATION_CLOSED=True,
    )
    @patch("traces.tasks_notifications.notify_new_registration")
    def test_closed_registration_does_not_notify(self, mock_task):
        # When registration is closed (no referral), signup is rejected, no task
        resp = self.client.post(reverse("register"), {
            "email": "blocked@test.local",
            "password1": "Str0ngP@ss!",
            "password2": "Str0ngP@ss!",
        })
        # Registration closed → renders form again (200)
        self.assertEqual(resp.status_code, 200)
        mock_task.defer.assert_not_called()
