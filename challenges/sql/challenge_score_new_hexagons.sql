-- Score for new_hexagons challenges (no geozone filter).
-- Counts hexagons acquired for the first time during the challenge period.
-- Parameters: start_date, end_date, challenge_id
SELECT
    cp.user_id,
    COUNT(DISTINCT e.hexagon_id) AS score
FROM challenges_challengeparticipant cp
JOIN traces_hexagongainevent e
    ON e.user_id = cp.user_id
   AND e.is_first = TRUE
   AND e.earned_at >= %s
   AND e.earned_at <= %s
WHERE cp.challenge_id = %s
GROUP BY cp.user_id
