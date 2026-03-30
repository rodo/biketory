import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("traces", "0039_auth_user_default_username_trigger"),
    ]

    operations = [
        migrations.AddField(
            model_name="trace",
            name="bbox",
            field=django.contrib.gis.db.models.fields.PolygonField(
                blank=True, null=True, srid=4326
            ),
        ),
        migrations.RunSQL(
            sql=(
                "UPDATE traces_trace "
                "SET bbox = ST_Expand(ST_Envelope(route), 0.01) "
                "WHERE route IS NOT NULL"
            ),
            reverse_sql="UPDATE traces_trace SET bbox = NULL",
        ),
    ]
