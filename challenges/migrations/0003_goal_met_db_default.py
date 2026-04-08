"""Add database-level DEFAULT for goal_met column.

Django removes the DB default after AddField, but we need it to prevent
NOT NULL violations from any non-ORM INSERT path.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("challenges", "0002_challenge_new_types"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE challenges_challengeleaderboardentry ALTER COLUMN goal_met SET DEFAULT true;",
            reverse_sql="ALTER TABLE challenges_challengeleaderboardentry ALTER COLUMN goal_met DROP DEFAULT;",
        ),
    ]
