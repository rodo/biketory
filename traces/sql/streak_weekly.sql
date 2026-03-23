-- Current streak of consecutive ISO weeks with at least one trace.
-- Returns a single integer: the streak length (0 if none).
WITH trace_weeks AS (
    SELECT DISTINCT DATE_TRUNC('week', (first_point_date AT TIME ZONE 'UTC')::date)::date AS w
    FROM traces_trace
    WHERE uploaded_by_id = %s
      AND first_point_date IS NOT NULL
),
numbered AS (
    SELECT w, w - (ROW_NUMBER() OVER (ORDER BY w) * 7)::int AS grp
    FROM trace_weeks
),
streaks AS (
    SELECT grp, COUNT(*) AS streak_len, MAX(w) AS last_week
    FROM numbered
    GROUP BY grp
)
SELECT COALESCE(MAX(streak_len), 0)
FROM streaks
WHERE last_week >= DATE_TRUNC('week', CURRENT_DATE)::date - 7;
