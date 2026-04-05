SELECT zle.zone_id, zle.rank_conquered, zle.rank_acquired,
       zle.hexagons_conquered, zle.hexagons_acquired
FROM geozones_zoneleaderboardentry zle
INNER JOIN geozones_geozone gz ON gz.id = zle.zone_id
WHERE zle.user_id = %s AND gz.active = TRUE
