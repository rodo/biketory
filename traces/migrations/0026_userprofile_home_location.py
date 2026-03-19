from django.db import migrations
import django.contrib.gis.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ("traces", "0025_apitoken"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="home_location",
            field=django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326),
        ),
    ]
