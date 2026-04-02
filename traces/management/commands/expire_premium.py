import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from traces.models import Subscription, UserProfile

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Set is_premium=False on UserProfiles with no active subscription."

    def handle(self, *args, **options):
        today = timezone.now().date()
        active_user_ids = (
            Subscription.objects.filter(start_date__lte=today, end_date__gte=today)
            .values_list("user_id", flat=True)
            .distinct()
        )
        updated = UserProfile.objects.filter(is_premium=True).exclude(
            user_id__in=active_user_ids
        ).update(is_premium=False)
        logger.info("%d profile(s) set to non-premium.", updated)
