-- Total km all-time for a user.
-- Returns a single float (0 if no traces).
SELECT COALESCE(SUM(length_km), 0)
FROM traces_trace
WHERE uploaded_by_id = %s;
