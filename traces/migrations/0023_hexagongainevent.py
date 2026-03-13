import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("traces", "0022_hexagonscore_remove_auto_now"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="HexagonGainEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("earned_at", models.DateTimeField(db_index=True)),
                (
                    "hexagon",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="gain_events",
                        to="traces.hexagon",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hexagon_gain_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
