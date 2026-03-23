-- Minimum number of traces per week over the last 4 complete ISO weeks.
-- Returns a single integer (0 if any week has no traces).
WITH last_4_weeks AS (
    SELECT generate_series(
        DATE_TRUNC('week', CURRENT_DATE)::date - 28,
        DATE_TRUNC('week', CURRENT_DATE)::date - 7,
        '7 days'::interval
    )::date AS week_start
),
counts AS (
    SELECT w.week_start,
           COUNT(t.id) AS cnt
    FROM last_4_weeks w
    LEFT JOIN traces_trace t
        ON t.uploaded_by_id = %s
       AND t.first_point_date IS NOT NULL
       AND (t.first_point_date AT TIME ZONE 'UTC')::date >= w.week_start
       AND (t.first_point_date AT TIME ZONE 'UTC')::date < w.week_start + 7
    GROUP BY w.week_start
)
SELECT COALESCE(MIN(cnt), 0) FROM counts;
