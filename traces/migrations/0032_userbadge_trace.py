import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("traces", "0031_trace_length_km"),
    ]

    operations = [
        migrations.AddField(
            model_name="userbadge",
            name="trace",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="badges",
                to="traces.trace",
            ),
        ),
    ]
