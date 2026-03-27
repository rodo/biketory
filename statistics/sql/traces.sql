SELECT date_trunc(%s, uploaded_at)::date AS period,
       COUNT(*)                          AS traces_uploaded,
       COALESCE(SUM(length_km), 0)       AS total_distance_km
FROM   traces_trace
WHERE  uploaded_at >= %s::date
  AND  uploaded_at <  (%s::date + interval '1 day')
GROUP  BY 1
