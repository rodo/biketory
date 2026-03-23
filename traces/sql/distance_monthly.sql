-- Total km for the current calendar month.
-- Returns a single float (0 if no traces).
SELECT COALESCE(SUM(length_km), 0)
FROM traces_trace
WHERE uploaded_by_id = %s
  AND first_point_date IS NOT NULL
  AND DATE_TRUNC('month', (first_point_date AT TIME ZONE 'UTC')::date) = DATE_TRUNC('month', CURRENT_DATE);
