from django.db import IntegrityError
from django.test import TestCase

from referrals.models import Referral
from referrals.tests._helpers import make_user


class ReferralModelTest(TestCase):

    def setUp(self):
        self.sponsor = make_user("sponsor")

    def test_create_referral(self):
        ref = Referral.objects.create(sponsor=self.sponsor, email="new@test.local")
        self.assertEqual(ref.status, Referral.PENDING)
        self.assertFalse(ref.rewarded)
        self.assertIsNone(ref.referee)
        self.assertTrue(len(ref.token) > 10)

    def test_token_generated_unique(self):
        r1 = Referral.objects.create(sponsor=self.sponsor, email="a@test.local")
        r2 = Referral.objects.create(sponsor=self.sponsor, email="b@test.local")
        self.assertNotEqual(r1.token, r2.token)

    def test_unique_sponsor_email(self):
        Referral.objects.create(sponsor=self.sponsor, email="dup@test.local")
        with self.assertRaises(IntegrityError):
            Referral.objects.create(sponsor=self.sponsor, email="dup@test.local")

    def test_str(self):
        ref = Referral.objects.create(sponsor=self.sponsor, email="new@test.local")
        self.assertIn("sponsor", str(ref))
        self.assertIn("new@test.local", str(ref))
