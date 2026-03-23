from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("traces", "0030_userbadge"),
    ]

    operations = [
        migrations.AddField(
            model_name="trace",
            name="length_km",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
