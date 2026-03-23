-- Current streak of consecutive days with at least one trace.
-- Returns a single integer: the streak length (0 if none).
WITH trace_days AS (
    SELECT DISTINCT (first_point_date AT TIME ZONE 'UTC')::date AS d
    FROM traces_trace
    WHERE uploaded_by_id = %s
      AND first_point_date IS NOT NULL
),
numbered AS (
    SELECT d, d - (ROW_NUMBER() OVER (ORDER BY d))::int AS grp
    FROM trace_days
),
streaks AS (
    SELECT grp, COUNT(*) AS streak_len, MAX(d) AS last_day
    FROM numbered
    GROUP BY grp
)
SELECT COALESCE(MAX(streak_len), 0)
FROM streaks
WHERE last_day >= CURRENT_DATE - 1;
