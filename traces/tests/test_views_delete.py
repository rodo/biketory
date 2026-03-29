from django.test import TestCase
from django.urls import reverse

from traces.models import Trace

from ._helpers import make_user, small_route


class DeleteTraceTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.trace = Trace.objects.create(route=small_route(), uploaded_by=self.user)

    def test_get_redirects_to_trace_list(self):
        resp = self.client.get(reverse("delete_trace", args=[self.trace.pk]))
        self.assertRedirects(resp, reverse("trace_list"), fetch_redirect_response=False)

    def test_get_does_not_delete_trace(self):
        self.client.get(reverse("delete_trace", args=[self.trace.pk]))
        self.assertEqual(Trace.objects.count(), 1)

    def test_post_deletes_trace(self):
        self.client.post(reverse("delete_trace", args=[self.trace.pk]))
        self.assertEqual(Trace.objects.count(), 0)

    def test_post_redirects_to_trace_list(self):
        resp = self.client.post(reverse("delete_trace", args=[self.trace.pk]))
        self.assertRedirects(resp, reverse("trace_list"), fetch_redirect_response=False)

    def test_delete_unknown_returns_404(self):
        resp = self.client.post(reverse("delete_trace", args=[99999]))
        self.assertEqual(resp.status_code, 404)
