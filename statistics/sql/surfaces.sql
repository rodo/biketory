SELECT date_trunc(%s, detected_at)::date AS period,
       COUNT(*)                           AS surfaces_detected
FROM   traces_closedsurface
WHERE  detected_at >= %s::date
  AND  detected_at <  (%s::date + interval '1 day')
GROUP  BY 1
