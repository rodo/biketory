-- Score for capture_hexagon challenges.
-- Counts how many challenge hexagons the participant currently owns (is Hexagon.owner).
-- Parameters: challenge_id
SELECT
    cp.user_id,
    COUNT(DISTINCT ch.hexagon_id) AS score
FROM challenges_challengeparticipant cp
JOIN challenges_challengehexagon ch
    ON ch.challenge_id = cp.challenge_id
JOIN traces_hexagon h
    ON h.id = ch.hexagon_id
   AND h.owner_id = cp.user_id
WHERE cp.challenge_id = %s
GROUP BY cp.user_id
