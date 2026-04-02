import datetime

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from notifs.models import Notification
from referrals.models import Referral
from referrals.tests._helpers import make_user
from traces.models import Subscription, Trace


class ReferralListViewTest(TestCase):

    def setUp(self):
        self.sponsor = make_user("sponsor")
        self.client.force_login(self.sponsor)
        self.url = reverse("referral_list")

    def test_auth_required(self):
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_get_displays_form(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'type="email"')

    def test_get_displays_referrals(self):
        Referral.objects.create(sponsor=self.sponsor, email="a@test.local")
        resp = self.client.get(self.url)
        self.assertContains(resp, "a@test.local")

    def test_post_creates_referral_and_sends_email(self):
        resp = self.client.post(self.url, {"email": "new@example.com"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Referral.objects.filter(
            sponsor=self.sponsor, email="new@example.com"
        ).exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("new@example.com", mail.outbox[0].to)
        self.assertIn("ref=", mail.outbox[0].body)

    def test_post_own_email_rejected(self):
        resp = self.client.post(self.url, {"email": self.sponsor.email})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Referral.objects.filter(sponsor=self.sponsor).exists())

    def test_post_existing_user_email_rejected(self):
        existing = make_user("existing", email="existing@test.local")
        resp = self.client.post(self.url, {"email": existing.email})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Referral.objects.filter(sponsor=self.sponsor).exists())

    def test_post_duplicate_email_rejected(self):
        Referral.objects.create(sponsor=self.sponsor, email="dup@test.local")
        resp = self.client.post(self.url, {"email": "dup@test.local"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            Referral.objects.filter(sponsor=self.sponsor, email="dup@test.local").count(),
            1,
        )

    def test_limit_5_invitations(self):
        for i in range(5):
            Referral.objects.create(sponsor=self.sponsor, email=f"r{i}@test.local")
        resp = self.client.post(self.url, {"email": "six@test.local"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(
            Referral.objects.filter(email="six@test.local").exists()
        )


class ReferralDeleteViewTest(TestCase):

    def setUp(self):
        self.sponsor = make_user("sponsor")
        self.client.force_login(self.sponsor)

    def test_delete_pending_referral(self):
        ref = Referral.objects.create(sponsor=self.sponsor, email="a@test.local")
        url = reverse("referral_delete", args=[ref.pk])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Referral.objects.filter(pk=ref.pk).exists())

    def test_cannot_delete_accepted_referral(self):
        ref = Referral.objects.create(
            sponsor=self.sponsor, email="a@test.local", status=Referral.ACCEPTED
        )
        url = reverse("referral_delete", args=[ref.pk])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Referral.objects.filter(pk=ref.pk).exists())

    def test_cannot_delete_other_users_referral(self):
        other = make_user("other")
        ref = Referral.objects.create(sponsor=other, email="a@test.local")
        url = reverse("referral_delete", args=[ref.pk])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Referral.objects.filter(pk=ref.pk).exists())

    def test_get_does_not_delete(self):
        ref = Referral.objects.create(sponsor=self.sponsor, email="a@test.local")
        url = reverse("referral_delete", args=[ref.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Referral.objects.filter(pk=ref.pk).exists())

    def test_auth_required(self):
        ref = Referral.objects.create(sponsor=self.sponsor, email="a@test.local")
        self.client.logout()
        url = reverse("referral_delete", args=[ref.pk])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Referral.objects.filter(pk=ref.pk).exists())


class RegisterWithRefTokenTest(TestCase):

    def setUp(self):
        self.sponsor = make_user("sponsor")
        self.referral = Referral.objects.create(
            sponsor=self.sponsor, email="new@test.local"
        )

    def test_register_with_valid_ref_accepts_referral(self):
        url = reverse("register") + f"?ref={self.referral.token}"
        resp = self.client.post(url, {
            "email": "new@test.local",
            "password1": "Str0ngP@ss!",
            "password2": "Str0ngP@ss!",
        })
        self.assertEqual(resp.status_code, 302)

        self.referral.refresh_from_db()
        self.assertEqual(self.referral.status, Referral.ACCEPTED)
        self.assertIsNotNone(self.referral.referee)
        self.assertIsNotNone(self.referral.accepted_at)

    def test_register_with_valid_ref_sends_notification(self):
        url = reverse("register") + f"?ref={self.referral.token}"
        self.client.post(url, {
            "email": "new@test.local",
            "password1": "Str0ngP@ss!",
            "password2": "Str0ngP@ss!",
        })
        self.assertTrue(
            Notification.objects.filter(
                user=self.sponsor,
                notification_type=Notification.REFERRAL_SIGNUP,
            ).exists()
        )

    def test_register_with_invalid_ref_works_normally(self):
        url = reverse("register") + "?ref=invalid_token"
        resp = self.client.post(url, {
            "email": "other@test.local",
            "password1": "Str0ngP@ss!",
            "password2": "Str0ngP@ss!",
        })
        self.assertEqual(resp.status_code, 302)
        self.referral.refresh_from_db()
        self.assertEqual(self.referral.status, Referral.PENDING)

    def test_register_with_ref_in_post_body(self):
        """Token passed via hidden field (real browser behavior)."""
        url = reverse("register")
        resp = self.client.post(url, {
            "ref": self.referral.token,
            "email": "new@test.local",
            "password1": "Str0ngP@ss!",
            "password2": "Str0ngP@ss!",
        })
        self.assertEqual(resp.status_code, 302)

        self.referral.refresh_from_db()
        self.assertEqual(self.referral.status, Referral.ACCEPTED)
        self.assertIsNotNone(self.referral.referee)

    def test_register_get_prefills_email(self):
        url = reverse("register") + f"?ref={self.referral.token}"
        resp = self.client.get(url)
        self.assertContains(resp, "new@test.local")

    def test_register_get_contains_hidden_ref(self):
        url = reverse("register") + f"?ref={self.referral.token}"
        resp = self.client.get(url)
        self.assertContains(resp, f'value="{self.referral.token}"')


class FirstTraceRewardTest(TestCase):

    def setUp(self):
        self.sponsor = make_user("sponsor")
        self.referee = make_user("referee", email="referee@test.local")
        self.referral = Referral.objects.create(
            sponsor=self.sponsor,
            email="referee@test.local",
            status=Referral.ACCEPTED,
            referee=self.referee,
            accepted_at=timezone.now(),
        )

    def test_first_trace_rewards_sponsor(self):
        Trace.objects.create(uploaded_by=self.referee)

        from traces.views.upload import _reward_referral_sponsor
        _reward_referral_sponsor(self.referee)

        self.referral.refresh_from_db()
        self.assertTrue(self.referral.rewarded)
        self.assertTrue(Subscription.objects.filter(user=self.sponsor).exists())
        sub = Subscription.objects.get(user=self.sponsor)
        expected_end = datetime.date.today() + datetime.timedelta(days=30)
        self.assertGreaterEqual(sub.end_date, expected_end - datetime.timedelta(days=2))

    def test_second_trace_no_double_reward(self):
        Trace.objects.create(uploaded_by=self.referee)
        Trace.objects.create(uploaded_by=self.referee)

        from traces.views.upload import _reward_referral_sponsor
        _reward_referral_sponsor(self.referee)

        self.referral.refresh_from_db()
        self.assertFalse(self.referral.rewarded)

    def test_existing_subscription_creates_new_one_after(self):
        today = datetime.date.today()
        existing = Subscription.objects.create(
            user=self.sponsor,
            start_date=today - datetime.timedelta(days=10),
            end_date=today + datetime.timedelta(days=20),
        )
        Trace.objects.create(uploaded_by=self.referee)

        from traces.views.upload import _reward_referral_sponsor
        _reward_referral_sponsor(self.referee)

        self.assertEqual(Subscription.objects.filter(user=self.sponsor).count(), 2)
        new_sub = Subscription.objects.filter(user=self.sponsor).exclude(pk=existing.pk).get()
        self.assertEqual(new_sub.start_date, existing.end_date + datetime.timedelta(days=1))
