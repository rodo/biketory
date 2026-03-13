import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("traces", "0014_alter_hexagon_geom_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="hexagon",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
