from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from challenges.models import Challenge, ChallengeParticipant
from traces.models import UserProfile

user_model = get_user_model()


class ChallengeListViewTest(TestCase):
    def setUp(self):
        self.user = user_model.objects.create_user(
            username="player", password="test1234", email="player@test.com"
        )
        UserProfile.objects.get_or_create(user=self.user)
        self.admin = user_model.objects.create_user(
            username="admin", password="test1234", email="admin@test.com"
        )
        self.now = timezone.now()
        self.active_challenge = Challenge.objects.create(
            title="Active Challenge",
            challenge_type=Challenge.TYPE_CAPTURE_HEXAGON,
            start_date=self.now - timedelta(days=1),
            end_date=self.now + timedelta(days=6),
            created_by=self.admin,
        )

    def test_requires_login(self):
        response = self.client.get("/challenges/")
        assert response.status_code == 302

    def test_list_shows_active(self):
        self.client.force_login(self.user)
        response = self.client.get("/challenges/")
        assert response.status_code == 200
        assert "Active Challenge" in response.content.decode()


class ChallengeDetailViewTest(TestCase):
    def setUp(self):
        self.user = user_model.objects.create_user(
            username="player", password="test1234", email="player@test.com"
        )
        UserProfile.objects.get_or_create(user=self.user)
        self.admin = user_model.objects.create_user(
            username="admin", password="test1234", email="admin@test.com"
        )
        self.now = timezone.now()
        self.challenge = Challenge.objects.create(
            title="Detail Challenge",
            challenge_type=Challenge.TYPE_CAPTURE_HEXAGON,
            start_date=self.now - timedelta(days=1),
            end_date=self.now + timedelta(days=6),
            created_by=self.admin,
        )

    def test_requires_login(self):
        response = self.client.get(f"/challenges/{self.challenge.pk}/")
        assert response.status_code == 302

    def test_detail_page(self):
        self.client.force_login(self.user)
        response = self.client.get(f"/challenges/{self.challenge.pk}/")
        assert response.status_code == 200
        assert "Detail Challenge" in response.content.decode()

    def test_ajax_returns_json(self):
        self.client.force_login(self.user)
        response = self.client.get(
            f"/challenges/{self.challenge.pk}/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data


class JoinChallengeViewTest(TestCase):
    def setUp(self):
        self.user = user_model.objects.create_user(
            username="player", password="test1234", email="player@test.com"
        )
        UserProfile.objects.get_or_create(user=self.user)
        self.admin = user_model.objects.create_user(
            username="admin", password="test1234", email="admin@test.com"
        )
        self.now = timezone.now()
        self.challenge = Challenge.objects.create(
            title="Join Challenge",
            challenge_type=Challenge.TYPE_CAPTURE_HEXAGON,
            start_date=self.now - timedelta(days=1),
            end_date=self.now + timedelta(days=6),
            created_by=self.admin,
        )

    def test_join_requires_post(self):
        self.client.force_login(self.user)
        response = self.client.get(f"/challenges/{self.challenge.pk}/join/")
        assert response.status_code == 405

    def test_join(self):
        self.client.force_login(self.user)
        response = self.client.post(f"/challenges/{self.challenge.pk}/join/")
        assert response.status_code == 302
        assert ChallengeParticipant.objects.filter(
            challenge=self.challenge, user=self.user
        ).exists()

    def test_join_idempotent(self):
        self.client.force_login(self.user)
        self.client.post(f"/challenges/{self.challenge.pk}/join/")
        self.client.post(f"/challenges/{self.challenge.pk}/join/")
        assert ChallengeParticipant.objects.filter(
            challenge=self.challenge, user=self.user
        ).count() == 1

    def test_cannot_join_ended(self):
        self.challenge.end_date = self.now - timedelta(hours=1)
        self.challenge.save()
        self.client.force_login(self.user)
        response = self.client.post(f"/challenges/{self.challenge.pk}/join/")
        assert response.status_code == 302
        assert not ChallengeParticipant.objects.filter(
            challenge=self.challenge, user=self.user
        ).exists()

    def test_premium_only_rejects_non_premium(self):
        self.challenge.premium_only = True
        self.challenge.save()
        self.client.force_login(self.user)
        response = self.client.post(f"/challenges/{self.challenge.pk}/join/")
        assert response.status_code == 302
        assert not ChallengeParticipant.objects.filter(
            challenge=self.challenge, user=self.user
        ).exists()

    def test_premium_only_accepts_premium(self):
        self.challenge.premium_only = True
        self.challenge.save()
        profile = self.user.profile
        profile.is_premium = True
        profile.save()
        self.client.force_login(self.user)
        response = self.client.post(f"/challenges/{self.challenge.pk}/join/")
        assert response.status_code == 302
        assert ChallengeParticipant.objects.filter(
            challenge=self.challenge, user=self.user
        ).exists()


class AdminChallengesViewTest(TestCase):
    def setUp(self):
        self.admin = user_model.objects.create_superuser(
            username="superadmin", password="test1234", email="super@test.com"
        )
        self.user = user_model.objects.create_user(
            username="player", password="test1234", email="player@test.com"
        )

    def test_requires_staff(self):
        self.client.force_login(self.user)
        response = self.client.get("/admin-dashboard/challenges/")
        assert response.status_code == 302

    def test_admin_list(self):
        self.client.force_login(self.admin)
        response = self.client.get("/admin-dashboard/challenges/")
        assert response.status_code == 200
