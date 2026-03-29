from django.test import TestCase
from django.urls import reverse

from ._helpers import make_user


class BadgesViewTest(TestCase):

    def test_anonymous_returns_200(self):
        resp = self.client.get(reverse("badges"))
        self.assertEqual(resp.status_code, 200)

    def test_authenticated_returns_200(self):
        user = make_user()
        self.client.force_login(user)
        resp = self.client.get(reverse("badges"))
        self.assertEqual(resp.status_code, 200)

    def test_context_has_catalogue(self):
        resp = self.client.get(reverse("badges"))
        self.assertIn("catalogue", resp.context)
        self.assertIn("total", resp.context)
        self.assertIn("earned_count", resp.context)


class StatsBadgesViewTest(TestCase):

    def test_returns_200(self):
        resp = self.client.get(reverse("stats_badges"))
        self.assertEqual(resp.status_code, 200)

    def test_context_keys(self):
        resp = self.client.get(reverse("stats_badges"))
        for key in ("total_badges", "avg_badges", "rarest",
                     "most_common", "badge_leaderboard", "recent_activity"):
            self.assertIn(key, resp.context)

    def test_with_badge_data(self):
        from traces.models import UserBadge
        user = make_user()
        UserBadge.objects.create(user=user, badge_id="territoire_premier")
        resp = self.client.get(reverse("stats_badges"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["total_badges"], 1)
