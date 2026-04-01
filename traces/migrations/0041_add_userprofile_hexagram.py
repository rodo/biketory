import random
import string

from django.db import IntegrityError, migrations, models


def generate_hexagram():
    return "".join(random.choices(string.ascii_lowercase, k=6))


def populate_hexagrams(apps, schema_editor):
    UserProfile = apps.get_model("traces", "UserProfile")
    for profile in UserProfile.objects.filter(hexagram=""):
        for _ in range(10):
            hexagram = generate_hexagram()
            try:
                profile.hexagram = hexagram
                profile.save(update_fields=["hexagram"])
                break
            except IntegrityError:
                continue


class Migration(migrations.Migration):

    dependencies = [
        ("traces", "0040_trace_bbox"),
    ]

    operations = [
        # 1. Add the field as nullable with no unique constraint
        migrations.AddField(
            model_name="userprofile",
            name="hexagram",
            field=models.CharField(default="", max_length=6, editable=False),
            preserve_default=False,
        ),
        # 2. Populate existing rows with random unique values
        migrations.RunPython(populate_hexagrams, migrations.RunPython.noop),
        # 3. Add unique constraint
        migrations.AlterField(
            model_name="userprofile",
            name="hexagram",
            field=models.CharField(max_length=6, unique=True, editable=False),
        ),
    ]
