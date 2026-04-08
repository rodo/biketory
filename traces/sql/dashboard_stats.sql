-- Dashboard stats: streak, total distance, monthly distance in a single query.
-- Returns one row: (streak_daily, distance_total, distance_monthly).
-- Parameters: user_id
WITH trace_days AS (
    SELECT DISTINCT (first_point_date AT TIME ZONE 'UTC')::date AS d
    FROM traces_trace
    WHERE uploaded_by_id = %s
      AND first_point_date IS NOT NULL
      AND first_point_date >= CURRENT_DATE - INTERVAL '1 year'
),
numbered AS (
    SELECT d, d - (ROW_NUMBER() OVER (ORDER BY d))::int AS grp
    FROM trace_days
),
streaks AS (
    SELECT COUNT(*) AS streak_len, MAX(d) AS last_day
    FROM numbered
    GROUP BY grp
),
current_streak AS (
    SELECT COALESCE(MAX(streak_len), 0) AS val
    FROM streaks
    WHERE last_day >= CURRENT_DATE - 1
),
dist_total AS (
    SELECT COALESCE(SUM(length_km), 0) AS val
    FROM traces_trace
    WHERE uploaded_by_id = %s
),
dist_monthly AS (
    SELECT COALESCE(SUM(length_km), 0) AS val
    FROM traces_trace
    WHERE uploaded_by_id = %s
      AND first_point_date IS NOT NULL
      AND first_point_date >= DATE_TRUNC('month', CURRENT_DATE)
      AND first_point_date < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'
)
SELECT s.val AS streak_daily,
       dt.val AS distance_total,
       dm.val AS distance_monthly
FROM current_streak s, dist_total dt, dist_monthly dm;
