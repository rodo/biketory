SELECT date_trunc(%s, earned_at)::date AS period,
       COUNT(*)                         AS new_hexagons_acquired
FROM   traces_hexagongainevent
WHERE  earned_at >= %s::date
  AND  earned_at <  (%s::date + interval '1 day')
  AND  is_first = true
GROUP  BY 1
