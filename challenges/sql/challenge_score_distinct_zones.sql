-- Score for distinct_zones challenges.
-- Counts distinct zones (at the configured admin_level) where the participant
-- acquired at least N hexagons for the first time during the challenge period.
-- Parameters: admin_level, start_date, end_date, hexagons_per_zone, challenge_id
WITH zone_counts AS (
    SELECT
        e.user_id,
        gz.id AS zone_id
    FROM traces_hexagongainevent e
    JOIN traces_hexagon h ON h.id = e.hexagon_id
    JOIN geozones_geozone gz
        ON gz.admin_level = %s
       AND gz.active = TRUE
       AND ST_Contains(gz.geom, ST_Centroid(h.geom))
    WHERE e.is_first = TRUE
      AND e.earned_at >= %s
      AND e.earned_at <= %s
    GROUP BY e.user_id, gz.id
    HAVING COUNT(DISTINCT e.hexagon_id) >= %s
)
SELECT
    cp.user_id,
    COALESCE(COUNT(zc.zone_id), 0) AS score
FROM challenges_challengeparticipant cp
LEFT JOIN zone_counts zc ON zc.user_id = cp.user_id
WHERE cp.challenge_id = %s
GROUP BY cp.user_id
