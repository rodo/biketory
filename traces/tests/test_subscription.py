import datetime

from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from traces.decorators import premium_required
from traces.models import Subscription

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

    def test_premium_required_allows_active_subscriber(self):
        Subscription.objects.create(
            user=self.user,
            start_date=_today() - datetime.timedelta(days=1),
            end_date=_today() + datetime.timedelta(days=30),
        )
        view = premium_required(self._dummy_view)
        request = self.factory.get("/fake/")
        request.user = self.user
        response = view(request)
        self.assertEqual(response.status_code, 200)


class SubscriptionRequiredViewTest(TestCase):

    def test_subscription_required_view_returns_200(self):
        resp = self.client.get(reverse("subscription_required"))
        self.assertEqual(resp.status_code, 200)
