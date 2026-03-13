import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("traces", "0013_closedsurface_segment_index_alter_trace_route"),
    ]

    operations = [
        migrations.AlterField(
            model_name="hexagon",
            name="geom",
            field=django.contrib.gis.db.models.fields.PolygonField(srid=4326, unique=True),
        ),
    ]
