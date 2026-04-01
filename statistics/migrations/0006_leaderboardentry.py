from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("statistics", "0005_userstats_user_id_partitioned"),
    ]

    operations = [
        migrations.CreateModel(
            name="LeaderboardEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_id", models.IntegerField()),
                ("username", models.CharField(max_length=150)),
                ("is_premium", models.BooleanField(default=False)),
                ("hexagons_conquered", models.PositiveIntegerField(default=0)),
                ("hexagons_acquired", models.PositiveIntegerField(default=0)),
                ("rank_conquered", models.PositiveIntegerField()),
                ("rank_acquired", models.PositiveIntegerField()),
                ("computed_at", models.DateTimeField()),
            ],
        ),
        migrations.AddIndex(
            model_name="leaderboardentry",
            index=models.Index(fields=["rank_conquered"], name="statistics_l_rank_co_idx"),
        ),
        migrations.AddIndex(
            model_name="leaderboardentry",
            index=models.Index(fields=["rank_acquired"], name="statistics_l_rank_ac_idx"),
        ),
        migrations.AddConstraint(
            model_name="leaderboardentry",
            constraint=models.UniqueConstraint(fields=("user_id",), name="leaderboard_user_unique"),
        ),
    ]
