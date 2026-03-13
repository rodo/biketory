import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("traces", "0015_hexagon_created_at"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(model_name="hexagon", name="owner"),
        migrations.RemoveField(model_name="hexagon", name="closed_surface"),
        migrations.CreateModel(
            name="HexagonScore",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("points", models.PositiveIntegerField(default=0)),
                ("hexagon", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="scores", to="traces.hexagon")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="hexagon_scores", to=settings.AUTH_USER_MODEL)),
            ],
            options={"unique_together": {("hexagon", "user")}},
        ),
    ]
