import uuid

from django.db import migrations, models


def populate_uuids(apps, schema_editor):
    Trace = apps.get_model("traces", "Trace")
    for trace in Trace.objects.filter(uuid__isnull=True).iterator():
        trace.uuid = uuid.uuid4()
        trace.save(update_fields=["uuid"])


class Migration(migrations.Migration):

    dependencies = [
        ("traces", "0036_set_existing_traces_analyzed"),
    ]

    operations = [
        # Step 1: add nullable uuid field without default
        migrations.AddField(
            model_name="trace",
            name="uuid",
            field=models.UUIDField(null=True, editable=False),
        ),
        # Step 2: populate existing rows with unique UUIDs
        migrations.RunPython(populate_uuids, migrations.RunPython.noop),
        # Step 3: make non-null + unique + set default for future rows
        migrations.AlterField(
            model_name="trace",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        # Step 4: composite index for index-only scan on polling
        migrations.AddIndex(
            model_name="trace",
            index=models.Index(fields=["uuid", "status"], name="trace_uuid_status"),
        ),
    ]
