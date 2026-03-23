-- Current streak of consecutive months with at least one trace.
-- Returns a single integer: the streak length (0 if none).
WITH trace_months AS (
    SELECT DISTINCT DATE_TRUNC('month', (first_point_date AT TIME ZONE 'UTC')::date)::date AS m
    FROM traces_trace
    WHERE uploaded_by_id = %s
      AND first_point_date IS NOT NULL
),
numbered AS (
    SELECT m,
           m - (ROW_NUMBER() OVER (ORDER BY m) * INTERVAL '1 month') AS grp
    FROM trace_months
),
streaks AS (
    SELECT grp, COUNT(*) AS streak_len, MAX(m) AS last_month
    FROM numbered
    GROUP BY grp
)
SELECT COALESCE(MAX(streak_len), 0)
FROM streaks
WHERE last_month >= DATE_TRUNC('month', CURRENT_DATE)::date - INTERVAL '1 month';
