-- Score for new_hexagons challenges with geozone filter.
-- Counts hexagons acquired for the first time during the challenge period,
-- restricted to hexagons within the specified geozone.
-- Parameters: start_date, end_date, geozone_id, challenge_id
SELECT
    cp.user_id,
    COUNT(DISTINCT e.hexagon_id) AS score
FROM challenges_challengeparticipant cp
JOIN traces_hexagongainevent e
    ON e.user_id = cp.user_id
   AND e.is_first = TRUE
   AND e.earned_at >= %s
   AND e.earned_at <= %s
JOIN traces_hexagon h
    ON h.id = e.hexagon_id
JOIN geozones_geozone gz
    ON gz.id = %s
   AND ST_Contains(gz.geom, ST_Centroid(h.geom))
WHERE cp.challenge_id = %s
GROUP BY cp.user_id
