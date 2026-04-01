import random
import string

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models.signals import post_save
from django.dispatch import receiver


def generate_hexagram():
    """Return a random 6-letter lowercase string."""
    return "".join(random.choices(string.ascii_lowercase, k=6))


@receiver(post_save, sender=get_user_model())
def create_user_profile(sender, instance, created, **kwargs):
    if not created:
        return

    from traces.models import UserProfile

    for _ in range(10):
        hexagram = generate_hexagram()
        try:
            UserProfile.objects.create(user=instance, hexagram=hexagram)
            return
        except IntegrityError:
            continue

    raise RuntimeError("Failed to generate a unique hexagram after 10 attempts")
