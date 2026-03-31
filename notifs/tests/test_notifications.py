from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from notifs.context_processors import notifications as notif_ctx
from notifs.helpers import notify, notify_bulk
from notifs.models import Notification

user_model = get_user_model()


class NotifyHelperTest(TestCase):
    def setUp(self):
        self.user = user_model.objects.create_user(
            username="alice", password="testpass123"
        )

    def test_notify_creates_notification(self):
        n = notify(self.user, Notification.BADGE_AWARDED, "You earned X!", "/badges/")
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(n.notification_type, Notification.BADGE_AWARDED)
        self.assertEqual(n.link, "/badges/")
        self.assertFalse(n.is_read)

    def test_notify_bulk_creates_multiple(self):
        items = [
            ("Badge A", "/badges/"),
            ("Badge B", "/badges/"),
            ("Badge C", "/badges/"),
        ]
        notify_bulk(self.user, Notification.BADGE_AWARDED, items)
        self.assertEqual(Notification.objects.count(), 3)


class ContextProcessorTest(TestCase):
    def setUp(self):
        self.user = user_model.objects.create_user(
            username="bob", password="testpass123"
        )
        self.factory = RequestFactory()

    def test_unread_count_context_processor(self):
        notify(self.user, Notification.TRACE_ANALYZED, "Trace done", "/traces/1/")
        notify(self.user, Notification.TRACE_ANALYZED, "Trace done 2", "/traces/2/")

        request = self.factory.get("/")
        request.user = self.user
        ctx = notif_ctx(request)
        self.assertEqual(ctx["unread_notifications_count"], 2)

    def test_unread_count_anonymous(self):
        from django.contrib.auth.models import AnonymousUser

        request = self.factory.get("/")
        request.user = AnonymousUser()
        ctx = notif_ctx(request)
        self.assertEqual(ctx["unread_notifications_count"], 0)


class NotificationsViewTest(TestCase):
    def setUp(self):
        self.user = user_model.objects.create_user(
            username="charlie", password="testpass123"
        )
        self.client.force_login(self.user)

    def test_notifications_list_view(self):
        notify(self.user, Notification.FRIEND_REQUEST, "Alice wants to be friends")
        resp = self.client.get(reverse("notifications"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alice wants to be friends")

    def test_mark_read(self):
        notify(self.user, Notification.TRACE_ANALYZED, "Done")
        notify(self.user, Notification.TRACE_ANALYZED, "Done 2")
        self.assertEqual(
            Notification.objects.filter(user=self.user, is_read=False).count(), 2
        )
        resp = self.client.post(reverse("notifications_mark_read"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            Notification.objects.filter(user=self.user, is_read=False).count(), 0
        )

    def test_mark_read_requires_post(self):
        resp = self.client.get(reverse("notifications_mark_read"))
        self.assertEqual(resp.status_code, 405)
