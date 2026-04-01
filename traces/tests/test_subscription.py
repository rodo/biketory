import datetime

from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from traces.decorators import premium_required
from traces.models import Subscription, UserProfile

from ._helpers import make_user


def _today():
    return timezone.now().date()


class SubscriptionIsActiveTest(TestCase):

    def setUp(self):
        self.user = make_user()

    def test_subscription_is_active_within_dates(self):
        sub = Subscription(
            user=self.user,
            start_date=_today() - datetime.timedelta(days=1),
            end_date=_today() + datetime.timedelta(days=1),
        )
        self.assertTrue(sub.is_active())

    def test_subscription_is_inactive_after_end_date(self):
        sub = Subscription(
            user=self.user,
            start_date=_today() - datetime.timedelta(days=10),
            end_date=_today() - datetime.timedelta(days=1),
        )
        self.assertFalse(sub.is_active())

    def test_subscription_is_inactive_before_start_date(self):
        sub = Subscription(
            user=self.user,
            start_date=_today() + datetime.timedelta(days=1),
            end_date=_today() + datetime.timedelta(days=10),
        )
        self.assertFalse(sub.is_active())


class IsPremiumFlagTest(TestCase):

    def setUp(self):
        self.user = make_user()

    def test_is_premium_false_by_default(self):
        profile = UserProfile.objects.get(user=self.user)
        self.assertFalse(profile.is_premium)

    def test_is_premium_set_true_on_active_subscription_save(self):
        Subscription.objects.create(
            user=self.user,
            start_date=_today() - datetime.timedelta(days=1),
            end_date=_today() + datetime.timedelta(days=30),
        )
        profile = UserProfile.objects.get(user=self.user)
        self.assertTrue(profile.is_premium)

    def test_is_premium_not_set_on_expired_subscription_save(self):
        Subscription.objects.create(
            user=self.user,
            start_date=_today() - datetime.timedelta(days=30),
            end_date=_today() - datetime.timedelta(days=1),
        )
        profile = UserProfile.objects.get(user=self.user)
        self.assertFalse(profile.is_premium)

    def test_multiple_subscriptions_allowed(self):
        Subscription.objects.create(
            user=self.user,
            start_date=_today() - datetime.timedelta(days=60),
            end_date=_today() - datetime.timedelta(days=31),
        )
        Subscription.objects.create(
            user=self.user,
            start_date=_today() - datetime.timedelta(days=1),
            end_date=_today() + datetime.timedelta(days=30),
        )
        self.assertEqual(Subscription.objects.filter(user=self.user).count(), 2)


class ExpirePremiumCommandTest(TestCase):

    def setUp(self):
        self.user = make_user()

    def test_expire_sets_false_when_no_active_subscription(self):
        profile = UserProfile.objects.get(user=self.user)
        profile.is_premium = True
        profile.save(update_fields=["is_premium"])

        Subscription.objects.create(
            user=self.user,
            start_date=_today() - datetime.timedelta(days=30),
            end_date=_today() - datetime.timedelta(days=1),
        )
        call_command("expire_premium")
        profile.refresh_from_db()
        self.assertFalse(profile.is_premium)

    def test_expire_keeps_true_when_active_subscription(self):
        Subscription.objects.create(
            user=self.user,
            start_date=_today() - datetime.timedelta(days=1),
            end_date=_today() + datetime.timedelta(days=30),
        )
        profile = UserProfile.objects.get(user=self.user)
        self.assertTrue(profile.is_premium)

        call_command("expire_premium")
        profile.refresh_from_db()
        self.assertTrue(profile.is_premium)


class PremiumRequiredDecoratorTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = make_user()

    def _dummy_view(self, request):
        from django.http import HttpResponse
        return HttpResponse("ok")

    def test_premium_required_redirects_anonymous(self):
        view = premium_required(self._dummy_view)
        request = self.factory.get("/fake/")
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])

    def test_premium_required_redirects_non_premium(self):
        view = premium_required(self._dummy_view)
        request = self.factory.get("/fake/")
        request.user = self.user
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("premium", response["Location"])

    def test_premium_required_allows_premium_user(self):
        profile = UserProfile.objects.get(user=self.user)
        profile.is_premium = True
        profile.save(update_fields=["is_premium"])

        view = premium_required(self._dummy_view)
        request = self.factory.get("/fake/")
        request.user = self.user
        response = view(request)
        self.assertEqual(response.status_code, 200)


class SubscriptionHistoryViewTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse("subscription_history"))
        self.assertEqual(resp.status_code, 302)

    def test_empty_history(self):
        resp = self.client.get(reverse("subscription_history"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["subscriptions"]), 0)

    def test_shows_subscriptions(self):
        Subscription.objects.create(
            user=self.user,
            start_date=_today() - datetime.timedelta(days=60),
            end_date=_today() - datetime.timedelta(days=31),
        )
        Subscription.objects.create(
            user=self.user,
            start_date=_today() - datetime.timedelta(days=1),
            end_date=_today() + datetime.timedelta(days=30),
        )
        resp = self.client.get(reverse("subscription_history"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["subscriptions"]), 2)


class SubscriptionRequiredViewTest(TestCase):

    def test_subscription_required_view_returns_200(self):
        resp = self.client.get(reverse("subscription_required"))
        self.assertEqual(resp.status_code, 200)
