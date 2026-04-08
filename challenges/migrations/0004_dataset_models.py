"""Add Dataset, DatasetFeature, ChallengeDatasetScore models.

Also adds:
- Challenge.dataset FK
- ChallengeParticipant.score field
- SQL trigger to increment participant score on dataset score insert
"""

import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("challenges", "0003_goal_met_db_default"),
        ("traces", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- Dataset ---
        migrations.CreateModel(
            name="Dataset",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("source_file", models.CharField(max_length=500)),
                ("md5_hash", models.CharField(max_length=32, unique=True)),
                ("feature_count", models.PositiveIntegerField(default=0)),
                ("imported_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        # --- DatasetFeature ---
        migrations.CreateModel(
            name="DatasetFeature",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("geom", django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ("properties", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("dataset", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="features", to="challenges.dataset")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["dataset"], name="challenges_d_dataset_idx"),
                ],
            },
        ),
        # --- ChallengeDatasetScore ---
        migrations.CreateModel(
            name="ChallengeDatasetScore",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("earned_at", models.DateTimeField(auto_now_add=True)),
                ("challenge", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dataset_scores", to="challenges.challenge")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="challenge_dataset_scores", to=settings.AUTH_USER_MODEL)),
                ("dataset_feature", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="challenge_scores", to="challenges.datasetfeature")),
                ("trace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="challenge_dataset_scores", to="traces.trace")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["challenge", "user"], name="challenges_d_chall_user_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(fields=["challenge", "user", "dataset_feature"], name="challenge_dataset_score_unique"),
                ],
            },
        ),
        # --- Challenge.dataset FK ---
        migrations.AddField(
            model_name="challenge",
            name="dataset",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="challenges",
                to="challenges.dataset",
            ),
        ),
        # --- ChallengeParticipant.score ---
        migrations.AddField(
            model_name="challengeparticipant",
            name="score",
            field=models.IntegerField(default=0),
        ),
        # --- Challenge.challenge_type: widen max_length for new type ---
        migrations.AlterField(
            model_name="challenge",
            name="challenge_type",
            field=models.CharField(
                choices=[
                    ("capture_hexagon", "Capture hexagon"),
                    ("max_points", "Max points"),
                    ("active_days", "Active days"),
                    ("new_hexagons", "New hexagons"),
                    ("distinct_zones", "Distinct zones"),
                    ("dataset_points", "Dataset points"),
                ],
                max_length=20,
            ),
        ),
        # --- SQL trigger: auto-increment participant score on dataset score insert ---
        migrations.RunSQL(
            sql="""
                CREATE OR REPLACE FUNCTION fn_increment_participant_score()
                RETURNS TRIGGER AS $$
                BEGIN
                    UPDATE challenges_challengeparticipant
                       SET score = score + 1
                     WHERE challenge_id = NEW.challenge_id
                       AND user_id = NEW.user_id;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER trg_dataset_score_increment
                AFTER INSERT ON challenges_challengedatasetscore
                FOR EACH ROW
                EXECUTE FUNCTION fn_increment_participant_score();
            """,
            reverse_sql="""
                DROP TRIGGER IF EXISTS trg_dataset_score_increment ON challenges_challengedatasetscore;
                DROP FUNCTION IF EXISTS fn_increment_participant_score();
            """,
        ),
        # --- GIST index on DatasetFeature.geom ---
        migrations.RunSQL(
            sql="CREATE INDEX IF NOT EXISTS challenges_datasetfeature_geom_gist ON challenges_datasetfeature USING GIST (geom);",
            reverse_sql="DROP INDEX IF EXISTS challenges_datasetfeature_geom_gist;",
        ),
    ]
