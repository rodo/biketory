SELECT date_trunc(%s, earned_at)::date AS period,
       e.user_id                       AS user_id,
       COUNT(*)                         AS hexagons_acquired
FROM   traces_hexagongainevent e
WHERE  earned_at >= %s::date
  AND  earned_at <  (%s::date + interval '1 day')
GROUP  BY 1, 2
