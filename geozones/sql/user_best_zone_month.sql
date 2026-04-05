SELECT * FROM (
  SELECT DISTINCT ON (r.zone_id)
         r.zone_id, gz.name AS zone_name, gz.code AS zone_code,
         r.period, r.rank_conquered, r.hexagons_conquered,
         r.rank_acquired, r.hexagons_acquired
  FROM geozones_monthlyzoneranking r
  INNER JOIN geozones_geozone gz ON gz.id = r.zone_id
  INNER JOIN geozones_zoneleaderboardentry zle
         ON zle.zone_id = r.zone_id AND zle.user_id = r.user_id
  WHERE r.user_id = %s AND gz.active = TRUE
  ORDER BY r.zone_id, r.rank_conquered ASC, r.period DESC
) best
ORDER BY best.rank_conquered ASC, best.period DESC
LIMIT 3
