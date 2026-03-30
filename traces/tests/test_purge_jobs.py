from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase, override_settings


class PurgeJobsTests(TestCase):

    @override_settings(DEBUG=False)
    def test_refuses_when_debug_false(self):
        with self.assertRaises(CommandError):
            call_command("purge_jobs", "--yes")

    @override_settings(DEBUG=True)
    def test_purge_deletes_jobs_and_events(self):
        # Insert a fake job + event to verify deletion
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO procrastinate_jobs (queue_name, task_name, status, args) "
                "VALUES ('test', 'test_task', 'todo', '{}')"
            )
            cursor.execute(
                "INSERT INTO procrastinate_events (job_id, type) "
                "VALUES (currval('procrastinate_jobs_id_seq'), 'deferred')"
            )

        call_command("purge_jobs", "--yes")

        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM procrastinate_jobs")
            self.assertEqual(cursor.fetchone()[0], 0)
            cursor.execute("SELECT count(*) FROM procrastinate_events")
            self.assertEqual(cursor.fetchone()[0], 0)

    @override_settings(DEBUG=True)
    def test_purge_with_empty_tables(self):
        call_command("purge_jobs", "--yes")

        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM procrastinate_jobs")
            self.assertEqual(cursor.fetchone()[0], 0)
