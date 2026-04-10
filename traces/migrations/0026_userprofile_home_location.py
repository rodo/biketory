import django.contrib.gis.db.models.fields
from django.db import migrations


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
