"""Replace username with user_id in User*Stats tables.

UserDailyStats is recreated as a 2-level partitioned table (raw SQL,
managed = False).  The other User*Stats tables are dropped and recreated
with user_id instead of username.
"""

from pathlib import Path

from django.db import migrations, models

_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
_CREATE_PARTITIONED_SQL = (_SQL_DIR / "create_userdailystats_partitioned.sql").read_text()


class Migration(migrations.Migration):

    dependencies = [
        ("statistics", "0004_userstats"),
    ]

    operations = [
        # ── Drop old tables ──────────────────────────────────────────
        migrations.DeleteModel(name="UserDailyStats"),
        migrations.DeleteModel(name="UserWeeklyStats"),
        migrations.DeleteModel(name="UserMonthlyStats"),
        migrations.DeleteModel(name="UserYearlyStats"),

        # ── Recreate UserWeeklyStats with user_id ────────────────────
        migrations.CreateModel(
            name="UserWeeklyStats",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("period", models.DateField()),
                ("user_id", models.IntegerField()),
                ("hexagons_acquired", models.PositiveIntegerField(default=0)),
                ("computed_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-period"],
                "abstract": False,
                "constraints": [
                    models.UniqueConstraint(fields=("user_id", "period"), name="userweeklystats_user_id_period"),
                    models.CheckConstraint(condition=models.Q(("period__week_day", 2)), name="userweeklystats_period_is_monday"),
                ],
            },
        ),

        # ── Recreate UserMonthlyStats with user_id ───────────────────
        migrations.CreateModel(
            name="UserMonthlyStats",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("period", models.DateField()),
                ("user_id", models.IntegerField()),
                ("hexagons_acquired", models.PositiveIntegerField(default=0)),
                ("computed_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-period"],
                "abstract": False,
                "constraints": [
                    models.UniqueConstraint(fields=("user_id", "period"), name="usermonthlystats_user_id_period"),
                    models.CheckConstraint(condition=models.Q(("period__day", 1)), name="usermonthlystats_period_first_of_month"),
                ],
            },
        ),

        # ── Recreate UserYearlyStats with user_id ────────────────────
        migrations.CreateModel(
            name="UserYearlyStats",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("period", models.DateField()),
                ("user_id", models.IntegerField()),
                ("hexagons_acquired", models.PositiveIntegerField(default=0)),
                ("computed_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-period"],
                "abstract": False,
                "constraints": [
                    models.UniqueConstraint(fields=("user_id", "period"), name="useryearlystats_user_id_period"),
                    models.CheckConstraint(condition=models.Q(("period__day", 1), ("period__month", 1)), name="useryearlystats_period_is_jan_first"),
                ],
            },
        ),

        # ── Create partitioned UserDailyStats via raw SQL ────────────
        migrations.RunSQL(
            sql=_CREATE_PARTITIONED_SQL,
            reverse_sql="DROP TABLE IF EXISTS statistics_userdailystats CASCADE;",
        ),
    ]
