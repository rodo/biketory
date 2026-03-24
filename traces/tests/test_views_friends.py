from django.test import TestCase
from django.urls import reverse

from traces.models import Friendship

from ._helpers import make_user


class FriendsViewGetTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.login(username="alice", password="pass")

    def test_get_returns_200(self):
        resp = self.client.get(reverse("friends"))
        self.assertEqual(resp.status_code, 200)

    def test_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse("friends"))
        self.assertEqual(resp.status_code, 302)


class FriendsSendTest(TestCase):

    def setUp(self):
        self.alice = make_user("alice")
        self.bob = make_user("bob")
        self.client.login(username="alice", password="pass")

    def test_send_creates_pending_friendship(self):
        self.client.post(reverse("friends"), {
            "action": "send",
            "to_user_id": self.bob.pk,
        })
        f = Friendship.objects.get(from_user=self.alice, to_user=self.bob)
        self.assertEqual(f.status, Friendship.STATUS_PENDING)

    def test_send_to_self_does_nothing(self):
        self.client.post(reverse("friends"), {
            "action": "send",
            "to_user_id": self.alice.pk,
        })
        self.assertEqual(Friendship.objects.count(), 0)


class FriendsAcceptDeclineTest(TestCase):

    def setUp(self):
        self.alice = make_user("alice")
        self.bob = make_user("bob")
        self.friendship = Friendship.objects.create(
            from_user=self.bob, to_user=self.alice,
        )

    def test_accept(self):
        self.client.login(username="alice", password="pass")
        self.client.post(reverse("friends"), {
            "action": "accept",
            "friendship_id": self.friendship.pk,
        })
        self.friendship.refresh_from_db()
        self.assertEqual(self.friendship.status, Friendship.STATUS_ACCEPTED)

    def test_decline_deletes(self):
        self.client.login(username="alice", password="pass")
        self.client.post(reverse("friends"), {
            "action": "decline",
            "friendship_id": self.friendship.pk,
        })
        self.assertFalse(Friendship.objects.filter(pk=self.friendship.pk).exists())


class FriendsCancelRemoveTest(TestCase):

    def setUp(self):
        self.alice = make_user("alice")
        self.bob = make_user("bob")

    def test_cancel_sent_request(self):
        f = Friendship.objects.create(from_user=self.alice, to_user=self.bob)
        self.client.login(username="alice", password="pass")
        self.client.post(reverse("friends"), {
            "action": "cancel",
            "friendship_id": f.pk,
        })
        self.assertFalse(Friendship.objects.filter(pk=f.pk).exists())

    def test_remove_accepted_friend(self):
        f = Friendship.objects.create(
            from_user=self.alice, to_user=self.bob,
            status=Friendship.STATUS_ACCEPTED,
        )
        self.client.login(username="alice", password="pass")
        self.client.post(reverse("friends"), {
            "action": "remove",
            "friendship_id": f.pk,
        })
        self.assertFalse(Friendship.objects.filter(pk=f.pk).exists())


class FriendsSearchTest(TestCase):

    def setUp(self):
        self.alice = make_user("alice")
        self.bob = make_user("bob")
        self.client.login(username="alice", password="pass")

    def test_search_by_username(self):
        resp = self.client.post(reverse("friends"), {
            "action": "search",
            "q": "bob",
        })
        self.assertEqual(resp.status_code, 200)
        results = resp.context["search_results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["user"], self.bob)
        self.assertEqual(results[0]["rel"], "none")

    def test_search_by_uuid(self):
        from traces.models import UserSurfaceStats
        stats, _ = UserSurfaceStats.objects.get_or_create(user=self.bob)
        resp = self.client.post(reverse("friends"), {
            "action": "search",
            "q": str(stats.secret_uuid),
        })
        self.assertEqual(resp.status_code, 200)
        results = resp.context["search_results"]
        self.assertEqual(len(results), 1)

    def test_search_empty_query_returns_no_results(self):
        resp = self.client.post(reverse("friends"), {
            "action": "search",
            "q": "",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context["search_results"])
