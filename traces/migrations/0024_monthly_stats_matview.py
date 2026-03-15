from django.db import migrations, models


CREATE_MATVIEW = """
CREATE MATERIALIZED VIEW hexagon_monthly_stats AS
SELECT
    date_trunc('month', earned_at)::date AS month,
    COUNT(*) AS count
FROM traces_hexagongainevent
GROUP BY 1
ORDER BY 1;
"""

DROP_MATVIEW = "DROP MATERIALIZED VIEW IF EXISTS hexagon_monthly_stats;"


class Migration(migrations.Migration):

    dependencies = [
        ("traces", "0023_hexagongainevent"),
    ]

    operations = [
        migrations.CreateModel(
            name="MonthlyStatsRefresh",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("refreshed_at", models.DateTimeField()),
            ],
            options={"db_table": "traces_monthlystatsrefresh"},
        ),
        migrations.RunSQL(CREATE_MATVIEW, reverse_sql=DROP_MATVIEW),
    ]
