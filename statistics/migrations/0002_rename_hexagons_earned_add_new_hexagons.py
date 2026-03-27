from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("statistics", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="dailystats",
            old_name="hexagons_earned",
            new_name="hexagons_acquired",
        ),
        migrations.RenameField(
            model_name="weeklystats",
            old_name="hexagons_earned",
            new_name="hexagons_acquired",
        ),
        migrations.RenameField(
            model_name="monthlystats",
            old_name="hexagons_earned",
            new_name="hexagons_acquired",
        ),
        migrations.RenameField(
            model_name="yearlystats",
            old_name="hexagons_earned",
            new_name="hexagons_acquired",
        ),
        migrations.AddField(
            model_name="dailystats",
            name="new_hexagons_acquired",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="weeklystats",
            name="new_hexagons_acquired",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="monthlystats",
            name="new_hexagons_acquired",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="yearlystats",
            name="new_hexagons_acquired",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
