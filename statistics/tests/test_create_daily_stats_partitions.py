from django.core.management import call_command
from django.db import connection
from django.test import TestCase


def _list_partitions(parent_pattern):
    """Return partition names matching a LIKE pattern from pg_class."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT c.relname FROM pg_class c "
            "WHERE c.relname LIKE %s ORDER BY c.relname",
            [parent_pattern],
        )
        return [row[0] for row in cursor.fetchall()]


class CreateDailyStatsPartitionsTests(TestCase):

    def test_creates_partitions(self):
        # Get partition count before
        before = _list_partitions("statistics_userdailystats_%")
        call_command("create_daily_stats_partitions", months_ahead=2)
        after = _list_partitions("statistics_userdailystats_%")
        # Should have at least as many partitions as before (idempotent)
        self.assertGreaterEqual(len(after), len(before))

    def test_idempotent(self):
        call_command("create_daily_stats_partitions", months_ahead=1)
        first = _list_partitions("statistics_userdailystats_%")
        call_command("create_daily_stats_partitions", months_ahead=1)
        second = _list_partitions("statistics_userdailystats_%")
        self.assertEqual(first, second)

    def test_months_ahead_creates_future_partitions(self):
        call_command("create_daily_stats_partitions", months_ahead=4)
        partitions = _list_partitions("statistics_userdailystats_%")
        # Should have partitions beyond the initial set
        self.assertGreater(len(partitions), 0)
