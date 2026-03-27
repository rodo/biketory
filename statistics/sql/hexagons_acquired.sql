SELECT date_trunc(%s, earned_at)::date AS period,
       COUNT(*)                         AS hexagons_acquired
FROM   traces_hexagongainevent
WHERE  earned_at >= %s::date
  AND  earned_at <  (%s::date + interval '1 day')
GROUP  BY 1
